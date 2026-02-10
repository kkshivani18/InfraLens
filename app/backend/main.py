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