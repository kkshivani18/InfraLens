from fastapi import FastAPI

app = FastAPI()

@app.get("/chat")
async def root():
    return {"message": "Hello World"}