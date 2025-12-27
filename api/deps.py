"""
API dependencies.

Provides dependency injection for services, authentication, and common utilities.
"""

import logging
from typing import Optional, Annotated
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.config import load_config, Config
from src.services import (
    ServiceContext,
    AuthService,
    UserAuthService,
    MemberService,
    AvailabilityService,
    BookingService,
    MonitorService,
    GraphService,
    BeyondTokenService,
)
from src.auth import JWTHandler, TokenPayload, UserStore, User
from src.firebase_auth import FirebaseTokens

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer(auto_error=False)


@dataclass
class Services:
    """Container for all services."""
    config: Config
    context: ServiceContext
    auth: AuthService
    user_auth: UserAuthService
    members: MemberService
    availability: AvailabilityService
    bookings: BookingService
    monitor: MonitorService
    graph: GraphService
    beyond_tokens: BeyondTokenService
    jwt: JWTHandler
    users: UserStore


# Global services instance (singleton)
_services: Optional[Services] = None


def get_services() -> Services:
    """
    Get or create the services singleton.

    This initializes all services on first call.
    """
    global _services

    if _services is None:
        logger.info("Initializing services...")

        config = load_config()

        # Create service context
        context = ServiceContext.create(config=config)

        # Create JWT and user handlers
        jwt = JWTHandler()
        users = UserStore()

        # Create services
        auth = AuthService(context)
        user_auth = UserAuthService(jwt, users)
        members = MemberService(context)
        availability = AvailabilityService(context, members)
        bookings = BookingService(context, members, availability)
        monitor = MonitorService(context, members, availability, bookings)
        graph = GraphService()
        beyond_tokens = BeyondTokenService(context)

        _services = Services(
            config=config,
            context=context,
            auth=auth,
            user_auth=user_auth,
            members=members,
            availability=availability,
            bookings=bookings,
            monitor=monitor,
            graph=graph,
            beyond_tokens=beyond_tokens,
            jwt=jwt,
            users=users
        )

        logger.info("Services initialized successfully")

    return _services


def close_services():
    """Close and cleanup services."""
    global _services
    if _services:
        _services.context.close()
        _services.graph.save()
        _services = None
        logger.info("Services closed")


# Dependency for getting services
def services_dep() -> Services:
    """FastAPI dependency for services."""
    return get_services()


ServicesDep = Annotated[Services, Depends(services_dep)]


# Authentication dependencies

async def get_current_user_optional(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    services: ServicesDep
) -> Optional[User]:
    """
    Get current user from JWT token (optional).

    Returns None if no valid token is provided.
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = services.jwt.verify_token(token)

    if payload is None or payload.token_type != "access":
        return None

    user = services.users.get_by_id(payload.user_id)
    return user


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    services: ServicesDep
) -> User:
    """
    Get current user from JWT token (required).

    Raises 401 if no valid token is provided.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    payload = services.jwt.verify_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if payload.token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"}
        )

    user = services.users.get_by_id(payload.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    return user


async def get_token_payload(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    services: ServicesDep
) -> TokenPayload:
    """
    Get token payload (for checking auth_type etc).

    Raises 401 if no valid token is provided.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials
    payload = services.jwt.verify_token(token)

    if payload is None or payload.token_type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return payload


# Type aliases for dependencies
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[Optional[User], Depends(get_current_user_optional)]
CurrentTokenPayload = Annotated[TokenPayload, Depends(get_token_payload)]


# Sport context dependency
async def get_sport(
    sport: str = "surf",
    services: ServicesDep = None
) -> str:
    """
    Get and validate sport parameter.

    Sets the sport context in services.
    """
    valid_sports = ["surf", "tennis"]
    if sport not in valid_sports:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sport. Must be one of: {valid_sports}"
        )

    if services:
        services.context.set_sport(sport)

    return sport


SportDep = Annotated[str, Depends(get_sport)]


def ensure_beyond_api(services: Services, user: User) -> bool:
    """
    Ensure Beyond API is initialized for the user.

    Uses the user's stored Beyond tokens (from SMS verification modal).
    Does NOT automatically send SMS - requires explicit verification via modal.
    Will try to refresh expired tokens using refresh_token.

    Also sets the current user context in MemberService for per-user caching.

    Returns:
        True if API is ready

    Raises:
        HTTPException 401 if Beyond verification is required
    """
    # Set current user in MemberService for per-user caching
    services.members.set_current_user(user.phone)

    # Check if API is already initialized
    if services.context.api:
        return True

    # Try to use user's Beyond token (from SMS verification)
    user_token = services.beyond_tokens.get_token(user.phone)

    if user_token:
        # Try to use the token (even if expired, we'll try refresh)
        try:
            tokens = FirebaseTokens(
                id_token=user_token.id_token,
                refresh_token=user_token.refresh_token,
                expires_at=user_token.expires_at
            )
            # This will attempt refresh if token is expired
            services.auth.initialize_with_tokens(tokens)

            # If successful and token was refreshed, save the new token
            new_token = services.context.firebase_auth.get_valid_token()
            if new_token and services.context.firebase_auth._tokens:
                # Update stored tokens with refreshed values
                services.beyond_tokens.save_token(
                    user.phone,
                    services.context.firebase_auth._tokens
                )
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize with user tokens: {e}")
            # Token might be invalid/refresh failed, delete it
            services.beyond_tokens.delete_token(user.phone)

    # No valid Beyond token - user needs to verify via SMS modal
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Beyond verification required",
        headers={"X-Beyond-Auth-Required": "true"}
    )
