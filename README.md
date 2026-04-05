## InfraLens: The AI-Native Project Analysis Platform
AI-powered codebase analysis platform with workspace-based team collaboration. Chat with your GitHub repositories using natural language — solo or with your team.

## What It Does
- Clone and analyze both **public and private** GitHub repositories with Personal Access Token integration
- Index code using hybrid vector search (dense + sparse embeddings) with support for 15+ file types
- Chat with your codebase using LLM (Groq) with context-aware retrieval
- **Multi-tenant architecture** with isolated personal & organization workspaces
- **Team collaboration** with role-based access control (Admin, Members)
- **Shared memory spaces** where team members access common ingested repositories and indexed code
- Full repository management (list, view metadata, delete with cleanup)
- GitHub account connection/disconnection for seamless private repo access
- Subscription-based plans (Free, Pro, Team) with usage quotas

## Features

### 🔐 Authentication & Multi-Tenancy
- Secure user authentication via Clerk with organization support
- **Personal Workspace:** Individual user repository isolation and management
- **Organization Workspace:** Multi-member team space with shared repositories and indexed memory
- **Role-Based Access Control:** Organization Owner, Admin, and Member roles with granular permissions
- **JWT-Based Tenancy:** Clerk JWT extracts org context; MongoDB cross-checks for consistency
- GitHub Personal Access Token integration for private repositories (per-user storage)

### 👥 Team Collaboration (Organization Workspaces)
- **Organization Creation:** Users can create organizations and invite team members
- **Member Invitations:** Send invites via email with automatic role assignment (Member roles)
- **Shared Repositories:** Ingest public/private repos to organization workspace for team access
- **Unified Memory:** All team members search over the same ingested repository index
- **Member Management:** View team members, their roles, and organization quota usage
- **Access Audit:** Clerk ensures only invited members with valid org_role can access org resources

### 📦 Repository Support
- **Public repositories:** Direct cloning via URL
- **Private repositories:** GitHub PAT authentication with automatic privacy detection
- **Supported file types:** `.py`, `.ts`, `.js`, `.tsx`, `.jsx`, `.md`, `.java`, `.go`, `.sh`, `.rs`, `.c`, `.cpp`, `.tf`, `.yml`, `.yaml`, `.json`, `.txt`, `.html`, `.css`, `.sql`
- **Intelligent exclusions:** Automatically skips `node_modules`, `.git`, `venv`, `__pycache__`, `dist`, `build`, `target`, `.next`, `.vscode`, `.idea`

### 🤖 Smart AI Chat
- Cloud LLM (Groq) for fast inference and scalability
- Hybrid vector search combining dense and sparse embeddings
- Context-aware retrieval with smart prioritization (README, package.json for broad questions)
- Language-aware code splitting for Python, JavaScript, TypeScript, Go, Java, Rust, Markdown, Terraform, YAML
- Per-repository conversation history (last 10 chats retrievable)
- **Org-scoped chat:** Conversation history visible to all team members in organization workspace

### 💳 Subscription & Billing
- **Free Plan:** Personal workspace with monthly limits
- **Pro Plan (₹100/month):** Enhanced quota for individual developers
- **Team Plan (₹250/month):** Organization workspace with higher limits for team collaboration
- Razorpay integration with webhook-based payment processing
- Automatic subscription renewal with expiry-based entitlement checking

### Repository Management
- List all ingested repositories with metadata (ingestion date, file/chunk counts, privacy status, workspace scope)
- Delete repositories with full cleanup (removes from MongoDB, Qdrant, and temporary files)
- Repository status tracking and GitHub connection monitoring
- **Quota Enforcement:** Monthly per-tenant (user or org) limits tracked and enforced

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
- Groq (Cloud LLM API)
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
- Groq API key (for LLM access)
- Clerk account (for authentication)
- GitHub Personal Access Token (optional, for private repositories)

## Usage

### Personal Workspace (For Individual Users)

#### For Public Repositories
1. Sign up/login via Clerk
2. Add a GitHub repository URL
3. Wait for ingestion (indexing takes 30s-2min depending on repo size)
4. Start chatting with your codebase

