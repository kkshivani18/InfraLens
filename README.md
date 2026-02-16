## InfraLens: The AI-Native Onboarding Platform
AI-powered codebase analysis platform. Chat with your GitHub repositories using natural language.

## What It Does
- Clone and analyze both **public and private** GitHub repositories with Personal Access Token integration
- Index code using hybrid vector search (dense + sparse embeddings) with support for 15+ file types
- Chat with your codebase using local LLM (Ollama llama3.2) with context-aware retrieval
- Multi-user support with secure authentication (Clerk)
- Persistent chat history per repository with conversation retrieval
- Full repository management (list, view metadata, delete with cleanup)
- GitHub account connection/disconnection for seamless private repo access

## Features

### 🔐 Authentication & Multi-tenancy
- Secure user authentication via Clerk
- Per-user repository isolation and management
- GitHub Personal Access Token integration for private repositories

### 📦 Repository Support
- **Public repositories:** Direct cloning via URL
- **Private repositories:** GitHub PAT authentication with automatic privacy detection
- **Supported file types:** `.py`, `.ts`, `.js`, `.tsx`, `.jsx`, `.md`, `.java`, `.go`, `.sh`, `.rs`, `.c`, `.cpp`, `.tf`, `.yml`, `.yaml`, `.json`, `.txt`, `.html`, `.css`, `.sql`
- **Intelligent exclusions:** Automatically skips `node_modules`, `.git`, `venv`, `__pycache__`, `dist`, `build`, `target`, `.next`, `.vscode`, `.idea`

### 🤖 Smart AI Chat
- Local LLM (Ollama llama3.2) for privacy-first architecture
- Hybrid vector search combining dense and sparse embeddings
- Context-aware retrieval with smart prioritization (README, package.json for broad questions)
- Language-aware code splitting for Python, JavaScript, TypeScript, Go, Java, Rust, Markdown, Terraform, YAML
- Per-repository conversation history (last 10 chats retrievable)

### Repository Management
- List all ingested repositories with metadata (ingestion date, file/chunk counts, privacy status)
- Delete repositories with full cleanup (removes from MongoDB, Qdrant, and temporary files)
- Repository status tracking and GitHub connection monitoring

## Tech Stack

**Frontend**
- React 19.2.0 + TypeScript 5.9.3
- Vite 7.2.4
- TailwindCSS 4.1.18
- React Router
- Clerk (authentication)
- Lucide React 0.563.0 (icons)

**Backend**
- FastAPI (Python 3.9+)
- LangChain (LLM orchestration)
- Ollama (local LLM - llama3.2)
- Sentence Transformers (`all-MiniLM-L6-v2` for dense embeddings)
- FastEmbed Sparse (`Qdrant/bm25` for sparse embeddings)
- httpx (GitHub API integration)
- chardet (file encoding detection)
- PyJWT (token handling)

**Data Layer**
- MongoDB (user data, repos, chat history)
- Qdrant (vector database)
- GitPython (repo cloning)

## Prerequisites

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- Ollama (running locally with `llama3.2` model)
- Clerk account (for authentication)
- GitHub Personal Access Token (optional, for private repositories)

## Usage

### For Public Repositories
1. Sign up/login via Clerk
2. Add a GitHub repository URL
3. Wait for ingestion (indexing takes 30s-2min depending on repo size)
4. Start chatting with your codebase

### For Private Repositories
1. Sign up/login via Clerk
2. **Connect GitHub:** Navigate to "Add Repository" and set up your Personal Access Token
   - Generate a PAT from GitHub Settings → Developer settings → Personal access tokens
   - Required scope: `repo` (full control of private repositories)
3. Add your private repository URL
4. Wait for ingestion with authenticated cloning
5. Start chatting with your codebase

### Repository Management
- **View all repositories:** Navigate to "Cloned Repos" to see all ingested repositories
- **Delete repositories:** Click delete to remove repo from database, vector store, and cleanup temporary files
- **Chat history:** Access previous conversations (last 10 per repository)
- **Switch repositories:** Select different repos from the dropdown in chat interface

## Architecture  

**Ingestion Flow:**
1. **Repository Validation:** Check GitHub API for privacy status (uses PAT if available)
2. **Clone Repository:** GitPython clones to temporary directory with authentication for private repos
3. **File Parsing:** Scan 15+ file types, skip exclusion patterns (`node_modules`, `.git`, etc.)
4. **Encoding Detection:** Use chardet for robust file reading across different encodings
5. **Language-Aware Splitting:** Apply custom text splitters based on file type (Python, JS, Go, Java, Rust, Markdown, Terraform, YAML, generic)
6. **Embedding Generation:** 
   - Dense embeddings: `sentence-transformers/all-MiniLM-L6-v2`
   - Sparse embeddings: `Qdrant/bm25`
