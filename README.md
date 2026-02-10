## InfraLens: The AI-Native Onboarding Platform
AI-powered codebase analysis platform. Chat with your GitHub repositories using natural language.

## What It Does
- Clone GitHub repositories (public only for now)
- Index code using hybrid vector search (dense + sparse embeddings)
- Chat with your codebase using local LLM (Ollama)
- Multi-user support with authentication (Clerk)
- Persistent chat history per repository

## Tech Stack

**Frontend**
- React + TypeScript + Vite
- TailwindCSS
- React Router
- Clerk (authentication)

**Backend**
- FastAPI (Python)
- LangChain (LLM orchestration)
- Ollama (local LLM - llama3.2)
- Sentence Transformers (embeddings)

**Data Layer**
- MongoDB (user data, repos, chat history)
- Qdrant (vector database)
- GitPython (repo cloning)

## Prerequisites

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- Ollama (running locally)
- Clerk account (for auth)

## Setup

### 1. Clone and Install

```bash
git clone <repo-url>
cd InfraLens
```

### 2. Start Infrastructure

```bash
docker-compose up -d
```

This starts MongoDB (port 27017) and Qdrant (port 6333).

### 3. Install Ollama & Pull Model

```bash
# Install from https://ollama.ai
ollama pull llama3.2
```

### 4. Backend Setup

```bash
cd app/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env`:
```env
MONGODB_URL=mongodb://localhost:27017/<database-name>
QDRANT_URL=http://localhost:6333
CLERK_SECRET_KEY=your_clerk_secret_key
```

Start backend:
```bash
uvicorn main:app --reload --port 8000
```

### 5. Frontend Setup

```bash
cd app/frontend
npm install
```

Create `.env`:
```env
VITE_API_URL=http://localhost:8000/api
VITE_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
```

Start frontend:
```bash
npm run dev
```

## Usage

1. Sign up/login via Clerk
2. Add a GitHub repository URL
3. Wait for ingestion (indexing takes 30s-2min depending on repo size)
4. Start chatting with your codebase

## Architecture  

**Ingestion Flow:**
1. Clone repo → Parse files → Split into chunks
2. Generate embeddings (dense + sparse)
3. Store in Qdrant with hybrid retrieval mode
4. Save metadata to MongoDB

**Chat Flow:**
1. User query → Retrieve relevant code chunks
2. Smart prioritization (README for broad questions)
3. Build context → Send to Ollama LLM
4. Return response → Save to MongoDB

## Project Structure

```
InfraLens/
├── app/
│   ├── backend/
│   │   ├── core/          # Auth, database connection
│   │   ├── models/        # Pydantic schemas
│   │   ├── services/      # Ingestion, chat service
│   │   └── main.py        # FastAPI app
│   └── frontend/
│       └── src/
│           ├── layouts/
│           ├── pages/     # Chat, repos, add repo
│           └── services/  # API client
├── docker-compose.yml
└── qdrant_data/          # Vector DB storage
```

## To be Implemented

- **Private repositories** - Only public GitHub repos work (OAuth integration pending)
- **API rate limiting** - No request throttling implemented
- **Billing integration** - No usage tracking or payment system
- Large codebases (>5000 files) may take significant time to ingest
- Only English language support in LLM

<!-- ## Known Issues

- Chat history loads but pagination not implemented (shows last 10 chats)
- No progress indicator during repository ingestion
- Error handling for network failures needs improvement -->

## License

MIT