#### For Private Repositories
1. Sign up/login via Clerk
2. **Connect GitHub:** Navigate to "Add Repository" and set up your Personal Access Token
   - Generate a PAT from GitHub Settings → Developer settings → Personal access tokens
   - Required scope: `repo` (full control of private repositories)
3. Add your private repository URL
4. Wait for ingestion with authenticated cloning
5. Start chatting with your codebase

### Organization Workspace (For Team Collaboration)

![Data Modal](./images/data%20modal.png)

#### Create an Organization
1. Sign up/login via Clerk
2. Navigate to Settings → Create Organization
3. Provide organization name and details
4. You become the Organization Owner

#### Invite Team Members
1. Navigate to Settings → Team Members → Invite
2. Enter team member email address
3. Send invitation (members receive email with invite link)
4. Once accepted, member can:
   - View all organization repositories
   - Chat with org-indexed code
   - Access shared chat history

#### Ingest Repository to Organization
1. Select Organization from workspace switcher (top-left)
2. Click "Add Repository"
3. Provide repository URL (public or private)
4. Wait for ingestion—all team members can now search and query this repository
5. Chat history is shared across all org members

#### Member Roles & Permissions
- **Owner:** Created the organization, full access to settings and billing
- **Admin:** Can manage members, invite/remove, and manage repositories
- **Member:** Can view repositories, chat, and access shared conversation history

#### View Organization Quota
1. Navigate to Settings → Team Members → Organization Stats
2. See monthly ingestion quota usage across all team members
3. Upgrade to Team plan for higher limits

### Workspace Switching
- Use the workspace switcher (top-left header) to switch between Personal workspace and any organization you're a member of
- Organization selection persists in browser—your workspace choice is remembered
- All chat history and repositories are scoped to the active workspace

## Repository Management
- **View all repositories:** Navigate to "Cloned Repos" to see all ingested repositories in active workspace
- **Delete repositories:** Click delete to remove repo from database, vector store, and cleanup temporary files
- **Chat history:** Access previous conversations (last 10 per repository, team-visible if in org workspace)
- **Switch repositories:** Select different repos from the dropdown in chat interface

## Architecture

InfraLens uses a **multi-tenant, workspace-based architecture** with complete data isolation between personal and organization workspaces.

![InfraLens Architecture](./images/infralens%20architecture.jpg)

### Core Design

**Multi-Tenant Isolation**
- **Personal Workspace:** Data scoped by `user_id`; accessible only to the owning user
- **Organization Workspace:** Data scoped by `org_id`; accessible to all org members with valid roles
- **Collection Naming:** Tenant-prefixed collections (`user_*` / `org_*`) in Qdrant ensure strict data boundaries

**Authorization Model (JWT-First)**
- Clerk JWT is the source of truth for organization membership
- All requests extract tenant scope (`user_id` or `org_id`) from JWT
- MongoDB member list acts as consistency cache, not primary authority
- Result: Immediate member access/removal with no sync delays

**Data Layer**
- **MongoDB:** User data, repositories, chat history (tenant-filtered)
- **Qdrant:** Vector embeddings in tenant-prefixed collections (hybrid search: dense + sparse)
- **Clerk:** Organization and role management (JWT provider)

### High-Level Request Flow

```
User Request (with Clerk JWT)
    ↓
Extract tenant scope (user_id or org_id, org_role)
    ↓
Auth Check: Verify ownership or org membership
    ↓
Query MongoDB & Qdrant with tenant filter
    ↓
Return tenant-scoped data only
```

### Feature Layers

| Layer | Responsibility |
|-------|-----------------|
| **Ingestion** | Clone repo → parse files → generate embeddings → store in tenant collection |
| **Chat** | Retrieve tenant-scoped chunks → send to Groq → return answer with sources |
| **GitHub** | Per-user PAT storage; private repo authentication |
| **Organizations** | Create orgs, invite members via Clerk, manage roles |
| **Billing** | Razorpay subscriptions; Free/Pro/Team plan entitlements |

### For Deeper Understanding

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed documentation on:
- Authorization & ingestion flows
- Chat & vector retrieval pipelines  
- GitHub integration & token management
- Organization & member lifecycle
- Subscription & billing workflows

## API Endpoints