7. **Vector Storage:** Store in Qdrant with hybrid retrieval mode
8. **Metadata Storage:** Save repository info, file count, chunk count, ingestion timestamp to MongoDB
9. **Cleanup:** Removes temporary cloned files

**Chat Flow:**
1. **User Query:** Receive question with repository context
2. **Vector Retrieval:** Hybrid search in Qdrant (dense + sparse) for relevant code chunks
3. **Smart Prioritization:** Boost README/package.json for broad architectural questions
4. **Context Building:** Assemble retrieved chunks with metadata
5. **LLM Processing:** Send to Ollama llama3.2 (cached on startup for performance)
6. **Response Delivery:** Return AI response to user
7. **History Storage:** Save conversation to MongoDB with timestamp

**GitHub Integration Flow:**
1. **Token Storage:** User provides GitHub PAT → Validated and stored in MongoDB (per-user)
2. **Privacy Detection:** Before cloning, GitHub API checks if repo is private
3. **Authenticated Cloning:** Use stored PAT for private repository access
4. **Connection Management:** Users can connect/disconnect GitHub accounts

**Deletion Flow:**
1. Remove repository metadata from MongoDB
2. Delete vector collection from Qdrant
3. Remove all associated chat history
4. Cleanup temporary files (if any)

## API Endpoints

### Repository Management
- `POST /api/ingest` - Ingest a new repository
  - Body: `{ "repo_url": "https://github.com/user/repo" }`
  - Returns: Ingestion status with file/chunk counts
  - Auth: Required (Clerk)

- `GET /api/repositories` - List all user's repositories
  - Returns: Array of repositories with metadata (name, ingestion date, file count, chunk count, privacy status)
  - Auth: Required (Clerk)

- `DELETE /api/repositories/{repo_id}` - Delete a repository
  - Returns: Success confirmation
  - Auth: Required (Clerk)

### Chat
- `POST /api/chat` - Send a chat message
  - Body: `{ "message": "string", "repository_name": "string" }`
  - Returns: AI response with sources
  - Auth: Required (Clerk)

- `GET /api/chat/history/{repository_name}` - Get chat history
  - Returns: Last 10 conversations for the repository
  - Auth: Required (Clerk)

### GitHub Integration
- `POST /api/github/connect` - Store GitHub Personal Access Token
  - Body: `{ "github_token": "ghp_..." }`
  - Returns: Connection success
  - Auth: Required (Clerk)

- `POST /api/github/disconnect` - Remove GitHub connection
  - Returns: Disconnection success
  - Auth: Required (Clerk)

- `GET /api/github/status` - Check GitHub connection status
  - Returns: `{ "connected": boolean, "has_token": boolean }`
  - Auth: Required (Clerk)

### Health
- `GET /health` - Health check endpoint
  - Returns: Service status
  - Auth: Not required

## Project Structure

```
InfraLens/
├── app/
│   ├── backend/
│   │   ├── core/
│   │   │   ├── auth.py              # Clerk authentication middleware
│   │   │   ├── database.py          # MongoDB connection
│   │   │   └── embeddings.py        # Embedding model creation
│   │   ├── models/
│   │   │   └── schemas.py           # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── ingestion.py         # Repository cloning, parsing, embedding
│   │   │   ├── chat_service.py      # LLM integration, vector retrieval
│   │   │   └── user_service.py      # User management, GitHub token handling
│   │   ├── main.py                  # FastAPI app with all endpoints
│   │   └── requirements.txt         # Python dependencies
│   └── frontend/
│       └── src/
│           ├── components/
│           │   └── GitHubTokenSetup.tsx  # GitHub OAuth token UI
│           ├── features/
│           │   └── auth/pages/           # SignIn, SignUp pages
│           ├── layouts/                  # App layout structure
│           ├── pages/
│           │   ├── LandingPage.tsx       # Public homepage
│           │   ├── ChatPage.tsx          # Chat interface
│           │   ├── AddRepo.tsx           # Repository ingestion
│           │   └── ClonedRepos.tsx       # Repository list/management
│           └── services/                 # API client
├── docker-compose.yml                    # MongoDB + Qdrant setup
└── agent/                                # Python virtual environment
```

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

## To be Implemented

- **API rate limiting** - No request throttling implemented
- **Billing integration** - No usage tracking or payment system

<!-- ## Known Issues

- Chat history loads but pagination not implemented (shows last 10 chats)
- No progress indicator during repository ingestion
- Error handling for network failures needs improvement 
- Large codebases (>5000 files) may take significant time to ingest
- Only English language support in LLM -->

## License

MIT