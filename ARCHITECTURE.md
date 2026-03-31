# InfraLens Architecture Documentation

This document provides a detailed breakdown of InfraLens's multi-tenant, workspace-based architecture, including all request flows, data isolation strategies, and integration patterns.

## Table of Contents

1. [Multi-Tenant Data Isolation](#multi-tenant-data-isolation)
2. [Authorization Flow](#authorization-flow)
3. [Ingestion Flow](#ingestion-flow)
4. [Chat Flow](#chat-flow)
5. [GitHub Integration Flow](#github-integration-flow)
6. [Deletion Flow](#deletion-flow)
7. [Organization Management Flow](#organization-management-flow)
8. [Subscription & Billing Flow](#subscription--billing-flow)

---

## Multi-Tenant Data Isolation

InfraLens implements complete tenant isolation at the application layer, ensuring that personal and organization workspaces maintain strict data boundaries.

### Personal Workspace (`user_{user_id}_{repo_name}`)

```
JWT Claims:  { user_id: "user_123", org_id: null }
Qdrant:      user_user_123_repo_name (collection)
MongoDB:     { user_id: "user_123", org_id: null }
Access:      Only the owning user
```

**Characteristics:**
- Data accessible only by the authenticated user
- Collections prefixed with `user_` in Qdrant
- MongoDB documents filtered by user_id
- No shared access (single-tenant mode)

### Organization Workspace (`org_{org_id}_{repo_name}`)

```
JWT Claims:  { user_id: "user_456", org_id: "org_acmecorp", org_role: "org:member" }
Qdrant:      org_org_acmecorp_repo_name (collection)
MongoDB:     { org_id: "org_acmecorp", user_id: "org_owner_id" }
Access:      All members with valid org_role in Clerk + verified in MongoDB
```

**Characteristics:**
- Data accessible by all members with valid org_role
- Collections prefixed with `org_` in Qdrant
- MongoDB documents filtered by org_id
- Shared access across team members (multi-tenant within org)

### Key Design Principle: JWT-First Authority

**Clerk JWT is the source of truth for organization membership.** MongoDB member list is treated as a cache for consistency checks. This design ensures:

- **Immediate access for new members:** Invited members get instant access upon JWT refresh (no sync delay)
- **Immediate removal on member deletion:** Member immediately loses access once JWT is revoked by Clerk
- **No stale data in cross-tenant queries:** All authorization checks performed against JWT before querying data
- **Scalability:** No need for real-time sync between Clerk and MongoDB; periodic consistency checks are sufficient

---

## Authorization Flow

All requests follow this strict authorization pattern:

```
User Request
    ↓
Extract JWT (org_id, org_role, user_id from Clerk)
    ↓
Check Workspace Type:
  ├─ Personal: org_id is null? 
  │   └─ Verified: user_id must match resource owner
  └─ Organization: org_role in ["org:owner", "org:admin", "org:member"]?
      └─ Verified: org_id must match resource
    ↓
Query MongoDB with tenant filter
  ├─ Personal: { user_id: "user_123", org_id: null }
  └─ Organization: { org_id: "org_xyz" }
    ↓
Query Qdrant collection (tenant-prefixed name ensures isolation)
    ↓
Audit: Log interaction with both user_id and org_id
    ↓
Return tenant-scoped data only
```

### Authorization Checks

**Personal Workspace Requests:**
1. Extract user_id from JWT
2. Verify JWT has no org_id or org_id is null
3. Ensure requesting user_id matches resource owner
4. Query MongoDB with filter: `{ user_id: <requesting_user_id> }`

**Organization Workspace Requests:**
1. Extract org_id and org_role from JWT
2. Verify org_role is one of: `org:owner`, `org:admin`, `org:member`
3. Query MongoDB with filter: `{ org_id: <org_id> }`
4. Double-check member exists in MongoDB (consistency cache)

**Audit Trail:**
- All chat interactions logged with both user_id and org_id
- Enables per-team and per-org analytics
- Tracks workspace usage for quota enforcement

---

## Ingestion Flow

### Step 1: Repository Validation

- Check GitHub API for privacy status (uses user's PAT if available)
- Determine target workspace:
  - If `org_id` provided: validate user is org member
  - If no `org_id`: ingest to personal workspace (org_id=null)

### Step 2: Clone Repository

- GitPython clones repository to temporary directory
- For private repos: use stored GitHub PAT from user's account (individual token, not team-shared)
- Preserve .git metadata for commit history (optional future enhancement)

### Step 3: File Parsing

- Scan all files recursively
- Support 15+ file types: `.py`, `.ts`, `.js`, `.tsx`, `.jsx`, `.md`, `.java`, `.go`, `.sh`, `.rs`, `.c`, `.cpp`, `.tf`, `.yml`, `.yaml`, `.json`, `.txt`, `.html`, `.css`, `.sql`
- Automatically skip exclusion patterns: `node_modules`, `.git`, `venv`, `__pycache__`, `dist`, `build`, `target`, `.next`, `.vscode`, `.idea`
- Detect file encoding robustly with chardet (handles UTF-8, ISO-8859-1, etc.)

### Step 4: Language-Aware Code Splitting

Apply custom text splitters based on file type:
- **Python:** Split on function/class boundaries
- **JavaScript/TypeScript:** Split on function/class boundaries
- **Go:** Split on function boundaries
- **Java:** Split on class/method boundaries
- **Rust:** Split on function/trait boundaries
- **Markdown:** Split on heading hierarchy
- **Terraform/YAML:** Split on resource/block boundaries
- **Generic/Text:** Split on paragraph with overlap

**Chunking Strategy:**
- Target chunk size: 1000 tokens
- Overlap: 200 tokens (preserve context across chunks)
- Preserve metadata: filename, line numbers, language

### Step 5: Embedding Generation

**Dense Embeddings:**
- Model: `sentence-transformers/all-MiniLM-L6-v2`
- Dimension: 384
- Speed: Fast inference; suitable for real-time retrieval

**Sparse Embeddings:**
- Model: `Qdrant/bm25`
- Type: Keyword-based (BM25 algorithm)
- Use case: Exact term matching, supplement dense search

**Hybrid Approach:**
- Dense embeddings capture semantic similarity
- Sparse embeddings ensure keyword matches aren't missed
- Combined retrieval maximizes relevance

### Step 6: Vector Storage

- Store in Qdrant with tenant-scoped collection name:
  - Personal: `user_{user_id}_{repo_name}` 
  - Organization: `org_{org_id}_{repo_name}`
- Enable hybrid retrieval mode (dense + sparse search)
- Store metadata with each vector:
  - `filename`, `line_start`, `line_end`
  - `repo_name`, `user_id` or `org_id` (tenant marker)
  - `file_type`, `language`
  - `chunk_index` (order within file)

### Step 7: Metadata Storage

- Save to MongoDB collection `repositories`:
  - `repo_name`, `repo_url`, `repo_id`
  - `user_id` (for personal) or `org_id` (for organization)
  - `privacy_status` (public/private)
  - `file_count`, `chunk_count`
  - `ingestion_date`, `last_updated`
  - `language_breakdown` (% Python, % JS, etc.)

### Step 8: Cleanup & Quota Tracking

- Remove temporary cloned directory
- Track monthly ingestion count in MongoDB:
  - Document: `{ _id: "usage_2026-03_user_123", count: 2 }`
  - Or: `{ _id: "usage_2026-03_org_acmecorp", count: 5 }`
- Check against subscription plan limits:
  - Free: 5 repos/month (personal only)
  - Pro: 20 repos/month (personal only)
  - Team: 50 repos/month (organization)
- Reject ingestion if quota exceeded

---

## Chat Flow

### Step 1: User Query

- Receive chat message with repository context
- Extract tenant scope from JWT (org_id or user_id)
- Validate user has access to specified repository in their workspace

### Step 2: Vector Retrieval

- Query **only** the tenant-scoped Qdrant collection
- Hybrid search with both dense and sparse embeddings:
  - Dense: Semantic similarity search
  - Sparse: BM25 keyword matching
- Retrieve top-K relevant chunks (default: 5-10 chunks)

**Smart Prioritization for Broad Questions:**
- If user asks architectural question without specific file: prioritize README, package.json, main entry point
- Language detection: prefer files matching codebase's primary language

### Step 3: Context Building

- Assemble retrieved chunks with metadata (filename, line numbers)
- Build prompt with:
  - Original user question
  - Retrieved code context with source attribution
  - Repository name for context
- **Critical:** Respect tenant boundaries—no cross-tenant chunk leakage possible (collection-level isolation)

### Step 4: LLM Processing

- Send constructed prompt to Groq API (cloud LLM)
- Include system prompt guiding response format:
  - Explain code clearly
  - Reference specific file locations
  - Suggest related files if relevant
- Receive AI response with reasoning

### Step 5: Response Delivery

- Return AI response with source references:
  - Filename and line numbers for each source chunk
  - Allow user to click and jump to code
- Include confidence indicators if applicable

### Step 6: History Storage

- Save conversation to MongoDB collection `chat_history`:
  - `repository_name`, `user_id` or `org_id` (tenant marker)
  - `message` (user question), `response` (AI answer)
  - `sources` (array of retrieved chunks)
  - `timestamp`
- For organization workspace:
  - Conversation accessible to all org members with org access
  - Prevents duplicate LLM calls for same question
  - Enables team knowledge sharing

**History Retention:**
- Keep last 10 conversations per repository per workspace
- Cleanup older conversations automatically
- Preserve org conversation history even after member removal

---

## GitHub Integration Flow

### Step 1: Token Storage

- User provides GitHub Personal Access Token in settings
- Validate token against GitHub API (test if valid)
- Store **encrypted** in MongoDB (AES-256 encryption):
  ```json
  {
    "_id": "user_123",
    "github_token_encrypted": "<encrypted_token>",
    "github_connected_at": "2026-03-31",
    "github_token_validated": true
  }
  ```
- **Critical:** Per-user storage, NOT shared across organization
- Each org member independently manages their own GitHub connection

### Step 2: Privacy Detection

- Before cloning any repository:
  - Check GitHub API if repo is private: `GET /repos/{owner}/{repo}`
  - Use authenticated request if user has connected GitHub
  - If private repo detected without valid PAT: show alert to user
- Cache privacy status in MongoDB to avoid repeated API calls

### Step 3: Authenticated Cloning

- For private repositories:
  - Use user's stored GitHub PAT as authentication
  - GitPython handles credentials transparently
  - Token scoped to individual user (e.g., can't access repos user didn't authorize)
- For public repositories:
  - Clone without authentication (GitHub allows public clones)
  - Still uses user's PAT if available (for higher rate limits)

### Step 4: Connection Management

- Users can connect/disconnect GitHub accounts anytime
- **On Disconnect:**
  - Delete encrypted token from MongoDB
  - Prevent new ingestions requiring private repo access
  - Existing ingested private repos remain accessible (already indexed)
  - Future ingestions default to public repos only

**Rate Limiting:**
- GitHub API rate limit: 60 req/hour (unauthenticated), 5000 req/hour (authenticated)
- With team of 5 members: 25,000 requests/hour available
- Sufficient for typical usage patterns

---

## Deletion Flow

### Step 1: Authorization Check

- Verify requesting user has permission to delete:
  - **Personal workspace:** user_id must match repository owner
  - **Organization workspace:** user_role must be "org:admin" or "org:owner"
- Reject deletion if unauthorized

### Step 2: Database Cleanup

- Find repository in MongoDB using `repo_id`
- Remove repository document from `repositories` collection
- Update any related documents (e.g., remove from organization stats)

### Step 3: Vector Cleanup

- Identify Qdrant collection name:
  - Personal: `user_{user_id}_{repo_name}`
  - Organization: `org_{org_id}_{repo_name}`
- Delete entire collection (removes all vectors/embeddings)
- Verify deletion successful

### Step 4: Chat History Cleanup

- Find all chat history in MongoDB:
  - Query: `{ repository_name: "repo_name", user_id: "user_id" }` OR `{ repository_name: "repo_name", org_id: "org_id" }`
- Delete all matching chat documents
- Option: Archive history for audit (future enhancement)

### Step 5: File Cleanup

- Remove temporary cloned directory (if it still exists)
- Clean any large cache files related to repository

**Transactional Safety:**
- Modern MongoDB: use multi-document transactions for atomicity
- If any step fails, log error and notify admin
- Orphaned vectors tolerable (manual cleanup); orphaned MongoDB docs are not

---

## Organization Management Flow

### Step 1: Organization Creation

- User initiates org creation in frontend
- Backend calls Clerk API to create organization:
  ```
  POST /api/organizations
  Body: { "name": "Acme Corp", "slug": "acme-corp" }
  ```
- Clerk automatically assigns creator as `org:owner`
- Backend creates corresponding record in MongoDB:
  ```json
  {
    "_id": "org_acmecorp",
    "clerk_org_id": "org_acmecorp",
    "owner_id": "user_123",
    "created_at": "2026-03-31",
    "members": [{ "user_id": "user_123", "role": "org:owner" }]
  }
  ```

### Step 2: Member Invitation

- Owner/Admin navigates to Settings → Team Members → Invite
- Enters team member email address
- Backend calls Clerk API:
  ```
  POST /api/organizations/{org_id}/invitations
  Body: { "email": "teammate@example.com", "role": "org:member" }
  ```
- Clerk generates invitation and sends email with invite link
- Invitation state managed entirely by Clerk

### Step 3: Access Grant

- Invited user clicks email link and accepts invitation
- Clerk updates user's JWT to include:
  ```json
  {
    "org_id": "org_acmecorp",
    "org_role": "org:member",
    "org_permissions": ["view_repos", "chat"]
  }
  ```
- Backend verifies JWT org_role (source of truth)
- MongoDB consistency check: confirm user_id in members list
- Grant immediate access to organization repositories and chat
- User can now switch to org workspace in UI

### Step 4: Member Removal

- Owner/Admin removes member from organization settings
- Backend calls Clerk API:
  ```
  DELETE /api/organizations/{org_id}/memberships/{user_id}
  ```
- Clerk revokes user's org_role from JWT
- User's next API request fails authorization check
- MongoDB cleanup happens asynchronously:
  - Remove user from org's members list
  - Mark user's chat contributions with `archived_member: true`

**Important:** Shared chat history remains intact after member removal, but member cannot trigger new requests.

---

## Subscription & Billing Flow

### Step 1: Plan Selection

- User selects Free, Pro, or Team plan on pricing page
- Free plan: automatic (no payment required)
- Pro/Team: triggered by checkout

**Plan Features:**
```
Free Plan:
  ├─ Personal workspace only
  ├─ 5 repos/month limit
  ├─ Hybrid vector search
  ├─ Chat history
  └─ GitHub PAT support

Pro Plan (₹100/month):
  ├─ Personal workspace only
  ├─ 20 repos/month limit
  ├─ All Free features
  └─ Priority support

Team Plan (₹250/month):
  ├─ Organization workspace enabled
  ├─ 50 repos/month limit
  ├─ Team member invitations (up to 5)
  ├─ Shared repositories & chat
  ├─ All Pro features
  └─ Organization stats & analytics
```

### Step 2: Subscription Creation

- Frontend calls `/api/payments/create-subscription` with selected plan:
  ```json
  {
    "plan": "pro"  // or "team"
  }
  ```
- Backend identifies/creates Razorpay customer:
  - Check if customer exists by email
  - Create if new: `POST /customers` to Razorpay
- Backend creates subscription:
  ```
  POST /subscriptions
  Body: {
    "customer_id": "cust_xyz",
    "plan_id": "plan_id_pro",
    "quantity": 1,
    "total_count": null  // auto-renew indefinitely
  }
  ```
- Returns subscription object with `subscription_id` and checkout link

### Step 3: Checkout

- Backend returns Razorpay `subscription_id` to frontend
- Frontend opens Razorpay Checkout modal with subscription details
- Modal displays:
  - Plan name and price
  - Billing frequency (monthly)
  - Contact fields (pre-filled with user email)

### Step 4: Payment

- User enters card details in Razorpay modal
- Razorpay processes payment (3D Secure if required)
- On success: Razorpay triggers `payment.captured` webhook
- On failure: Frontend shows error, user can retry

### Step 5: Webhook Handling

- Razorpay sends webhook events to `/api/payments/webhook`:
  - `payment.captured`: Payment successful
  - `subscription.activated`: Subscription started/renewed
  - `subscription.halted`: Subscription on hold (payment failed)
  - `subscription.cancelled`: User cancelled subscription

**Webhook Processing:**
```python
1. Verify HMAC-SHA256 signature (Razorpay-Signature header)
2. Extract event data (payment_id, subscription_id)
3. Update MongoDB:
   {
     "_id": "user_123",
     "subscription": {
       "plan": "pro",
       "status": "active",
       "razorpay_subscription_id": "sub_xyz",
       "razorpay_customer_id": "cust_xyz",
       "current_period_start": "2026-02-28",
       "current_period_end": "2026-03-31"
     }
   }
4. Handle duplicates gracefully (idempotent updates)
5. Log event for audit trail
```

### Step 6: Entitlement Check

On every API request:

```python
# Get user's subscription from MongoDB
subscription = db.users.find_one({ "_id": user_id })

if subscription["plan"] == "free":
    allowed_workspaces = ["personal"]
    monthly_ingestion_limit = 5
elif subscription["plan"] == "pro":
    allowed_workspaces = ["personal"]
    monthly_ingestion_limit = 20
elif subscription["plan"] == "team":
    allowed_workspaces = ["personal", "org"]
    monthly_ingestion_limit = 50

# Check if subscription expired
if subscription["current_period_end"] < now:
    subscription["plan"] = "free"  # Fall back to Free tier
    subscription["status"] = "expired"
    db.users.update_one(
        { "_id": user_id },
        { "$set": { "subscription": subscription } }
    )

# Enforce workspace restrictions
if org_id and subscription["plan"] != "team":
    raise PermissionError("Organization workspace requires Team plan")

# Check ingestion quota
monthly_key = f"usage_{current_month}_{user_id or org_id}"
usage = db.usage.find_one({ "_id": monthly_key })
if usage["count"] >= monthly_ingestion_limit:
    raise QuotaExceededError(f"Limit: {monthly_ingestion_limit}/month")
```

### Billing Details

- **Billing Cycle:** Monthly (starts on subscription date, auto-renews)
- **Currency:** Indian Rupees (₹)
- **Payment Method:** Card (Visa, Mastercard, etc.)
- **Refunds:** 7-day money-back guarantee (processed manually)
- **Cancellation:** Immediate (no pro-rata refunds)
- **Renewal:** Automatic on billing date; email reminder sent 3 days before
- **Failed Payments:** 3 retry attempts over 5 days before halting

**Idempotent Webhook Handling:**
- Razorpay retries failed webhooks up to 5 times
- Track processed webhook IDs in MongoDB to prevent duplicates
- Use `upsert` operations in database updates (idempotent)

---

## Data Security & Compliance

### Encryption

- **At Rest:** MongoDB + Qdrant data encrypted (if managed service)
- **In Transit:** TLS 1.2+ for all API communication
- **Sensitive Data:** GitHub tokens, Razorpay IDs encrypted in MongoDB

### Access Control

- **Role-Based:** Owner, Admin, Member roles with granular permissions
- **API Keys:** Clerk JWT + internal service keys (rotated regularly)
- **Rate Limiting:** 100 requests/minute per user (prevent abuse)

### Audit & Logging

- All requests logged with user_id, org_id, timestamp, action
- Chat interactions tracked for compliance reporting
- Deletion events archived for audit trail
- Monthly reports available in org settings

---

## Monitoring & Observability

### Key Metrics

- **Ingestion Success Rate:** % of successful repo ingestion attempts
- **Chat Latency:** p50/p95/p99 response times
- **Vector Retrieval Relevance:** User feedback on context quality
- **Subscription Churn:** % of users keeping active subscriptions
- **API Error Rates:** 4xx and 5xx errors by endpoint

### Logging

- **Application Logs:** FastAPI request/response logs
- **Database Logs:** MongoDB slow query logs, Qdrant indexing logs
- **Webhook Logs:** Razorpay webhook processing with status
- **Auth Logs:** JWT validation failures, org access denials

### Alerts

- Ingestion failure threshold exceeded
- Chat response latency > 5 seconds
- Vector database unavailable
- Webhook processing backlog > 100
- MongoDB connection pool exhaustion

---

<!-- ## Future Enhancements

1. **Commit History Timeline:** Chat with git blame, see evolving code
2. **Code Review Assistant:** AI review of pull request diffs
3. **Multi-Language Support:** Expand supported file types
4. **Real-Time Collaboration:** Simultaneous multi-user chat (WebSocket)
5. **API Rate Limiting Per User:** Prevent abuse at a per-user level
6. **Advanced Search:** Filters (by date, language, author) in chat
7. **Batch Processing:** Background jobs for large ingestions
8. **Analytics Dashboard:** Org-level insights on code changes, chat trends -->
