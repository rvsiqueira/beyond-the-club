"""
Authentication endpoints.

Handles user registration, login, and token management.
"""

import logging
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from ..deps import ServicesDep, CurrentUser

logger = logging.getLogger(__name__)

router = APIRouter()


# Request/Response models

class RegisterRequest(BaseModel):
    """User registration request."""
    phone: str = Field(..., description="Phone number (e.g., +5511999999999)")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    name: Optional[str] = Field(None, description="Display name")
    email: Optional[str] = Field(None, description="Email address")
    member_ids: Optional[List[int]] = Field(None, description="Beyond member IDs to link")


class LoginRequest(BaseModel):
    """Login request."""
    phone: str = Field(..., description="Phone number")
    password: str = Field(..., description="Password")


class PhoneLoginRequest(BaseModel):
    """Phone-only login request (for voice agent)."""
    phone: str = Field(..., description="Phone number (caller ID)")
    auto_create: bool = Field(False, description="Create user if not exists")


class RefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str = Field(..., description="Valid refresh token")


class TokenResponse(BaseModel):
    """Token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class UserResponse(BaseModel):
    """User info response."""
    user_id: str
    phone: str
    name: Optional[str]
    member_ids: List[int]
    is_active: bool


class AuthResponse(BaseModel):
    """Authentication response with tokens and user info."""
    success: bool
    tokens: Optional[TokenResponse] = None
    user: Optional[UserResponse] = None
    error: Optional[str] = None


# Endpoints

@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, services: ServicesDep):
    """
    Register a new user.

    Creates a new user account with phone and password.
    Returns JWT tokens on success.
    """
    result = services.user_auth.register(
        phone=request.phone,
        password=request.password,
        name=request.name,
        email=request.email,
        member_ids=request.member_ids
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )

    # Sync user to graph
    if result.user:
        services.graph.sync_user(
            phone=result.user.phone,
            name=result.user.name,
            member_ids=result.user.member_ids
        )

    return AuthResponse(
        success=True,
        tokens=TokenResponse(
            access_token=result.tokens.access_token,
            refresh_token=result.tokens.refresh_token
        ) if result.tokens else None,
        user=UserResponse(
            user_id=result.user.user_id,
            phone=result.user.phone,
            name=result.user.name,
            member_ids=result.user.member_ids,
            is_active=result.user.is_active
        ) if result.user else None
    )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, services: ServicesDep):
    """
    Login with phone and password.

    Returns JWT tokens on success.
    """
    result = services.user_auth.login_password(
        phone=request.phone,
        password=request.password
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.error
        )

    return AuthResponse(
        success=True,
        tokens=TokenResponse(
            access_token=result.tokens.access_token,
            refresh_token=result.tokens.refresh_token
        ) if result.tokens else None,
        user=UserResponse(
            user_id=result.user.user_id,
            phone=result.user.phone,
            name=result.user.name,
            member_ids=result.user.member_ids,
            is_active=result.user.is_active
        ) if result.user else None
    )


@router.post("/login/phone", response_model=AuthResponse)
async def login_phone_only(request: PhoneLoginRequest, services: ServicesDep):
    """
    Login with phone number only (for voice agent).

    This is a lower-security auth method for caller ID identification.
    Use auto_create=true to create user if not exists.
    """
    result = services.user_auth.login_phone_only(
        phone=request.phone,
        auto_create=request.auto_create
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.error
        )

    # Sync user to graph if auto-created
    if request.auto_create and result.user:
        services.graph.sync_user(phone=result.user.phone)

    return AuthResponse(
        success=True,
        tokens=TokenResponse(
            access_token=result.tokens.access_token,
            refresh_token=result.tokens.refresh_token
        ) if result.tokens else None,
        user=UserResponse(
            user_id=result.user.user_id,
            phone=result.user.phone,
            name=result.user.name,
            member_ids=result.user.member_ids,
            is_active=result.user.is_active
        ) if result.user else None
    )


@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(request: RefreshRequest, services: ServicesDep):
    """
    Refresh an access token.

    Use the refresh token to get a new access token.
    """
    result = services.user_auth.refresh_token(request.refresh_token)

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.error
        )

    return AuthResponse(
        success=True,
        tokens=TokenResponse(
            access_token=result.tokens.access_token,
            refresh_token=result.tokens.refresh_token
        ) if result.tokens else None,
        user=UserResponse(
            user_id=result.user.user_id,
            phone=result.user.phone,
            name=result.user.name,
            member_ids=result.user.member_ids,
            is_active=result.user.is_active
        ) if result.user else None
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser):
    """
    Get current authenticated user info.

    Requires valid access token.
    """
    return UserResponse(
        user_id=current_user.user_id,
        phone=current_user.phone,
        name=current_user.name,
        member_ids=current_user.member_ids,
        is_active=current_user.is_active
    )


@router.post("/link-member/{member_id}")
async def link_member(
    member_id: int,
    current_user: CurrentUser,
    services: ServicesDep
):
    """
    Link a Beyond member ID to the current user.

    Requires valid access token.
    """
    result = services.user_auth.link_member_to_user(
        phone=current_user.phone,
        member_id=member_id
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.error
        )

    # Update graph
    services.graph.link_user_to_member(current_user.phone, member_id)

    return {"success": True, "member_id": member_id}


# Beyond API SMS Authentication
# These endpoints manage the Beyond API (Firebase) tokens per user

class BeyondSMSRequest(BaseModel):
    """Request to send Beyond SMS code."""
    phone: str = Field(..., description="Phone number for Beyond API")


class BeyondVerifyRequest(BaseModel):
    """Request to verify Beyond SMS code."""
    phone: str = Field(..., description="Phone number")
    code: str = Field(..., description="6-digit SMS code")
    session_info: str = Field(..., description="Session info from request")


@router.post("/beyond/request-sms")
async def request_beyond_sms(
    request: BeyondSMSRequest,
    current_user: CurrentUser,
    services: ServicesDep
):
    """
    Request SMS code for Beyond API authentication.

    Sends an SMS to the specified phone number with a verification code.
    The tokens will be linked to the current web user's phone.
    """
    try:
        session_info = services.beyond_tokens.request_sms(request.phone)
        return {"session_info": session_info}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/beyond/verify-sms")
async def verify_beyond_sms(
    request: BeyondVerifyRequest,
    current_user: CurrentUser,
    services: ServicesDep
):
    """
    Verify Beyond SMS code and store tokens.

    Verifies the SMS code and stores the Beyond API tokens
    linked to the current web user's phone number.

    After verification, automatically loads members for the user's cache.
    """
    try:
        # Verify using the Beyond phone (that received the SMS)
        # Store tokens linked to the web user's phone
        tokens = services.beyond_tokens.verify_sms(
            beyond_phone=request.phone,  # Phone that received SMS
            code=request.code,
            session_info=request.session_info,
            store_for_phone=current_user.phone  # Store linked to web user
        )

        # Initialize Beyond API and load members for this user
        try:
            from src.firebase_auth import FirebaseTokens
            services.auth.initialize_with_tokens(tokens)
            services.members.set_current_user(current_user.phone)
            services.members.refresh_members()
            logger.info(f"Loaded members for user {current_user.phone} after Beyond verification")
        except Exception as e:
            logger.warning(f"Failed to load members after Beyond verification: {e}")
            # Don't fail the verification if member loading fails

        return {"success": True}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/beyond/status")
async def check_beyond_status(
    current_user: CurrentUser,
    services: ServicesDep
):
    """
    Check if the current user has valid Beyond API tokens.

    Returns whether the user has valid tokens for the Beyond API.
    This endpoint will attempt to refresh expired tokens automatically.
    """
    # Try to get a valid token (this will refresh if expired)
    valid_token = services.beyond_tokens.get_valid_id_token(current_user.phone)
    token = services.beyond_tokens.get_token(current_user.phone)

    return {
        "valid": valid_token is not None,
        "phone": current_user.phone,
        "expires_at": token.expires_at if token else None
    }
