import os
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from models.schemas import PlanType, SubscriptionStatus, SubscriptionPlan, PaymentEvent
from core.database import get_database
import httpx
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_API_URL = "https://api.razorpay.com/v1"

class PaymentService:
    def __init__(self):
        self.key_id = os.getenv("RAZORPAY_API_KEY")
        self.key_secret = os.getenv("RAZORPAY_SECRET_KEY")
        self.webhook_secret = os.getenv("RAZORPAY_WEBHOOK_SECRET", "test_webhook_secret")
        self.app_base_url = os.getenv("APP_BASE_URL", "http://localhost:5173")
        
        # Plan configuration (Razorpay plan IDs from env)
        self.plan_config = {
            PlanType.PRO: {
                "razorpay_id": os.getenv("RAZORPAY_PLAN_ID_PRO"),
                "price_inr": 100,
                "interval": 1,  # monthly
            },
            PlanType.TEAM: {
                "razorpay_id": os.getenv("RAZORPAY_PLAN_ID_TEAM"),
                "price_inr": 250,
                "interval": 1,
            },
        }

    async def create_or_get_customer(
        self, user_id: str, email: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Create Razorpay customer or fetch existing.
        Returns: (customer_id, error_message)
        """
        db = get_database()
        users = db["users"]
        
        user = await users.find_one({"user_id": user_id})
        
        # If customer already exists, return it
        if user and user.get("plan", {}).get("razorpay_customer_id"):
            return user["plan"]["razorpay_customer_id"], None
        
        # Create new customer
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{RAZORPAY_API_URL}/customers",
                    auth=(self.key_id, self.key_secret),
                    json={"email": email, "description": f"User: {user_id}"},
                    timeout=10.0,
                )
                if response.status_code == 400:
                    # Customer already exists
                    try:
                        error_json = response.json()
                        if "Customer already exists" in error_json.get("error", {}).get("description", ""):
                            # Try to fetch existing customer by email
                            fetch_response = await client.get(
                                f"{RAZORPAY_API_URL}/customers",
                                auth=(self.key_id, self.key_secret),
                                params={"email": email},
                                timeout=10.0,
                            )
                            if fetch_response.status_code == 200:
                                customers = fetch_response.json().get("items", [])
                                if customers:
                                    cust_id = customers[0]["id"]
                                    # Store it in MongoDB for future use
                                    await users.update_one(
                                        {"user_id": user_id},
                                        {"$set": {"plan.razorpay_customer_id": cust_id}},
                                        upsert=True,
                                    )
                                    return cust_id, None
                    except:
                        pass
                
                if response.status_code != 200:
                    error_msg = response.text
                    try:
                        error_json = response.json()
                        error_msg = json.dumps(error_json, indent=2)
                    except:
                        pass
                response.raise_for_status()
                customer_data = response.json()
                
                # Store customer_id immediately for future retries
                await users.update_one(
                    {"user_id": user_id},
                    {"$set": {"plan.razorpay_customer_id": customer_data["id"]}},
                    upsert=True,
                )
                return customer_data["id"], None
            except Exception as e:
                print(f"[PaymentService] Failed to create customer: {str(e)}")
                return None, str(e)

    async def create_subscription(
        self, user_id: str, email: str, plan: PlanType
    ) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Start subscription checkout for user (create Razorpay subscription).
        Returns: (checkout_payload, error_message)
        """
        if plan not in self.plan_config:
            return None, f"Invalid plan: {plan}"

        # Get or create customer
        customer_id, error = await self.create_or_get_customer(user_id, email)
        if error:
            return None, error

        # Create subscription
        plan_config = self.plan_config[plan]
        
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "plan_id": plan_config["razorpay_id"],
                    "customer_id": customer_id,
                    "customer_notify": 1,
                    "quantity": 1,
                    "total_count": 10,  
                }
                response = await client.post(
                    f"{RAZORPAY_API_URL}/subscriptions",
                    auth=(self.key_id, self.key_secret),
                    json=payload,
                    timeout=10.0,
                )
                if response.status_code not in [200, 201]:
                    error_msg = response.text
                    try:
                        error_json = response.json()
                        error_msg = json.dumps(error_json, indent=2)
                    except:
                        pass
                response.raise_for_status()
                sub_data = response.json()
                
                # store customer_id in user doc for future ref
                db = get_database()
                users = db["users"]
                await users.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "plan.razorpay_customer_id": customer_id,
                            "plan.updated_at": datetime.utcnow(),
                        }
                    },
                    upsert=True,
                )
                
                return {
                    "razorpay_subscription_id": sub_data["id"],
                    "status": sub_data["status"],
                    "customer_id": customer_id,
                    "amount": plan_config["price_inr"] * 100,  # convert to paise
                    "currency": "INR",
                    "customer_email": email,
                    "razorpay_key_id": self.key_id,
                }, None
            except Exception as e:
                print(f"[PaymentService] Failed to create subscription: {str(e)}")
                return None, str(e)

    def verify_webhook_signature(self, body: str, signature: str) -> bool:
        """Verify Razorpay webhook signature for security."""
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            body.encode(),
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature)

    async def process_webhook_event(self, event_data: dict) -> Tuple[bool, str]:
        """
        Process Razorpay webhook event (subscription.activated, payment.failed)
        Idempotent: skips if event_id already processed.
        Returns: (success, message)
        """
        event_type = event_data.get("event")
        payload = event_data.get("payload", {})
        event_id = event_data.get("id")  # Razorpay event ID
        
        db = get_database()
        payment_events = db["payment_events"]
        
        # check idempotency: if event been processed
        existing = await payment_events.find_one({"razorpay_event_id": event_id})
        if existing and existing.get("processed"):

            return True, "Event already processed (idempotent)"

        # Extract subscription and user info
        sub_data = payload.get("subscription", {})
        sub_id = sub_data.get("id")
        
        # Find user by subscription ID in their plan
        users = db["users"]
        user = await users.find_one({"plan.razorpay_subscription_id": sub_id})
        
        if not user:
            msg = f"Could not find user for subscription {sub_id}"
            # Log event as unprocessed for later investigation
            await payment_events.insert_one({
                "razorpay_event_id": event_id,
                "razorpay_event_type": event_type,
                "razorpay_subscription_id": sub_id,
                "razorpay_payload": payload,
                "processed": False,
                "error_message": msg,
                "created_at": datetime.utcnow(),
            })
            return False, msg
        
        user_id = user["user_id"]
        
        # HANDLE EVENT TYPES 
        try:
            if event_type == "subscription.activated":
                await users.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "plan.status": SubscriptionStatus.ACTIVE,
                            "plan.razorpay_subscription_id": sub_id,
                            "plan.current_period_start": datetime.fromisoformat(
                                sub_data.get("current_period_start_at", "").replace("Z", "+00:00")
                            ) if sub_data.get("current_period_start_at") else datetime.utcnow(),
                            "plan.current_period_end": datetime.fromisoformat(
                                sub_data.get("current_period_end_at", "").replace("Z", "+00:00")
                            ) if sub_data.get("current_period_end_at") else None,
                            "plan.updated_at": datetime.utcnow(),
                        }
                    },
                )

            elif event_type == "subscription.halted":
                await users.update_one(
                    {"user_id": user_id},
                    {"$set": {"plan.status": SubscriptionStatus.PAST_DUE, "plan.updated_at": datetime.utcnow()}},
                )

            elif event_type == "subscription.cancelled":
                await users.update_one(
                    {"user_id": user_id},
                    {"$set": {"plan.status": SubscriptionStatus.CANCELLED, "plan.updated_at": datetime.utcnow()}},
                )

            elif event_type == "payment.captured":
                payment = payload.get("payment", {})
                await users.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "plan.last_payment_id": payment.get("id"),
                            "plan.last_payment_date": datetime.utcnow(),
                            "plan.last_payment_status": "captured",
                            "plan.updated_at": datetime.utcnow(),
                        }
                    },
                )

            elif event_type == "payment.failed":
                await users.update_one(
                    {"user_id": user_id},
                    {
                        "$set": {
                            "plan.last_payment_status": "failed",
                            "plan.updated_at": datetime.utcnow(),
                        }
                    },
                )

            # marking event as processed
            await payment_events.update_one(
                {"razorpay_event_id": event_id},
                {
                    "$set": {
                        "processed": True,
                        "processed_at": datetime.utcnow(),
                        "razorpay_event_type": event_type,
                        "razorpay_subscription_id": sub_id,
                        "razorpay_payload": payload,
                    }
                },
                upsert=True,
            )
            
            return True, f"Event {event_type} processed successfully"

        except Exception as e:
            print(f"[Webhook] Error processing event {event_id}: {str(e)}")
            await payment_events.update_one(
                {"razorpay_event_id": event_id},
                {
                    "$set": {
                        "processed": False,
                        "error_message": str(e),
                        "created_at": datetime.utcnow(),
                    }
                },
                upsert=True,
            )
            return False, str(e)

    async def get_user_subscription(self, user_id: str) -> Dict:
        """Fetch user's current plan/subscription status."""
        db = get_database()
        users = db["users"]
        user = await users.find_one(
            {"user_id": user_id},
            {"plan": 1}
        )
        if not user:
            return {
                "plan": "free",
                "status": "inactive",
                "current_period_end": None,
            }
        plan = user.get("plan", {})
        return {
            "plan": plan.get("name", "free"),
            "status": plan.get("status", "inactive"),
            "current_period_end": plan.get("current_period_end"),
            "razorpay_subscription_id": plan.get("razorpay_subscription_id"),
        }

# global instance
payment_service = PaymentService()