### Repository Management
- `POST /api/ingest` - Ingest a new repository
  - Body: `{ "repo_url": "https://github.com/user/repo", "org_id": "optional_org_id" }`
  - Returns: Ingestion status with file/chunk counts
  - Scope: Personal workspace if org_id omitted; organization workspace if org_id provided
  - Auth: Required (Clerk)

- `GET /api/repositories` - List user's repositories
  - Returns: Array of repositories scoped to active workspace (personal or org)
  - Includes: name, ingestion date, file count, chunk count, privacy status, workspace scope
  - Auth: Required (Clerk)

- `DELETE /api/repositories/{repo_id}` - Delete a repository
  - Returns: Success confirmation
  - Auth: Required (Clerk; must have ownership/admin access)

### Chat (Tenant-Aware)
- `POST /api/chat` - Send a chat message
  - Body: `{ "message": "string", "repository_name": "string", "org_id": "optional" }`
  - Returns: AI response with sources
  - Scope: Searches only within active workspace (personal or org)
  - Auth: Required (Clerk)

- `GET /api/chat/history/{repository_name}` - Get chat history
  - Query: `?org_id=optional_org_id`
  - Returns: Last 10 conversations scoped to workspace
  - Org members can view shared conversation history
  - Auth: Required (Clerk)

### Organization Management
- `POST /api/org/create` - Create a new organization
  - Body: `{ "org_name": "string", "org_display_name": "string" }`
  - Returns: Organization details and Clerk org_id
  - Auth: Required (Clerk)

- `GET /api/org/list` - List user's organizations
  - Returns: All orgs user is member of with role (owner, admin, member)
  - Auth: Required (Clerk)

- `GET /api/org/{org_id}/members` - List organization members
  - Returns: Array of members with email, role, and join date
  - Auth: Required (Clerk; must be org member)

- `POST /api/org/{org_id}/invite` - Send member invitation
  - Body: `{ "email": "member@example.com" }`
  - Returns: Invitation confirmation
  - Auth: Required (Clerk; must be owner or admin)

- `DELETE /api/org/{org_id}/member/{user_id}` - Remove member from organization
  - Returns: Removal confirmation
  - Auth: Required (Clerk; must be owner or admin)

- `GET /api/org/{org_id}/quota` - Get organization usage quota
  - Returns: `{ "month": "2026-03", "repos_ingested": 5, "limit": 20, "usage_percent": 25 }`
  - Auth: Required (Clerk; must be org member)

### GitHub Integration
- `POST /api/github/connect` - Store GitHub Personal Access Token
  - Body: `{ "github_token": "ghp_..." }`
  - Returns: Connection success
  - Note: Token stored per-user, not shared across organization
  - Auth: Required (Clerk)

- `POST /api/github/disconnect` - Remove GitHub connection
  - Returns: Disconnection success
  - Auth: Required (Clerk)

- `GET /api/github/status` - Check GitHub connection status
  - Returns: `{ "connected": boolean, "has_token": boolean }`
  - Auth: Required (Clerk)

### Health & Status
- `GET /health` - Health check endpoint
  - Returns: Service status
  - Auth: Not required

### Payment & Billing
- `POST /api/payments/create-subscription` - Create subscription
  - Body: `{ "plan": "pro" | "team" }`
  - Returns: Razorpay subscription ID and checkout details
  - Auth: Required (Clerk)

- `GET /api/payments/subscription-status` - Get subscription status
  - Returns: `{ "plan", "status", "current_period_end", "razorpay_subscription_id" }`
  - Auth: Required (Clerk)

- `POST /api/payments/webhook` - Razorpay webhook handler
  - Webhook events: `subscription.activated`, `subscription.halted`, `subscription.cancelled`, `payment.captured`, `payment.failed`
  - Auto-updates user subscription status in MongoDB
  - Auth: Signature verification (not JWT)

## Project Structure

