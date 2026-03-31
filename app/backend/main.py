from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from services.ingestion import ingest_repo, get_collection_name
from services.chat_service import get_chat_response
from services.user_service import update_github_token, get_or_create_user, get_github_token, disconnect_github
from core.auth import get_current_user
from core.database import connect_to_mongo, close_mongo_connection
from models.schemas import ChatRequest, IngestRequest, GitHubConnectRequest, CreateSubscriptionRequest, CreateSubscriptionResponse, SubscriptionStatusResponse, ShareChatRequest, InviteRequest, OrgDetailsResponse, IngestRequestWithOrg
from services.payment_service import payment_service
from services.entitlement_service import entitlement_checker
from services.org_service import require_org_access, invite_member, get_org_details, ensure_org_exists_in_db
from bson import ObjectId
from datetime import datetime
import traceback
import json
import httpx
import os

app = FastAPI(title="infralens backend")
CLERK_API_KEY = os.getenv("CLERK_API_KEY")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://infralens-theta.vercel.app",
        "https://infralens-n36v.onrender.com"
    ],
    allow_origin_regex=r"https://.*\.cloudfront\.net",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("Connecting to MongoDB...")
    await connect_to_mongo()
    print("Startup: Loading ML models...")
    from services.chat_service import get_llm, get_embeddings
    
    # trigger model loading
    get_embeddings()
    get_llm()
    print("Startup: ML models loaded and cached!")

@app.on_event("shutdown")
async def shutdown_event():
    await close_mongo_connection()

@app.get("/health")
async def health_check():
    return {"status": "active", "service": "InfraLens API"}

