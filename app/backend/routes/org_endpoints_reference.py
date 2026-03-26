"""
REFERENCE: Organization and Tenant-Aware Endpoints

This file shows example patterns for integrating org_service helpers into FastAPI endpoints.
Copy patterns here into main.py for your specific endpoints.

Key patterns:
1. require_org_access() — validate repo ownership before access
2. check_org_quota() → increment_org_quota() — quota enforcement on ingest
3. invite_member() — seat limit + Clerk invitation
"""

from fastapi import APIRouter, Depends, HTTPException
from core.auth import get_current_user, get_org_context
from core.database import get_database
from services.org_service import (
    require_org_access,
    check_org_quota,
    increment_org_quota,
    invite_member
)
from services.ingestion import ingest_repo
from models.schemas import (
    IngestRequestWithOrg,
    ChatRequest,
    InviteRequest,
    InviteResponse,
    OrgDetailsResponse
)

router = APIRouter()

# Validate Repo Access Before Chat

@router.post("/api/chat")
async def chat(
    request: ChatRequest,
    user: dict = Depends(get_current_user),
    db: dict = Depends(get_database)
):
    """
    Chat about a repository.
    
    Validates user has access to the repo (owner of personal repo or member of org).
    Raises 403 if unauthorized, 404 if not found.
    """
    try:
        # Validate user can access this repo
        repo = await require_org_access(request.repository_name, user, db)
    except HTTPException as e:
        raise e
    
    # Build collection name based on repo tenancy
    from services.ingestion import get_collection_name
    
    if repo.get("org_id"):
        collection_name = get_collection_name("org", repo["org_id"], repo["name"])
    else:
        collection_name = get_collection_name("usr", repo["user_id"], repo["name"])
    
    # Query Qdrant with tenant-isolated collection
    from services.chat_service import get_chat_response
    response = await get_chat_response(
        message=request.message,
        collection_name=collection_name,
        user_id=user["user_id"]
    )
    
    return response


# Quota Check Before Ingest

@router.post("/api/ingest")
async def ingest(
    request: IngestRequestWithOrg,
    user: dict = Depends(get_current_user),
    db: dict = Depends(get_database)
):
    """
    Ingest a repository.
    
    If org_id is provided (team workspace), checks monthly ingestion quota.
    If None, ingests to user's personal workspace (no quota check).
    """
    org_id = request.org_id or user.get("org_id")  # explicit or from JWT
    
    # Validate user can ingest to this org (if org_id set)
    if org_id and user.get("org_id") != org_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to ingest to this org workspace"
        )
    
    # Quota check for team ingest
    if org_id:
        await check_org_quota(org_id, db)  
    
    # Perform ingestion
    result = await ingest_repo(
        repo_url=request.repo_url,
        user_id=user["user_id"],
        org_id=org_id
    )
    
    # Increment quota on success
    if org_id and result.get("status") == "success":
        await increment_org_quota(org_id, db)
    
    return result

# Invite Member with Seat Limit

@router.post("/api/org/invite", response_model=InviteResponse)
async def invite_to_org(
    request: InviteRequest,
    user: dict = Depends(get_current_user),
    db: dict = Depends(get_database)
):
    """
    Invite a user to an organization.
    
    Validates:
    - User is org admin/owner
    - Seat limit not exceeded
    - Clerk invitation succeeds
    
    Raises:
    - 403: User is not org admin
    - 402: Seat limit reached
    - 400: Clerk invitation failed
    """
    org_id = user.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=400,
            detail="You are not in an organization"
        )
    
    # invite_member handles auth, seat limit, and Clerk invitation
    response = await invite_member(org_id, request.email, user, db)
    
    return response


# Get Org Details with Quota Info
@router.get("/api/org/details", response_model=OrgDetailsResponse)
async def get_org_details(
    user: dict = Depends(get_current_user),
    db: dict = Depends(get_database)
):
    """
    Get current org details including members and ingestion quota.
    Only returns org if user is a member.
    """
    org_id = user.get("org_id")
    if not org_id:
        raise HTTPException(
            status_code=400,
            detail="You are not in an organization"
        )
    
    org = await db.organizations.find_one({"org_id": org_id})
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    # Get current month's usage
    from datetime import datetime
    month_key = datetime.utcnow().strftime("%Y-%m")
    usage = await db.usage.find_one({"org_id": org_id, "month": month_key})
    repos_ingested = usage.get("repos_ingested", 0) if usage else 0
    
    return OrgDetailsResponse(
        org_id=org["org_id"],
        name=org["name"],
        owner_user_id=org["owner_user_id"],
        plan=org.get("plan", {}).get("name", "team"),
        member_count=len(org.get("member_user_ids", [])),
        seats_max=org.get("seats_max", 5),
        ingestion_quota_monthly=org.get("ingestion_quota_monthly", 20),
        repos_ingested_this_month=repos_ingested,
        created_at=org["created_at"]
    )


