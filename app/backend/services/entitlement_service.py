from models.schemas import PlanType, SubscriptionStatus
from core.database import get_database
from datetime import datetime
from typing import Tuple

class EntitlementChecker:
    """Check if user has access to premium features based on subscription."""
    
    PLAN_LIMITS = {
        PlanType.FREE: {
            "can_clone_repo": True,
            "can_chat": True,
            "can_view_history": True,
            "can_share_chat": False,  # PREMIUM FEATURE
            "max_shared_chats": 0,
        },
        PlanType.PRO: {
            "can_clone_repo": True,
            "can_chat": True,
            "can_view_history": True,
            "can_share_chat": True,
            "max_shared_chats": 5,
        },
        PlanType.TEAM: {
            "can_clone_repo": True,
            "can_chat": True,
            "can_view_history": True,
            "can_share_chat": True,
            "max_shared_chats": 20,
        },
    }

    async def get_user_plan(self, user_id: str) -> Tuple[PlanType, SubscriptionStatus, bool]:
        """
        Get user's current plan and whether subscription is active.
        Returns: (plan_name, subscription_status, is_active)
        """
        db = get_database()
        users = db["users"]
        user = await users.find_one({"user_id": user_id}, {"plan": 1})
        
        if not user:
            return PlanType.FREE, SubscriptionStatus.INACTIVE, False

        plan_data = user.get("plan", {})
        plan_name = plan_data.get("name", PlanType.FREE)
        status = plan_data.get("status", SubscriptionStatus.INACTIVE)
        
        # Check if subscription is still valid (within billing period)
        is_active = (
            status == SubscriptionStatus.ACTIVE
            and plan_name != PlanType.FREE
            and plan_data.get("current_period_end")
            and plan_data.get("current_period_end") > datetime.utcnow()
        )
        
        return plan_name, status, is_active

    async def can_access_feature(self, user_id: str, feature: str) -> Tuple[bool, str]:
        """
        Check if user can access a feature.
        Returns: (allowed, reason_if_denied)
        """
        plan_name, status, is_active = await self.get_user_plan(user_id)
        
        # Free users always have access to free features
        if plan_name == PlanType.FREE:
            limits = self.PLAN_LIMITS[PlanType.FREE]
            allowed = limits.get(feature, False)
            if not allowed:
                return False, f"Feature '{feature}' requires a paid subscription. Upgrade to Pro or Team plan."
            return True, ""

        # Premium users
        if is_active:
            limits = self.PLAN_LIMITS[plan_name]
            allowed = limits.get(feature, False)
            if not allowed:
                return False, f"Feature '{feature}' not available in your {plan_name.value} plan."
            return True, ""
        else:
            # Subscription expired or not active
            return False, f"Your {plan_name.value} subscription is {status.value}. Please renew to access this feature."

    async def get_feature_limit(self, user_id: str, limit_key: str) -> int:
        """Get numeric limit for a feature (e.g., max_shared_chats)."""
        plan_name, status, is_active = await self.get_user_plan(user_id)
        
        if not is_active:
            plan_name = PlanType.FREE
        
        limits = self.PLAN_LIMITS[plan_name]
        return limits.get(limit_key, 0)

# Create global instance
entitlement_checker = EntitlementChecker()