@app.post("/api/ingest")
async def ingest_endpoint(request: IngestRequestWithOrg, current_user: dict = Depends(get_current_user)):
    try:
        from core.database import get_database
        from datetime import datetime
        
        db = get_database()
        user_id = current_user["user_id"]
        
        org_id = request.org_id or current_user.get("org_id")
        
        print(f"Starting ingestion for: {request.repo_url} by user: {user_id}, org: {org_id}")
        
        if org_id:
            await ensure_org_exists_in_db(org_id, db, current_user)
            
            jwt_org_role = current_user.get("org_role")
            has_org_access_from_jwt = (jwt_org_role in ["org:owner", "org:admin", "org:member"])
            
            org = await db.organizations.find_one({"org_id": org_id})
            is_owner = org and org.get("owner_user_id") == user_id
            is_member_in_db = org and user_id in org.get("member_user_ids", [])            
            has_access = is_owner or has_org_access_from_jwt or is_member_in_db
            
            if not has_access and not is_owner:
                try:
                    if CLERK_API_KEY:
                        async with httpx.AsyncClient() as client:
                            # Get org members from Clerk
                            response = await client.get(
                                f"https://api.clerk.com/v1/organizations/{org_id}/memberships",
                                headers={"Authorization": f"Bearer {CLERK_API_KEY}"}
                            )
                            if response.status_code == 200:
                                memberships = response.json()
                                # check if user is a member in Clerk
                                for membership in memberships.get("data", []):
                                    member_user_id = membership.get("public_user_data", {}).get("user_id")
                                    if member_user_id == user_id:
                                        has_access = True
                                        # sync to MongoDB
                                        if org:
                                            await db.organizations.update_one(
                                                {"org_id": org_id},
                                                {
                                                    "$addToSet": {"member_user_ids": user_id},
                                                    "$set": {"updated_at": datetime.utcnow()}
                                                }
                                            )
                                        print(f"[Ingest] Synced {user_id} to org {org_id} (from Clerk memberships)")
                                        break
                except Exception as e:
                    print(f"[Ingest] Warning: Could not verify Clerk membership: {e}")
            
            if not org or not has_access:
                raise HTTPException(status_code=403, detail="You are not authorized to ingest repos for this organization")
            
            # sync JWT membership to MongoDB
            if has_org_access_from_jwt and not is_member_in_db and not is_owner:
                await db.organizations.update_one(
                    {"org_id": org_id},
                    {
                        "$addToSet": {"member_user_ids": user_id},
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
            
            # Check org quota before ingestion
            month_key = datetime.utcnow().strftime("%Y-%m")
            usage = await db.usage.find_one({"org_id": org_id, "month": month_key})
            
            if usage and usage.get("repos_ingested", 0) >= org.get("ingestion_quota_monthly", 100):
                raise HTTPException(
                    status_code=402,
                    detail=f"Organization quota reached ({org.get('ingestion_quota_monthly', 100)} repos/month). Upgrade to ingest more."
                )
        
        result = await ingest_repo(request.repo_url, user_id, org_id=org_id)
        print(f"Ingestion result: {result}")
        
        if result["status"] == "error":
             raise HTTPException(status_code=400, detail=result["message"])
        
        # increment org quota after successful ingest
        if org_id:
            month_key = datetime.utcnow().strftime("%Y-%m")
            await db.usage.update_one(
                {"org_id": org_id, "month": month_key},
                {
                    "$inc": {"repos_ingested": 1},
                    "$set": {"org_id": org_id, "month": month_key, "updated_at": datetime.utcnow()}
                },
                upsert=True
            )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        print(f"Exception in ingest_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/github/connect")
async def connect_github(request: GitHubConnectRequest, current_user: dict = Depends(get_current_user)):
    """Store GitHub OAuth token for private repo access"""
    try:
        user_id = current_user["user_id"]
        email = current_user.get("email")
        
        print(f"[GitHub] Request from user: {user_id}")
        print(f"[GitHub] Token length: {len(request.github_token)}")
        print(f"[GitHub] Token starts with: {request.github_token[:8]}...")
        
        # user exists in DB
        user = await get_or_create_user(user_id, email)
        print(f"[GitHub Connect] User record: {'created' if user else 'exists'}")
        
        # store token
        success = await update_github_token(
            user_id, 
            request.github_token, 
            request.github_username
        )
        print(f"[GitHub Connect] Token storage: {'success' if success else 'failed'}")
        
        if success:
            print(f"GitHub token stored for user {user_id}")
            return {
                "status": "success", 
                "message": "GitHub account connected successfully",
                "github_username": request.github_username
            }
        else:
            print(f"✗ Failed to store GitHub token for user {user_id}")
            raise HTTPException(status_code=500, detail="Failed to store GitHub token")
    except HTTPException:
        raise
    except Exception as e:
        print(f"Exception in connect_github: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/github/disconnect")
async def disconnect_github_endpoint(current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user["user_id"]
        success = await disconnect_github(user_id)
        
        if success:
            return {"status": "success", "message": "GitHub account disconnected"}
        else:
            return {"status": "info", "message": "No GitHub account was connected"}
    except Exception as e:
        print(f"Exception in disconnect_github: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/github/status")
async def github_status(current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user["user_id"]
        token = await get_github_token(user_id)
        
        return {
            "connected": token is not None,
            "has_token": token is not None
        }
    except Exception as e:
        print(f"Exception in github_status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    return {"status": "active", "service": "InfraLens API"}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_msg = request.message
    user_id = current_user["user_id"]
    
    org_id = current_user.get("org_id")

    try:
        from core.database import get_database
        db = get_database()
        
        print(f"[Chat] User: {user_id}, Org: {org_id}, Repository: {request.repository_name}")
        print(f"[Chat] Message: {user_msg[:50]}...")
        
        # validate access to repository
        repo = await db.repositories.find_one({"name": request.repository_name})
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        print(f"[Chat] Found repo - user_id: {repo.get('user_id')}, org_id: {repo.get('org_id')}")
        
        # workspace isolation
        repo_user_id = repo.get("user_id")
        repo_org_id = repo.get("org_id")
        
        # personal repo
        if repo_org_id is None and repo_user_id:
            if repo_user_id != user_id:
                raise HTTPException(status_code=403, detail="You do not have access to this repository")
            print(f"[Chat] ✓ Personal repo access granted")
        
        # validate user is owner or member
        if repo_org_id:
            await ensure_org_exists_in_db(repo_org_id, db, current_user)
            
            jwt_org_role = current_user.get("org_role")
            has_org_access_from_jwt = (jwt_org_role in ["org:owner", "org:admin", "org:member"])
            
            org = await db.organizations.find_one({"org_id": repo_org_id})
            is_owner = org and org.get("owner_user_id") == user_id
            is_member_in_db = org and user_id in org.get("member_user_ids", [])
            has_access = is_owner or has_org_access_from_jwt or is_member_in_db
            
            if not has_access and not is_owner:
                try:
                    clerk_api_key = os.getenv("CLERK_API_KEY")
                    if clerk_api_key:
                        async with httpx.AsyncClient() as client:
                            # Get org members from Clerk
                            response = await client.get(
                                f"https://api.clerk.com/v1/organizations/{repo_org_id}/memberships",
                                headers={"Authorization": f"Bearer {clerk_api_key}"}
                            )
                            if response.status_code == 200:
                                memberships = response.json()
                                # check if user is a member in Clerk
                                for membership in memberships.get("data", []):
                                    member_user_id = membership.get("public_user_data", {}).get("user_id")
                                    if member_user_id == user_id:
                                        has_access = True
                                        # sync to MongoDB
                                        if org:
                                            await db.organizations.update_one(
                                                {"org_id": repo_org_id},
                                                {
                                                    "$addToSet": {"member_user_ids": user_id},
                                                    "$set": {"updated_at": datetime.utcnow()}
                                                }
                                            )
                                        print(f"[Chat] Synced {user_id} to org {repo_org_id} (from Clerk memberships)")
                                        break
                except Exception as e:
                    print(f"[Chat] Warning: Could not verify Clerk membership: {e}")
            
            if not org or not has_access:
                print(f"[Chat] ✗ Not org member (owner={is_owner}, jwt_role={jwt_org_role}, in_db={is_member_in_db})")
                raise HTTPException(status_code=403, detail="You are not authorized to access this organization's repository")
            
            if has_org_access_from_jwt and not is_member_in_db and not is_owner:
                await db.organizations.update_one(
                    {"org_id": repo_org_id},
                    {
                        "$addToSet": {"member_user_ids": user_id},
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
                print(f"[Chat] Synced {user_id} to org {repo_org_id} member list")
            
            print(f"[Chat] ✓ Org repo access granted")
        
        # chat shared across all org members, use org_id
        chat_org_id = repo.get("org_id") if repo else None
        ai_response = await get_chat_response(user_msg, user_id, request.repository_name, org_id=chat_org_id)
        return {"response": ai_response}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Exception in chat_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/repositories")
async def get_repositories(workspace_type: str = "personal", org_id: str = None, current_user: dict = Depends(get_current_user)):
    """Get repositories for current workspace (strict isolation).
    
    Args:
        workspace_type: "personal" or "org" (default: "personal")
        org_id: Optional org_id from query param (overrides JWT org_id)
    """
    try:
        from core.database import get_database
        db = get_database()
        user_id = current_user["user_id"]
        jwt_org_id = current_user.get("org_id")        
        final_org_id = org_id or jwt_org_id
        
        repositories = []
        
        # personal workspace
        if workspace_type == "personal":
            repositories = await db.repositories.find(
                {"user_id": user_id, "org_id": None}
            ).sort("ingested_at", -1).to_list(length=100)
        
        # Org workspace 
        elif workspace_type == "org":
            if not final_org_id:
                raise HTTPException(status_code=400, detail="No organization selected")
            print(f"        user_id={user_id}, org_id={final_org_id}")
            
            await ensure_org_exists_in_db(final_org_id, db, current_user)
            
            # validate user is org owner or member
            jwt_org_role = current_user.get("org_role")
            has_org_access_from_jwt = (jwt_org_role in ["org:owner", "org:admin", "org:member"])
            
            org = await db.organizations.find_one({"org_id": final_org_id})
            is_owner = org and org.get("owner_user_id") == user_id
            is_member_in_db = org and user_id in org.get("member_user_ids", [])
            has_access = is_owner or has_org_access_from_jwt or is_member_in_db
            
            if not has_access and not is_owner:
                try:
                    if CLERK_API_KEY:
                        async with httpx.AsyncClient() as client:
                            # Get org members from Clerk
                            response = await client.get(
                                f"https://api.clerk.com/v1/organizations/{final_org_id}/memberships",
                                headers={"Authorization": f"Bearer {CLERK_API_KEY}"}
                            )
                            if response.status_code == 200:
                                memberships = response.json()
                                found = False
                                for i, membership in enumerate(memberships.get("data", [])):
                                    print(json.dumps(membership, indent=2, default=str))
                                    
                                    member_id = membership.get("public_user_data", {}).get("user_id")
                                    role = membership.get("role")
                                    
                                    if member_id == user_id:
                                        has_access = True
                                        found = True
                                        # Sync to MongoDB
                                        if org:
                                            await db.organizations.update_one(
                                                {"org_id": final_org_id},
                                                {
                                                    "$addToSet": {"member_user_ids": user_id},
                                                    "$set": {"updated_at": datetime.utcnow()}
                                                }
                                            )
                                        print(f"[Auth] Synced {user_id} to org {final_org_id} (from Clerk memberships)")
                                        break
                    else:
                        print(f"[ERROR] CLERK_API_KEY not set! Cannot verify membership via Clerk")
                except Exception as e:
                    print(f"[Auth] Warning: Could not verify Clerk membership: {e}")
                    traceback.print_exc()
            
            if not org or not has_access:
                raise HTTPException(status_code=403, detail="You are not authorized to access this organization")
            
            if (has_org_access_from_jwt or is_member_in_db) and not is_member_in_db and not is_owner:
                await db.organizations.update_one(
                    {"org_id": final_org_id},
                    {
                        "$addToSet": {"member_user_ids": user_id},
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
                print(f"[Auth] Synced {user_id} to org {final_org_id} member list (from JWT org_role)")
            
            # Return ONLY org repos, never personal repos
            repositories = await db.repositories.find(
                {"org_id": final_org_id}
            ).sort("ingested_at", -1).to_list(length=100)
        
        else:
            raise HTTPException(status_code=400, detail="Invalid workspace_type. Use 'personal' or 'org'")
        
        # Format response
        for repo in repositories:
            repo["_id"] = str(repo["_id"])
            repo["ingested_at"] = repo["ingested_at"].isoformat()
        
        return {"repositories": repositories}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Exception in get_repositories: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history/{repository_name}")
async def get_chat_history(repository_name: str, current_user: dict = Depends(get_current_user)):
    """Get chat history for a specific repository with workspace isolation"""
    try:
        from core.database import get_database
        db = get_database()
        user_id = current_user["user_id"]
        
        final_org_id = current_user.get("org_id")
        
        # validate access to repo
        repo = await db.repositories.find_one({"name": repository_name})
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        # workspace isolation
        repo_user_id = repo.get("user_id")
        repo_org_id = repo.get("org_id")
        
        # personal repo
        if repo_org_id is None and repo_user_id:
            if repo_user_id != user_id:
                raise HTTPException(status_code=403, detail="You do not have access to this repository")
        
        # validate user is owner or member
        if repo_org_id:
            await ensure_org_exists_in_db(repo_org_id, db, current_user)
            
            jwt_org_role = current_user.get("org_role")
            has_org_access_from_jwt = (jwt_org_role in ["org:owner", "org:admin", "org:member"])
            
            org = await db.organizations.find_one({"org_id": repo_org_id})
            is_owner = org and org.get("owner_user_id") == user_id
            is_member_in_db = org and user_id in org.get("member_user_ids", [])
            
            has_access = is_owner or has_org_access_from_jwt or is_member_in_db
            
            if not has_access and not is_owner:
                import httpx
                import os
                try:
                    clerk_api_key = os.getenv("CLERK_API_KEY")
                    if clerk_api_key:
                        async with httpx.AsyncClient() as client:
                            # Get org members from Clerk
                            response = await client.get(
                                f"https://api.clerk.com/v1/organizations/{repo_org_id}/memberships",
                                headers={"Authorization": f"Bearer {clerk_api_key}"}
                            )
                            if response.status_code == 200:
                                memberships = response.json()
                                # Check if user is a member in Clerk
                                for membership in memberships.get("data", []):
                                    member_user_id = membership.get("public_user_data", {}).get("user_id")
                                    if member_user_id == user_id:
                                        # User is a member in Clerk, grant access
                                        has_access = True
                                        # Sync to MongoDB
                                        if org:
                                            await db.organizations.update_one(
                                                {"org_id": repo_org_id},
                                                {
                                                    "$addToSet": {"member_user_ids": user_id},
                                                    "$set": {"updated_at": datetime.utcnow()}
                                                }
                                            )
                                        print(f"[ChatHistory] Synced {user_id} to org {repo_org_id} (from Clerk memberships)")
                                        break
                except Exception as e:
                    print(f"[ChatHistory] Warning: Could not verify Clerk membership: {e}")
            
            if not org or not has_access:
                raise HTTPException(status_code=403, detail="You are not authorized to access this organization's repository")
            
            if has_org_access_from_jwt and not is_member_in_db and not is_owner:
                await db.organizations.update_one(
                    {"org_id": repo_org_id},
                    {
                        "$addToSet": {"member_user_ids": user_id},
                        "$set": {"updated_at": datetime.utcnow()}
                    }
                )
        
        # For org repos, all members see the same chat history
        if repo_org_id:
            chats = await db.chats.find({
                "org_id": repo_org_id,
                "repository_name": repository_name
            }).sort("created_at", -1).limit(10).to_list(length=10)
            print(f"[ChatHistory] Retrieved chat history for org repo: org_id={repo_org_id}, repo={repository_name}")
        else:
            chats = await db.chats.find({
                "user_id": user_id,
                "repository_name": repository_name
            }).sort("created_at", -1).limit(10).to_list(length=10)
            print(f"[ChatHistory] Retrieved chat history for personal repo: user_id={user_id}, repo={repository_name}")
        
        # extract messages
        all_messages = []
        for chat in reversed(chats):  
            for msg in chat.get("messages", []):
                all_messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": msg["timestamp"].isoformat() if "timestamp" in msg else None
                })
        
        return {"messages": all_messages}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Exception in get_chat_history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/shared-with-me")
async def get_shared_chats(current_user: dict = Depends(get_current_user)):
    """Get list of chats shared with the current user"""
    try:
        from core.database import get_database
        
        db = get_database()
        user_email = current_user.get("email")
        
        if not user_email:
            return {"shared_chats": []}
        
        # all chats shared with this user's email
        shared_chats = await db.chat_shares.find(
            {"shared_with_email": user_email}
        ).sort("created_at", -1).to_list(length=50)
        
        # enrich with actual chat messages
        enriched_chats = []
        for share in shared_chats:
            chat = await db.chats.find_one({
                "_id": ObjectId(share["chat_session_id"]) if share["chat_session_id"].startswith("ObjectId") else share["chat_session_id"],
                "repository_name": share["repository_name"]
            })
            
            if chat:
                messages = []
                for msg in chat.get("messages", []):
                    messages.append({
                        "role": msg["role"],
                        "content": msg["content"],
                        "timestamp": msg["timestamp"].isoformat() if "timestamp" in msg else None
                    })
                
                enriched_chats.append({
                    "chat_session_id": share["chat_session_id"],
                    "repository_name": share["repository_name"],
                    "shared_by_user_id": share["shared_by_user_id"],
                    "shared_at": share["created_at"].isoformat(),
                    "access_level": share["access_level"],
                    "messages": messages
                })
        
        return {"shared_chats": enriched_chats}
    
    except Exception as e:
        print(f"Exception in get_shared_chats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/repositories/{repo_id}")
async def delete_repository(repo_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a repository and its associated data"""
    try:
        from core.database import get_database
        from bson import ObjectId
        from qdrant_client import QdrantClient
        import os
        
        db = get_database()
        user_id = current_user["user_id"]
        
        # get repo first
        try:
            repo = await db.repositories.find_one({"_id": ObjectId(repo_id)})
        except Exception:
            repo = None
        
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        # personal repo access
        if repo.get("user_id") and not repo.get("org_id"):
            if repo["user_id"] != user_id:
                raise HTTPException(status_code=403, detail="You do not have access to this repository")
            
        # org repo access
        elif repo.get("org_id"):
            jwt_org_role = current_user.get("org_role")
            has_org_access_from_jwt = (jwt_org_role in ["org:owner", "org:admin", "org:member"])
            
            org = await db.organizations.find_one({"org_id": repo["org_id"]})
            is_owner = org and org.get("owner_user_id") == user_id
            is_member_in_db = org and user_id in org.get("member_user_ids", [])
            
            has_access = is_owner or has_org_access_from_jwt or is_member_in_db
            
            if not has_access and not is_owner:
                try:
                    clerk_api_key = os.getenv("CLERK_API_KEY")
                    if clerk_api_key:
                        async with httpx.AsyncClient() as client:
                            # Get org members from Clerk
                            response = await client.get(
                                f"https://api.clerk.com/v1/organizations/{repo['org_id']}/memberships",
                                headers={"Authorization": f"Bearer {clerk_api_key}"}
                            )
                            if response.status_code == 200:
                                memberships = response.json()
                                # Check if user is a member in Clerk
                                for membership in memberships.get("data", []):
                                    member_user_id = membership.get("public_user_data", {}).get("user_id")
                                    if member_user_id == user_id:
                                        # User is a member in Clerk, grant access
                                        has_access = True
                                        # Sync to MongoDB
                                        if org:
                                            await db.organizations.update_one(
                                                {"org_id": repo["org_id"]},
                                                {
                                                    "$addToSet": {"member_user_ids": user_id},
                                                    "$set": {"updated_at": datetime.utcnow()}
                                                }
                                            )
                                        print(f"[Delete] Synced {user_id} to org {repo['org_id']} (from Clerk memberships)")
                                        break
                except Exception as e:
                    print(f"[Delete] Warning: Could not verify Clerk membership: {e}")
            
            if not org or not has_access:
                raise HTTPException(status_code=403, detail="You do not have access to this organization's repository")
        else:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        collection_name = repo["collection_name"]
        
        # del from qdrant
        try:
            qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
            qdrant_api_key = os.getenv("QDRANT_API_KEY")
            qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
            qdrant_client.delete_collection(collection_name=collection_name)
            print(f"Deleted Qdrant collection: {collection_name}")
        except Exception as e:
            print(f"Warning: Failed to delete Qdrant collection: {e}")
        
        # del associated chats
        delete_chats_result = await db.chats.delete_many({
            "user_id": user_id,
            "repository_name": repo["name"]
        })
        print(f"Deleted {delete_chats_result.deleted_count} chats")
        
        # delete repo from mongoDB
        await db.repositories.delete_one({"_id": ObjectId(repo_id)})
        print(f"Deleted repository: {repo['name']}")
        
        return {
            "status": "success",
            "message": f"Repository '{repo['name']}' deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Exception in delete_repository: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Payment endpoints -----------------------------------------------------------------

@app.post("/api/payments/create-subscription")
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: dict = Depends(get_current_user),
):
    """Start subscription checkout for user."""
    try:
        user_id = current_user["user_id"]
        # Use email from Clerk, or fallback to generated email if None
        email = current_user.get("email") or f"{user_id}@gmail.com"
        
        checkout_data, error = await payment_service.create_subscription(
            user_id, email, request.plan
        )
        
        if error:
            raise HTTPException(status_code=400, detail=error)
        
        return CreateSubscriptionResponse(**checkout_data)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Exception in create_subscription: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/payments/subscription-status")
async def get_subscription_status(
    current_user: dict = Depends(get_current_user),
):
    """Get current subscription status for authenticated user."""
    try:
        user_id = current_user["user_id"]
        status = await payment_service.get_user_subscription(user_id)
        return status
    except Exception as e:
        print(f"Exception in get_subscription_status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/payments/webhook")
async def razorpay_webhook(
    request: dict,
    x_razorpay_signature: str = Header(None),
):
    """
    Public webhook endpoint for Razorpay events.
    Verify signature, then process subscription/payment events.
    """
    try:
        body_str = json.dumps(request)
        
        # verify webhook signature
        if not payment_service.verify_webhook_signature(body_str, x_razorpay_signature):
            raise HTTPException(status_code=403, detail="Invalid signature")
        
        # Process the event
        success, message = await payment_service.process_webhook_event(request)
        
        if success:
            return {"status": "success", "message": message}
        else:
            return {"status": "warning", "message": message}
    
    except ValueError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        # Always return 200 to avoid Razorpay retries
        return {"status": "error", "message": str(e)}

@app.post("/api/chat/share")
async def share_chat(
    request: ShareChatRequest,  # { repository_name, chat_session_id, share_with_emails }
    current_user: dict = Depends(get_current_user),
):
    """Share a chat session with team members (workspace sharing)."""
    try:
        from core.database import get_database
        from datetime import datetime
        
        db = get_database()
        user_id = current_user["user_id"]
        org_id = current_user.get("org_id")
        
        # org members can share chats
        if not org_id:
            raise HTTPException(
                status_code=403,
                detail="Chat sharing is only available in Team workspaces"
            )
        
        # Validate org exists and user is member or owner
        jwt_org_role = current_user.get("org_role")
        has_org_access_from_jwt = (jwt_org_role in ["org:owner", "org:admin", "org:member"])
        
        org = await db.organizations.find_one({"org_id": org_id})
        is_owner = org and org.get("owner_user_id") == user_id
        is_member_in_db = org and user_id in org.get("member_user_ids", [])
        
        has_access = is_owner or has_org_access_from_jwt or is_member_in_db
        
        if not has_access and not is_owner:
            try:
                clerk_api_key = os.getenv("CLERK_API_KEY")
                if clerk_api_key:
                    async with httpx.AsyncClient() as client:
                        # Get org members from Clerk
                        response = await client.get(
                            f"https://api.clerk.com/v1/organizations/{org_id}/memberships",
                            headers={"Authorization": f"Bearer {clerk_api_key}"}
                        )
                        if response.status_code == 200:
                            memberships = response.json()
                            # Check if user is a member in Clerk
                            for membership in memberships.get("data", []):
                                member_user_id = membership.get("public_user_data", {}).get("user_id")
                                if member_user_id == user_id:
                                    # User is a member in Clerk, grant access
                                    has_access = True
                                    # Sync to MongoDB
                                    if org:
                                        await db.organizations.update_one(
                                            {"org_id": org_id},
                                            {
                                                "$addToSet": {"member_user_ids": user_id},
                                                "$set": {"updated_at": datetime.utcnow()}
                                            }
                                        )
                                    print(f"[Share] Synced {user_id} to org {org_id} (from Clerk memberships)")
                                    break
            except Exception as e:
                print(f"[Share] Warning: Could not verify Clerk membership: {e}")
        
        if not org or not has_access:
            raise HTTPException(status_code=403, detail="You are not authorized to access this organization")
        
        if has_org_access_from_jwt and not is_member_in_db and not is_owner:
            await db.organizations.update_one(
                {"org_id": org_id},
                {
                    "$addToSet": {"member_user_ids": user_id},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
        
        # Validate repository exists and belongs to this org
        repo = await db.repositories.find_one(
            {"name": request.repository_name, "org_id": org_id}
        )
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found in this workspace")
        
        # Store share records for each recipient
        share_records = []
        for email in request.share_with_emails or []:
            share_record = {
                "chat_session_id": request.chat_session_id,
                "repository_name": request.repository_name,
                "org_id": org_id,
                "shared_by_user_id": user_id,
                "shared_with_email": email,
                "created_at": datetime.utcnow(),
                "access_level": "view"  # read-only access
            }
            share_records.append(share_record)
        
        if share_records:
            result = await db.chat_shares.insert_many(share_records)
            shared_count = len(result.inserted_ids)
        else:
            shared_count = 0
        
        return {
            "status": "success",
            "message": f"Chat shared with {shared_count} team member(s)",
            "shared_count": shared_count
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Exception in share_chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Org Management Endpoints ---------------------------------

@app.get("/api/org/details")
async def get_org_details_endpoint(org_id: str = None, current_user: dict = Depends(get_current_user)):
    """Get organization details (members, quota, plan info)"""
    try:
        from core.database import get_database
        db = get_database()
        
        auth_org_id = current_user.get("org_id")
        request_org_id = org_id
        
        final_org_id = request_org_id or auth_org_id
        
        if not final_org_id or final_org_id == "None":
            return {
                "error": "not_in_org",
                "message": "You are not in an organization. Switch to an organization workspace using the dropdown at the top left."
            }
        
        try:
            await ensure_org_exists_in_db(final_org_id, db, current_user)
        except HTTPException as e:
            if e.status_code == 404:
                return {
                    "error": "org_not_found",
                    "message": "Organization not found. It may have been deleted."
                }
            raise
        
        org_details = await get_org_details(final_org_id, db)
        return org_details
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Exception in get_org_details_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class InviteRequestWithOrg(BaseModel):
    email: str
    org_id: str = None

@app.post("/api/org/invite")
async def invite_member_endpoint(
    request: InviteRequestWithOrg,
    current_user: dict = Depends(get_current_user),
):
    """Invite a new member to the organization"""
    try:
        from core.database import get_database
        db = get_database()
        
        auth_org_id = current_user.get("org_id")
        request_org_id = request.org_id
        
        final_org_id = request_org_id or auth_org_id
        
        if not final_org_id:
            return {
                "error": "not_in_org",
                "message": "Not in an organization. Switch to an organization workspace first."
            }
        
     
        await ensure_org_exists_in_db(final_org_id, db, current_user)
        
        result = await invite_member(final_org_id, request.email, current_user, db)
        return result
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Exception in invite_member_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/org/leave")
async def leave_organization_endpoint(current_user: dict = Depends(get_current_user)):
    """Leave current organization"""
    try:
        from core.database import get_database
        db = get_database()
        
        user_id = current_user.get("user_id")
        org_id = current_user.get("org_id")
        
        if not org_id:
            raise HTTPException(
                status_code=400,
                detail="Not in an organization"
            )
        
        # Fetch org
        org = await db.organizations.find_one({"org_id": org_id})
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        # Remove user from org's member list
        await db.organizations.update_one(
            {"org_id": org_id},
            {"$pull": {"member_user_ids": user_id}}
        )
        
        # Update user's org_id to None
        await db.users.update_one(
            {"user_id": user_id},
            {"$set": {"org_id": None}}
        )
        
        return {
            "status": "success",
            "message": f"You have left the organization '{org['name']}'"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Exception in leave_organization_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))