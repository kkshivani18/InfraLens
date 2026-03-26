import os
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from typing import Dict, Optional

load_dotenv()

CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY")
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL")

if not CLERK_SECRET_KEY:
    raise Exception("CLERK_SECRET_KEY not found in environment variables")

if not CLERK_JWKS_URL:
    raise Exception("CLERK_JWKS_URL not found in environment variables. Add it to .env file.")

security = HTTPBearer()
jwks_client: Optional[PyJWKClient] = None

def get_jwks_client() -> PyJWKClient:
    global jwks_client
    if jwks_client is None:
        try:
            jwks_client = PyJWKClient(CLERK_JWKS_URL)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize JWT verification: {str(e)}"
            )
    return jwks_client

def get_org_context(decoded_jwt: dict) -> dict:
    """
    Extract org context from Clerk JWT claims.
    Clerk populates org_id and org_role if user is in an organization.
    """
    org_id = decoded_jwt.get("org_id")  
    org_role = decoded_jwt.get("org_role") 
    
    return {
        "org_id": org_id,
        "org_role": org_role
    }

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, str]:
    token = credentials.credentials
    
    try:
        jwks_client = get_jwks_client()
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        
        decoded = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_signature": True, "verify_exp": True}
        )
        
        # extract user_id from 'sub' claim
        user_id = decoded.get("sub")
        email = decoded.get("email")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: user_id not found"
            )
        
        # extract org context from JWT
        org_context = get_org_context(decoded)
        
        return {
            "user_id": user_id,
            "email": email or None,
            "org_id": org_context.get("org_id"),
            "org_role": org_context.get("org_role")
        }
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[Auth Error] Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )
