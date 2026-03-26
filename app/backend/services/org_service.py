"""
Organization service layer for Team plan operations.
Handles org membership, invitations, quotas and repo access control.
"""

from fastapi import HTTPException, status
from pymongo.database import Database
from typing import Optional, Dict
from datetime import datetime
import os
import httpx

CLERK_API_KEY = os.getenv("CLERK_API_KEY")
CLERK_API_URL = "https://api.clerk.com/v1"


async def require_org_access(repo_id: str, ctx: Dict, db: Database) -> Dict:
    """
    Validate user has access to a repository.
    Raises 403 if unauthorized, 404 if not found.
    
    Args:
        repo_id: Repository MongoDB _id
        ctx: User context from get_current_user (contains user_id, org_id)
        db: MongoDB connection
    
    Returns:
        repo document if authorized
    """
    from bson import ObjectId
    
    try:
        repo = await db.repositories.find_one({"_id": ObjectId(repo_id)})
    except Exception:
        repo = None
    
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    
    user_id = ctx.get("user_id")
    org_id = ctx.get("org_id")
    
    # Personal repo — user must be owner
    if repo.get("org_id") is None and repo.get("user_id"):
        if repo["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this repository"
            )
        return repo
    
    # Org repo — user must be a member of that org
    if repo.get("org_id"):
        if org_id != repo["org_id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this organization's repository"
            )
        
        org = await db.organizations.find_one({"org_id": org_id})
        if not org or user_id not in org.get("member_user_ids", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this organization"
            )
        return repo
    
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")


async def invite_member(org_id: str, email: str, ctx: Dict, db: Database) -> Dict:
    """
    Invite a new member to an org.
    Validates: org ownership, seat limit, Clerk invitation.
    
    Args:
        org_id: Organization ID
        email: Email to invite
        ctx: User context (must be org admin/owner)
        db: MongoDB connection
    
    Returns:
        Invitation details
    """
    user_id = ctx.get("user_id")
    
    # Fetch org
    org = await db.organizations.find_one({"org_id": org_id})
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # only org owner can invite 
    org_role = ctx.get("org_role")
    if org["owner_user_id"] != user_id and org_role not in ["org:admin", "org:owner"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only org admins can invite members"
        )
    
    # Check seat limit
    current_members = len(org.get("member_user_ids", []))
    seats_max = org.get("seats_max", 5)  
    
    if current_members >= seats_max:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Seat limit reached ({seats_max}). Upgrade your plan to add more members."
        )
    
    # Send Clerk invitation
    try:
        if not CLERK_API_KEY:
            raise Exception("CLERK_API_KEY not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{CLERK_API_URL}/organizations/{org_id}/invitations",
                json={"email_address": email},
                headers={"Authorization": f"Bearer {CLERK_API_KEY}"}
            )
            
            if response.status_code not in [200, 201]:
                error = response.json()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to send invitation: {error.get('errors', [{}])[0].get('message', 'Unknown error')}"
                )
            
            invitation_data = response.json()
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation failed: {str(e)}"
        )
    
    # Record invitation in MongoDB
    await db.invitations.insert_one({
        "org_id": org_id,
        "inviter_user_id": user_id,
        "invited_email": email,
        "clerk_invitation_id": invitation_data.get("id"),
        "created_at": datetime.utcnow()
    })
    
    return {
        "status": "success",
        "message": f"Invitation sent to {email}",
        "invited_email": email,
        "org_id": org_id
    }


async def check_org_quota(org_id: str, db: Database) -> bool:
    """
    Check if org has reached monthly ingestion quota.
    Raises 402 if limit exceeded.
    
    Args:
        org_id: Organization ID
        db: MongoDB connection
    
    Returns:
        True if within quota, raises HTTPException if exceeded
    
    Raises:
        HTTPException(402): Monthly quota exhausted
    """
    org = await db.organizations.find_one({"org_id": org_id})
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    
    # Get current month key 
    month_key = datetime.utcnow().strftime("%Y-%m")
    
    # Fetch or create usage record for this month
    usage = await db.usage.find_one({"org_id": org_id, "month": month_key})
    
    if not usage:
        # First repo of the month
        await db.usage.insert_one({
            "org_id": org_id,
            "month": month_key,
            "repos_ingested": 0,
            "created_at": datetime.utcnow()
        })
        return True
    
    # Check limit
    team_quota = org.get("ingestion_quota_monthly", 20)  # default team quota
    current_repos = usage.get("repos_ingested", 0)
    
    if current_repos >= team_quota:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Monthly ingestion quota reached ({team_quota} repos). Upgrade your plan or wait until next month."
        )
    
    return True


async def increment_org_quota(org_id: str, db: Database) -> None:
    """
    Increment the monthly repo count for an org after successful ingest.
    
    Args:
        org_id: Organization ID
        db: MongoDB connection
    """
    month_key = datetime.utcnow().strftime("%Y-%m")
    
    await db.usage.update_one(
        {"org_id": org_id, "month": month_key},
        {"$inc": {"repos_ingested": 1}},
        upsert=True
    )


async def reset_org_quota_if_needed(org_id: str, db: Database) -> None:
    """
    Reset monthly quota if month has changed.
    (Can be called on each org access to ensure quota_reset_date is current)
    """
    org = await db.organizations.find_one({"org_id": org_id})
    if not org:
        return
    
    last_reset = org.get("quota_reset_date")
    now = datetime.utcnow()
    current_month = now.strftime("%Y-%m")
    last_month = last_reset.strftime("%Y-%m") if last_reset else None
    
    if last_month != current_month:
        # Month rolled over, reset the usage record
        await db.usage.update_one(
            {"org_id": org_id, "month": current_month},
            {
                "$set": {
                    "repos_ingested": 0,
                    "reset_at": now
                }
            },
            upsert=True
        )
        
        # Update org's quota_reset_date
        await db.organizations.update_one(
            {"org_id": org_id},
            {"$set": {"quota_reset_date": now}}
        )
