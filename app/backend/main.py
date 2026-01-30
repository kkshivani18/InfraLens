from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

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

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    user_message = request.message
    print(f"Recieved from frontend: {user_message}")

    mock_resp = f"InfraLens AI recieved: '{user_message}' (Backend is working)"
    return {"response": mock_resp}

@app.get("health")
async def health_check():
    return {"status": "active", "service": "InfraLens API"}
