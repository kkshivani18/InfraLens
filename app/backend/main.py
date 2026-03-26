from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from services.ingestion import ingest_repo, get_collection_name
from services.chat_service import get_chat_response
from services.user_service import update_github_token, get_or_create_user, get_github_token, disconnect_github
from core.auth import get_current_user
from core.database import connect_to_mongo, close_mongo_connection
from models.schemas import ChatRequest, IngestRequest, GitHubConnectRequest, CreateSubscriptionRequest, CreateSubscriptionResponse, SubscriptionStatusResponse, ShareChatRequest
from services.payment_service import payment_service
from services.entitlement_service import entitlement_checker
from services.org_service import require_org_access
from bson import ObjectId
import traceback
import json

app = FastAPI(title="infralens backend")

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
async def ingest_endpoint(request: IngestRequest, current_user: dict = Depends(get_current_user)):
    try:
        from core.database import get_database
        from datetime import datetime
        
        db = get_database()
        user_id = current_user["user_id"]
        org_id = current_user.get("org_id")  # from Clerk JWT
        
        print(f"Starting ingestion for: {request.repo_url} by user: {user_id}, org: {org_id}")
        
        # If ingesting to org, validate user is org member
        if org_id:
            org = await db.organizations.find_one({"org_id": org_id})
            if not org or user_id not in org.get("member_user_ids", []):
                raise HTTPException(status_code=403, detail="You are not a member of this organization")
            
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
        
        # validate access to repository
        repo = await db.repositories.find_one({"name": request.repository_name})
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        
        # workspace isolation
        repo_user_id = repo.get("user_id")
        repo_org_id = repo.get("org_id")
        
        # personal repo
        if repo_org_id is None and repo_user_id:
            if repo_user_id != user_id:
                raise HTTPException(status_code=403, detail="You do not have access to this repository")
        
        # org repo
        if repo_org_id:
            if org_id != repo_org_id:
                raise HTTPException(status_code=403, detail="You do not have access to this organization's repository")
            
            org = await db.organizations.find_one({"org_id": org_id})
            if not org or user_id not in org.get("member_user_ids", []):
                raise HTTPException(status_code=403, detail="You are not a member of this organization")
        
        ai_response = await get_chat_response(user_msg, user_id, request.repository_name)
        return {"response": ai_response}
    except HTTPException:
        raise
    except Exception as e:
        print(f"Exception in chat_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/repositories")
async def get_repositories(workspace_type: str = "personal", current_user: dict = Depends(get_current_user)):
    """Get repositories for current workspace (strict isolation).
    
    Args:
        workspace_type: "personal" or "org" (default: "personal")
    """
    try:
        from core.database import get_database
        db = get_database()
        user_id = current_user["user_id"]
        org_id = current_user.get("org_id")
        
        repositories = []
        
        # personal workspace
        if workspace_type == "personal":
            repositories = await db.repositories.find(
                {"user_id": user_id, "org_id": None}
            ).sort("ingested_at", -1).to_list(length=100)
        
        # Org workspace 
        elif workspace_type == "org":
            if not org_id:
                raise HTTPException(status_code=400, detail="No organization selected")
            
            # Validate user is org member
            org = await db.organizations.find_one({"org_id": org_id})
            if not org or user_id not in org.get("member_user_ids", []):
                raise HTTPException(status_code=403, detail="You are not a member of this organization")
            
            # Return ONLY org repos, never personal repos
            repositories = await db.repositories.find(
                {"org_id": org_id}
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
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history/{repository_name}")
async def get_chat_history(repository_name: str, current_user: dict = Depends(get_current_user)):
    """Get chat history for a specific repository with workspace isolation"""
    try:
        from core.database import get_database
        db = get_database()
        user_id = current_user["user_id"]
        org_id = current_user.get("org_id")
        
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
        
        # Org repo
        if repo_org_id:
            if org_id != repo_org_id:
                raise HTTPException(status_code=403, detail="You do not have access to this organization's repository")
            
            org = await db.organizations.find_one({"org_id": org_id})
            if not org or user_id not in org.get("member_user_ids", []):
                raise HTTPException(status_code=403, detail="You are not a member of this organization")
        
        # Get chat history scoped to user + repository
        chats = await db.chats.find({
            "user_id": user_id,
            "repository_name": repository_name
        }).sort("created_at", -1).limit(10).to_list(length=10)
        
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
        
        repo = await db.repositories.find_one({
            "_id": ObjectId(repo_id),
            "user_id": user_id
        })
        
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found or access denied")
        
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
        
        # Validate org exists and user is member
        org = await db.organizations.find_one({"org_id": org_id})
        if not org or user_id not in org.get("member_user_ids", []):
            raise HTTPException(status_code=403, detail="You are not a member of this organization")
        
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