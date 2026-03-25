from datetime import datetime
from core.database import get_database
from typing import Optional
from models.schemas import PlanType, SubscriptionStatus

async def get_or_create_user(user_id: str, email: Optional[str] = None) -> dict:
    db = get_database()
    users_collection = db["users"]
    
    user = await users_collection.find_one({"user_id": user_id})
    
    if not user:
        new_user = {
            "user_id": user_id,
            "email": email,
            "github_token": None,
            "github_username": None,
            "connected_at": None,
            "plan": {
                "name": PlanType.FREE,
                "price_inr": 0,
                "status": SubscriptionStatus.INACTIVE,
                "razorpay_customer_id": None,
                "razorpay_subscription_id": None,
                "razorpay_plan_id": None,
                "current_period_start": None,
                "current_period_end": None,
                "last_payment_id": None,
                "last_payment_date": None,
                "last_payment_status": None,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            },
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await users_collection.insert_one(new_user)
        return new_user
    
    return user


async def update_github_token(user_id: str, github_token: str, github_username: Optional[str] = None) -> bool:
    db = get_database()
    users_collection = db["users"]
    
    update_data = {
        "github_token": github_token,
        "connected_at": datetime.utcnow()
    }
    
    if github_username:
        update_data["github_username"] = github_username
    
    result = await users_collection.update_one(
        {"user_id": user_id},
        {"$set": update_data},
        upsert=True  
    )
    
    return result.matched_count > 0 or result.upserted_id is not None


async def get_github_token(user_id: str) -> Optional[str]:
    db = get_database()
    users_collection = db["users"]
    
    user = await users_collection.find_one(
        {"user_id": user_id},
        {"github_token": 1}
    )
    
    return user.get("github_token") if user else None


async def disconnect_github(user_id: str) -> bool:
    db = get_database()
    users_collection = db["users"]
    
    result = await users_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "github_token": None,
            "github_username": None,
            "connected_at": None
        }}
    )
    
    return result.matched_count > 0
