from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from services.ingestion import ingest_repo
from services.chat_service import get_chat_response
import traceback

app = FastAPI(title="infralens backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    print("Startup: Loading ML models...")
    from services.chat_service import get_llm, get_embeddings
    # Trigger model loading
    get_embeddings()
    get_llm()
    print("Startup: ML models loaded and cached!")

class ChatRequest(BaseModel):
    message: str

class IngestReq(BaseModel):
    repo_url: str

@app.post("/api/ingest")
async def ingest_endpoint(request: IngestReq):
    try:
        print(f"Starting ingestion for: {request.repo_url}")
        result = ingest_repo(request.repo_url)
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
async def chat_endpoint(request: ChatRequest):
    user_msg = request.message
    print(f"Query: {user_msg}")

    try:
        ai_response = get_chat_response(user_msg)
        return {"response": ai_response}
    except Exception as e:
        print(f"CRITICAL CHAT ERROR: {e}")
        traceback.print_exc() 
        return {"response": f"Error: {str(e)}"}