```
InfraLens/
├── app/
│   ├── backend/
│   │   ├── core/
│   │   │   ├── auth.py              # Clerk JWT auth with org context extraction
│   │   │   ├── database.py          # MongoDB connection
│   │   │   └── embeddings.py        # Embedding model creation
│   │   ├── models/
│   │   │   └── schemas.py           # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── ingestion.py         # Repository cloning, parsing, embedding
│   │   │   ├── chat_service.py      # LLM integration, tenant-scoped retrieval
│   │   │   ├── user_service.py      # User management, GitHub token handling
│   │   │   ├── org_service.py       # Organization management, member invitations
│   │   │   ├── payment_service.py   # Razorpay integration, subscriptions
│   │   │   └── entitlement_service.py # Plan-based feature gating
│   │   ├── main.py                  # FastAPI app with all endpoints
│   │   └── requirements.txt         # Python dependencies
│   └── frontend/
│       └── src/
│           ├── components/
│           │   ├── OrgSwitcher.tsx       # Workspace switcher (Personal/Org)
│           │   └── GitHubTokenSetup.tsx  # GitHub PAT UI
│           ├── features/
│           │   └── auth/pages/           # SignIn, SignUp pages
│           ├── layouts/                  # App layout structure
│           ├── pages/
│           │   ├── ChatPage.tsx          # Multi-tenant chat interface
│           │   ├── AddRepo.tsx           # Repository ingestion
│           │   ├── ClonedRepos.tsx       # Repository list (org-scoped)
│           │   ├── PricingPage.tsx       # Pricing & subscription
│           │   ├── PricingSuccessPage.tsx # Payment success
│           │   └── SettingsPage.tsx      # Team management & invitations
│           └── services/
│               ├── chatService.ts        # Chat API with tenant awareness
│               ├── orgService.ts         # Organization API client
│               └── paymentService.ts     # Razorpay integration
├── docker-compose.yml               # MongoDB + Qdrant setup
├── infra/                           # Terraform IaC (optional)
└── agent/                           # Python virtual environment
```

## Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- Groq API key (for LLM access)
- Clerk account (for authentication and organization management)
- GitHub Personal Access Token (optional, for private repositories)
- Razorpay account (for payment processing)

### 1. Clone and Install

```bash
git clone https://github.com/kkshivani18/InfraLens
cd InfraLens
```

### 2. Configure Clerk for Organizations

**Important:** InfraLens uses Clerk Organizations for multi-tenancy. Enable it in Clerk dashboard:

1. Go to Clerk Dashboard → Settings → Organizations
2. Enable "Organizations" feature
3. Configure organization roles:
   - `org:owner` - Full access (auto-assigned to creator)
   - `org:admin` - Management permissions
   - `org:member` - Standard access

### 3. Start Infrastructure

```bash
docker-compose up -d
```

This starts MongoDB (port 27017) and Qdrant (port 6333).

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
QDRANT_API_KEY=your_qdrant_api_key
CLERK_SECRET_KEY=your_clerk_secret_key
CLERK_API_KEY=your_clerk_api_key
CLERK_JWKS_URL=your_clerk_jwks_url
GROQ_API_KEY=your_groq_api_key
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_secret_key
RAZORPAY_PLAN_ID_PRO=pro_plan_id
RAZORPAY_PLAN_ID_TEAM=team_plan_id
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
VITE_RAZORPAY_KEY_ID=your_razorpay_key_id
```

Start frontend:
```bash
npm run dev
```

### 6. Testing Multi-Tenant Features

**Personal Workspace:** 
- Sign in as any user
- Add repositories—they'll be scoped to personal workspace
- Chat with your repositories

**Organization Workspace:**
1. Sign in as User A
2. Go to Settings → Create Organization
3. Fill org details and confirm
4. Go to Settings → Team Members → Invite
5. Enter email of User B and send invite
6. Sign in as User B
7. Accept invitation from User A
8. User B can now:
   - Switch to org workspace (top-left switcher)
   - View repos ingested by User A
   - Chat with shared repositories
   - See conversation history

## Key Features Summary

| Feature | Free Plan | Pro Plan | Team Plan |
|---------|-----------|----------|-----------|
| Personal Workspace | ✅ | ✅ | ✅ |
| Organization Workspace | ❌ | ❌ | ✅ |
| Monthly Repo Limit | 5 | 20 | 50 |
| Team Members | N/A | N/A | 5 |
| Private Repo Support | ✅ | ✅ | ✅ |
| Chat History | ✅ | ✅ | ✅ |
| Vector Search | ✅ | ✅ | ✅ |

## License

MIT