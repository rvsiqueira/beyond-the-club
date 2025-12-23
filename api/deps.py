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
)
from src.auth import JWTHandler, TokenPayload, UserStore, User

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
