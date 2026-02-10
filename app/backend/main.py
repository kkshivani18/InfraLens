from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from services.ingestion import ingest_repo
from services.chat_service import get_chat_response
from core.auth import get_current_user
from core.database import connect_to_mongo, close_mongo_connection
from models.schemas import ChatRequest, IngestRequest
import traceback

app = FastAPI(title="infralens backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
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

@app.post("/api/ingest")
async def ingest_endpoint(request: IngestRequest, current_user: dict = Depends(get_current_user)):
    try:
        user_id = current_user["user_id"]
        print(f"Starting ingestion for: {request.repo_url} by user: {user_id}")
        result = await ingest_repo(request.repo_url, user_id)
        print(f"Ingestion result: {result}")
        if result["status"] == "error":
             raise HTTPException(status_code=400, detail=result["message"])
        return result
    except Exception as e:
        print(f"Exception in ingest_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("health")
async def health_check():
    return {"status": "active", "service": "InfraLens API"}

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_msg = request.message
    user_id = current_user["user_id"]
    print(f"Query from user {user_id}: {user_msg}")

    try:
        ai_response = await get_chat_response(user_msg, user_id, request.repository_name)
        return {"response": ai_response}
    except Exception as e:
        print(f"Exception in chat_endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/repositories")
async def get_repositories(current_user: dict = Depends(get_current_user)):
    """Get all repositories for the user"""
    try:
        from core.database import get_database
        db = get_database()
        user_id = current_user["user_id"]
        
        repositories = await db.repositories.find(
            {"user_id": user_id}
        ).sort("ingested_at", -1).to_list(length=100)
        
        for repo in repositories:
            repo["_id"] = str(repo["_id"])
            repo["ingested_at"] = repo["ingested_at"].isoformat()
        
        return {"repositories": repositories}
    except Exception as e:
        print(f"Exception in get_repositories: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history/{repository_name}")
async def get_chat_history(repository_name: str, current_user: dict = Depends(get_current_user)):
    """Get chat history for a specific repository"""
    try:
        from core.database import get_database
        db = get_database()
        user_id = current_user["user_id"]
        
        # get all chats of user with that repository
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
    except Exception as e:
        print(f"Exception in get_chat_history: {str(e)}")
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
            qdrant_client = QdrantClient(url=qdrant_url)
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