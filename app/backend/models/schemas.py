from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

# ENUMS -------------------------------------

class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"           # awaiting first payment
    PAST_DUE = "past_due"         # payment failed
    CANCELLED = "cancelled"       
    INACTIVE = "inactive"         # not yet subscribed

# BILLING MODELS ------------------------------

class SubscriptionPlan(BaseModel):
    """Plan details (nested in user doc)"""
    name: PlanType
    price_inr: int                 # monthly price in rupees
    status: SubscriptionStatus = SubscriptionStatus.INACTIVE
    razorpay_plan_id: Optional[str] = None      # "plan_xxx" from Razorpay
    razorpay_subscription_id: Optional[str] = None
    razorpay_customer_id: Optional[str] = None
    current_period_start: Optional[datetime] = None
    current_period_end: Optional[datetime] = None
    last_payment_id: Optional[str] = None       # razorpay payment id
    last_payment_date: Optional[datetime] = None
    last_payment_status: Optional[str] = None   # "captured", "failed"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# CORE MODELS --------------------------------------

class Organization(BaseModel):
    """Organization document for Team plan multi-tenancy"""
    org_id: str  
    name: str  # org name
    owner_user_id: str  
    plan: SubscriptionPlan = Field(default_factory=lambda: SubscriptionPlan(
        name=PlanType.TEAM,
        price_inr=0,
        status=SubscriptionStatus.INACTIVE
    ))
    member_user_ids: List[str] = []  # list of user_ids in this org
    ingestion_quota_monthly: int = 100  
    ingestion_count_this_month: int = 0  # current usage
    quota_reset_date: Optional[datetime] = None  # when quota resets
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class User(BaseModel):
    """User document with GitHub integration"""
    user_id: str 
    email: Optional[str] = None
    github_token: Optional[str] = None
    github_username: Optional[str] = None
    connected_at: Optional[datetime] = None
    org_id: Optional[str] = None  

    plan: SubscriptionPlan = Field(default_factory=lambda: SubscriptionPlan(
        name=PlanType.FREE,
        price_inr=0,
        status=SubscriptionStatus.INACTIVE
    ))

    created_at: datetime = Field(default_factory=datetime.utcnow)

class Message(BaseModel):
    """single chat message"""
    role: str 
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class Chat(BaseModel):
    """Chat conversation document (scoped to individual user)"""
    user_id: str  # individual user
    org_id: Optional[str] = None  # org's repo 
    repository_name: Optional[str] = None 
    messages: List[Message] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class Repository(BaseModel):
    """Repository document - supports both single-user (user_id) and team (org_id) models"""
    user_id: Optional[str] = None  # single-user or org member ingesting to personal repo
    org_id: Optional[str] = None  # ingested to team workspace
    github_url: str
    name: str  
    collection_name: str  
    is_private: bool = False  
    files_processed: int = 0
    chunks_stored: int = 0
    ingested_at: datetime = Field(default_factory=datetime.utcnow)

class ChatRequest(BaseModel):
    """Chat API request"""
    message: str
    repository_name: Optional[str] = None

class IngestRequest(BaseModel):
    """Repository ingestion API request"""
    repo_url: str

class GitHubConnectRequest(BaseModel):
    """GitHub OAuth connection request"""
    github_token: str
    github_username: Optional[str] = None

# PAYMENT EVENT & WEBHOOK ---------------------------------------

class PaymentEvent(BaseModel):
    """Webhook event from Razorpay (for audit trail)"""
    user_id: str
    razorpay_event_id: str         # idempotency key
    razorpay_event_type: str       # e.g., "subscription.activated", "payment.failed"
    razorpay_subscription_id: Optional[str] = None
    razorpay_payment_id: Optional[str] = None
    razorpay_payload: dict         # full webhook payload for debugging
    processed: bool = False
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    processed_at: Optional[datetime] = None

# API REQUEST/RESPONSE SCHEMAS -----------------------------------

class CreateSubscriptionRequest(BaseModel):
    """Start subscription checkout"""
    plan: PlanType  # "pro" or "team"

class CreateSubscriptionResponse(BaseModel):
    """Return checkout details to frontend"""
    razorpay_subscription_id: str
    razorpay_key_id: str           # public key for frontend
    amount: int                     # amount in paise 
    currency: str = "INR"
    customer_email: str
    customer_id: str

class SubscriptionStatusResponse(BaseModel):
    """Current plan and subscription status"""
    plan: PlanType
    status: SubscriptionStatus
    current_period_end: Optional[datetime] = None
    razorpay_subscription_id: Optional[str] = None

class ShareChatRequest(BaseModel):
    """Share a chat session with other users (PREMIUM feature)"""
    repository_name: str
    chat_session_id: str
    share_with_emails: List[str]  

class WebhookPayload(BaseModel):
    """Razorpay webhook structure (simplified)"""
    event: str  # e.g. "subscription.activated"
    payload: dict

# ORG MANAGEMENT SCHEMAS ------------------------------------------

class InviteRequest(BaseModel):
    """Invite a member to an organization"""
    email: str

class InviteResponse(BaseModel):
    """Response after sending invite"""
    status: str  # "success"
    message: str
    invited_email: str
    org_id: str

class OrgDetailsResponse(BaseModel):
    """Organization details with membership and quota info"""
    org_id: str
    name: str
    owner_user_id: str
    plan: PlanType
    member_count: int
    seats_max: int
    ingestion_quota_monthly: int
    repos_ingested_this_month: int
    created_at: datetime

class IngestRequestWithOrg(BaseModel):
    """Ingest request with optional org_id for team workspace"""
    repo_url: str
    org_id: Optional[str] = None  
