"""
MCP Context management.

Provides shared access to services for MCP tools and resources.
"""

import logging
from typing import Optional
from dataclasses import dataclass

from src.config import load_config, Config
from src.services import (
    ServiceContext,
    AuthService,
    MemberService,
    AvailabilityService,
    BookingService,
    MonitorService,
    GraphService,
)
from src.services.beyond_token_service import BeyondTokenService

logger = logging.getLogger(__name__)


@dataclass
class MCPServices:
    """Container for MCP services."""
    config: Config
    context: ServiceContext
    auth: AuthService
    members: MemberService
    availability: AvailabilityService
    bookings: BookingService
    monitor: MonitorService
    graph: GraphService
    beyond_tokens: BeyondTokenService


# Global services instance
_services: Optional[MCPServices] = None


def get_services() -> MCPServices:
    """
    Get or create the MCP services singleton.

    Returns:
        MCPServices instance
    """
    global _services

    if _services is None:
        logger.info("Initializing MCP services...")

        config = load_config()
        context = ServiceContext.create(config=config)

        auth = AuthService(context)
        members = MemberService(context)
        availability = AvailabilityService(context, members)
        bookings = BookingService(context, members, availability)
        monitor = MonitorService(context, members, availability, bookings)
        graph = GraphService()
        beyond_tokens = BeyondTokenService(context)

        _services = MCPServices(
            config=config,
            context=context,
            auth=auth,
            members=members,
            availability=availability,
            bookings=bookings,
            monitor=monitor,
            graph=graph,
            beyond_tokens=beyond_tokens
        )

        logger.info("MCP services initialized")

    return _services


def close_services():
    """Close and cleanup services."""
    global _services
    if _services:
        _services.context.close()
        _services.graph.save()
        _services = None
        logger.info("MCP services closed")
