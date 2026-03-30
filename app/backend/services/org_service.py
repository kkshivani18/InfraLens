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


async def get_org_details(org_id: str, db: Database) -> Dict:
    """
    Retrieve organization details with member count and quota info.
    
    Args:
        org_id: Organization ID
        db: MongoDB connection
    
    Returns:
        Organization details dictionary
    """
    org = await db.organizations.find_one({"org_id": org_id})
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    # Get current month's ingestion count
    month_key = datetime.utcnow().strftime("%Y-%m")
    usage = await db.usage.find_one({"org_id": org_id, "month": month_key})
    repos_ingested_this_month = usage.get("repos_ingested", 0) if usage else 0
    
    return {
        "org_id": org["org_id"],
        "name": org["name"],
        "owner_user_id": org["owner_user_id"],
        "plan": org.get("plan", {}).get("name", "team"),
        "member_count": len(org.get("member_user_ids", [])),
        "seats_max": org.get("seats_max", 5),
        "ingestion_quota_monthly": org.get("ingestion_quota_monthly", 100),
        "repos_ingested_this_month": repos_ingested_this_month,
        "created_at": org["created_at"].isoformat() if isinstance(org["created_at"], datetime) else org["created_at"]
    }


async def sync_org_from_clerk(org_id: str, clerk_org_data: Dict, db: Database) -> Dict:
    """
    Sync an organization from Clerk to MongoDB.
    Called when accessing an org for the first time.
    
    Args:
        org_id: Clerk organization ID
        clerk_org_data: Organization data from Clerk (contains name, created_at, etc.)
        db: MongoDB connection
    
    Returns:
        Organization document
    """
    # check org already exists
    existing_org = await db.organizations.find_one({"org_id": org_id})
    if existing_org:
        return existing_org
    
    # create new org 
    new_org = {
        "org_id": org_id,
        "name": clerk_org_data.get("name", "Untitled Organization"),
        "owner_user_id": clerk_org_data.get("created_by", ""),  # From Clerk
        "plan": {
            "name": "team",
            "price_inr": 0,
            "status": "inactive"
        },
        "member_user_ids": clerk_org_data.get("members", []),  # Clerk member IDs
        "seats_max": 5,  # Default for team plan
        "ingestion_quota_monthly": 100,  # Default quota
        "ingestion_count_this_month": 0,
        "quota_reset_date": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    try:
        await db.organizations.insert_one(new_org)
        print(f"✅ Synced organization {org_id} from Clerk to MongoDB")
        return new_org
    except Exception as e:
        if "duplicate key error" in str(e):
            # Race condition - org was created between check and insert
            return await db.organizations.find_one({"org_id": org_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync organization: {str(e)}"
        )


async def ensure_org_exists_in_db(org_id: str, db: Database, ctx: Dict = None) -> Dict:
    """
    Ensure an organization exists in MongoDB.
    If not, fetch from Clerk and create it.
    
    Args:
        org_id: Organization ID
        db: MongoDB connection
        ctx: User context (optional)
    
    Returns:
        Organization document from MongoDB
    """
    # Check if already in MongoDB
    org = await db.organizations.find_one({"org_id": org_id})
    if org:
        return org
    
    # Fetch from Clerk and sync
    try:
        if not CLERK_API_KEY:
            raise Exception("CLERK_API_KEY not configured")
            
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{CLERK_API_URL}/organizations/{org_id}",
                headers={"Authorization": f"Bearer {CLERK_API_KEY}"}
            )
            
            if response.status_code != 200:
                # Log the error but don't fail completely - org might exist in MongoDB
                print(f"⚠️  Failed to fetch org {org_id} from Clerk API: {response.status_code} - {response.text}")
                # Check MongoDB one more time before failing
                org = await db.organizations.find_one({"org_id": org_id})
                if org:
                    print(f"✅ Org {org_id} found in MongoDB, using existing record")
                    return org
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Organization {org_id} not found in Clerk. Please ensure the organization exists and you have access to it."
                )
            
            clerk_org = response.json()
            
            # Sync to MongoDB
            return await sync_org_from_clerk(org_id, clerk_org, db)
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in ensure_org_exists_in_db: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify organization: {str(e)}"
        )
