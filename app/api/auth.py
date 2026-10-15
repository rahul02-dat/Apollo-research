"""Apollo Authentication & Multi-Tenant Workspace Service."""

import base64
import hashlib
import hmac
import json
import logging
import time
from enum import Enum
from typing import Annotated, Any
from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from app.config import settings
from app.persistence.database import run_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication & Workspaces"])
security_scheme = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    ANALYST = "ANALYST"
    ADMIN = "ADMIN"
    AUDITOR = "AUDITOR"


class User(BaseModel):
    user_id: str
    email: str
    name: str
    role: UserRole = UserRole.ANALYST
    active_workspace_id: str = "ws_default"
    is_active: bool = True


class Workspace(BaseModel):
    workspace_id: str
    name: str
    owner_id: str
    created_at: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


class LoginRequest(BaseModel):
    api_key: str | None = None
    email: str | None = None


class CreateWorkspaceRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=50, description="Workspace name")


# --- Cryptographic Token Utilities ---
def create_access_token(user: User, expires_minutes: int | None = None) -> str:
    """Creates a cryptographically signed HMAC-SHA256 JWT-compatible bearer token."""
    exp_mins = expires_minutes or settings.AUTH_TOKEN_EXPIRE_MINUTES
    exp_time = int(time.time()) + (exp_mins * 60)

    payload = {
        "sub": user.user_id,
        "email": user.email,
        "name": user.name,
        "role": user.role.value,
        "workspace_id": user.active_workspace_id,
        "exp": exp_time,
    }

    payload_json = json.dumps(payload, separators=(",", ":"))
    payload_b64 = base64.urlsafe_b64encode(payload_json.encode()).decode().rstrip("=")

    sig = hmac.new(settings.AUTH_SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode().rstrip("=")

    return f"{payload_b64}.{sig_b64}"


def verify_access_token(token: str) -> dict[str, Any] | None:
    """Validates an HMAC-SHA256 signed bearer token."""
    parts = token.split(".")
    if len(parts) != 2:
        return None

    payload_b64, sig_b64 = parts
    # Check signature
    expected_sig = hmac.new(settings.AUTH_SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).digest()
    expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode().rstrip("=")

    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        return None

    # Decode payload
    try:
        # Add back padding
        pad_len = 4 - (len(payload_b64) % 4)
        if pad_len < 4:
            payload_b64 += "=" * pad_len
        payload_bytes = base64.urlsafe_b64decode(payload_b64.encode())
        payload = json.loads(payload_bytes.decode())

        if payload.get("exp", 0) < int(time.time()):
            return None  # Expired

        return payload
    except Exception as e:
        logger.warning("Token decode error: %s", e)
        return None


# --- FastAPI Dependency ---
async def get_current_user(
    auth_creds: Annotated[HTTPAuthorizationCredentials | None, Depends(security_scheme)] = None,
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> User:
    """Resolves authenticated user from Bearer Token or X-API-Key with development fallback."""
    # 1. Bearer Token
    if auth_creds and auth_creds.credentials:
        payload = verify_access_token(auth_creds.credentials)
        if payload:
            user_data = run_store.get_user(payload["sub"])
            if user_data:
                return User(
                    user_id=user_data["user_id"],
                    email=user_data["email"],
                    name=user_data["name"],
                    role=UserRole(user_data["role"]),
                    active_workspace_id=user_data.get("active_workspace_id", "ws_default"),
                )
            return User(
                user_id=payload["sub"],
                email=payload.get("email", ""),
                name=payload.get("name", "Analyst"),
                role=UserRole(payload.get("role", "ANALYST")),
                active_workspace_id=payload.get("workspace_id", "ws_default"),
            )

    # 2. X-API-Key Header
    if x_api_key:
        user_data = run_store.get_user_by_api_key(x_api_key)
        if user_data:
            return User(
                user_id=user_data["user_id"],
                email=user_data["email"],
                name=user_data["name"],
                role=UserRole(user_data["role"]),
                active_workspace_id=user_data.get("active_workspace_id", "ws_default"),
            )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")

    # 3. Development / Local Fallback
    if not settings.REQUIRE_AUTH:
        user_data = run_store.get_user("usr_primary_analyst")
        if user_data:
            return User(
                user_id=user_data["user_id"],
                email=user_data["email"],
                name=user_data["name"],
                role=UserRole(user_data["role"]),
                active_workspace_id=user_data.get("active_workspace_id", "ws_default"),
            )
        return User(
            user_id="usr_primary_analyst",
            email="analyst@apollo.local",
            name="Senior Financial Analyst",
            role=UserRole.ANALYST,
            active_workspace_id="ws_default",
        )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication credentials required")


# --- Auth Routes ---
@router.post("/token", response_model=TokenResponse)
def login_for_token(req: LoginRequest) -> Any:
    """Exchanges an API key or registered email for a signed JWT access token."""
    user_data = None
    if req.api_key:
        user_data = run_store.get_user_by_api_key(req.api_key)
    elif req.email:
        user_data = run_store.get_user_by_email(req.email)
    else:
        # Default dev user
        user_data = run_store.get_user("usr_primary_analyst")

    if not user_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authentication credentials")

    user = User(
        user_id=user_data["user_id"],
        email=user_data["email"],
        name=user_data["name"],
        role=UserRole(user_data["role"]),
        active_workspace_id=user_data.get("active_workspace_id", "ws_default"),
    )

    token = create_access_token(user)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/me", response_model=dict[str, Any])
def get_user_profile(current_user: Annotated[User, Depends(get_current_user)]) -> Any:
    """Returns the authenticated user's profile and workspace memberships."""
    workspaces = run_store.list_workspaces_for_user(current_user.user_id)
    return {
        "user": current_user,
        "workspaces": workspaces,
    }


@router.get("/workspaces", response_model=list[Workspace])
def list_workspaces(current_user: Annotated[User, Depends(get_current_user)]) -> Any:
    """Lists accessible workspaces for the authenticated user."""
    return run_store.list_workspaces_for_user(current_user.user_id)


@router.post("/workspaces", response_model=Workspace)
def create_workspace(
    req: CreateWorkspaceRequest,
    current_user: Annotated[User, Depends(get_current_user)],
) -> Any:
    """Creates a new isolated tenant workspace."""
    import uuid
    ws_id = f"ws_{uuid.uuid4().hex[:8]}"
    return run_store.create_workspace(
        workspace_id=ws_id,
        name=req.name,
        owner_id=current_user.user_id,
    )
