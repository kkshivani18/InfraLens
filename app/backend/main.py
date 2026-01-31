from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from services.ingestion import ingest_repo

app = FastAPI(title="infralens backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class IngestReq(BaseModel):
    repo_url: str

@app.post("/api/ingest")
async def ingest_endpoint(request: IngestReq):
    try:
        result = ingest_repo(request.repo_url)
        if result["status"] == "error":
             raise HTTPException(status_code=400, detail=result["message"])
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    user_message = request.message
    print(f"Recieved from frontend: {user_message}")

    mock_resp = f"InfraLens AI recieved: '{user_message}' (Backend is working)"
    return {"response": mock_resp}

@app.get("health")
async def health_check():
    return {"status": "active", "service": "InfraLens API"}
