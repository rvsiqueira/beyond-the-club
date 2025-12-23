"""
MCP Server implementation.

Exposes tools and resources for Claude to interact with
the Beyond The Club booking system.
"""

import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Tool,
    TextContent,
    Resource,
    ResourceTemplate,
)

from .tools import booking, availability, members, monitor
from .resources import context

logger = logging.getLogger(__name__)

# Create server instance
server = Server("beyond-the-club")


# === Tool Registration ===

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    tools = []

    # Availability tools
    tools.extend([
        Tool(
            name="check_availability",
            description="Check available surf/tennis session slots. Returns slots matching filters.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sport": {
                        "type": "string",
                        "description": "Sport type: 'surf' or 'tennis'",
                        "default": "surf"
                    },
                    "date": {
                        "type": "string",
                        "description": "Filter by date (YYYY-MM-DD format)"
                    },
                    "level": {
                        "type": "string",
                        "description": "Filter by level (e.g., 'Intermediario2')"
                    },
                    "wave_side": {
                        "type": "string",
                        "description": "Filter by wave side (e.g., 'Lado_direito')"
                    }
                }
            }
        ),
        Tool(
            name="scan_availability",
            description="Force a fresh scan of all available slots. Use when cached data might be stale.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sport": {
                        "type": "string",
                        "description": "Sport type: 'surf' or 'tennis'",
                        "default": "surf"
                    }
                }
            }
        ),
    ])

    # Booking tools
    tools.extend([
        Tool(
            name="book_session",
            description="Book a surf/tennis session for a member. Requires member name, date, and time.",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_name": {
                        "type": "string",
                        "description": "Member's name (e.g., 'Rafael', 'Julia')"
                    },
                    "date": {
                        "type": "string",
                        "description": "Session date (YYYY-MM-DD)"
                    },
                    "time": {
                        "type": "string",
                        "description": "Session time (e.g., '08:00')"
                    },
                    "level": {
                        "type": "string",
                        "description": "Session level (optional, uses member's preference if not specified)"
                    },
                    "wave_side": {
                        "type": "string",
                        "description": "Wave side (optional, uses member's preference if not specified)"
                    },
                    "sport": {
                        "type": "string",
                        "description": "Sport type: 'surf' or 'tennis'",
                        "default": "surf"
                    }
                },
                "required": ["member_name", "date", "time"]
            }
        ),
        Tool(
            name="cancel_booking",
            description="Cancel an existing booking by voucher code.",
            inputSchema={
                "type": "object",
                "properties": {
                    "voucher_code": {
                        "type": "string",
                        "description": "The booking voucher code to cancel"
                    }
                },
                "required": ["voucher_code"]
            }
        ),
        Tool(
            name="list_bookings",
            description="List active bookings. Optionally filter by member name.",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_name": {
                        "type": "string",
                        "description": "Filter by member name (optional)"
                    },
                    "sport": {
                        "type": "string",
                        "description": "Sport type: 'surf' or 'tennis'",
                        "default": "surf"
                    }
                }
            }
        ),
    ])

    # Member tools
    tools.extend([
        Tool(
            name="get_members",
            description="Get list of all members with their usage status and preferences.",
            inputSchema={
                "type": "object",
                "properties": {
                    "sport": {
                        "type": "string",
                        "description": "Sport context: 'surf' or 'tennis'",
                        "default": "surf"
                    }
                }
            }
        ),
        Tool(
            name="get_member_preferences",
            description="Get a specific member's session preferences.",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_name": {
                        "type": "string",
                        "description": "Member's name"
                    },
                    "sport": {
                        "type": "string",
                        "description": "Sport context: 'surf' or 'tennis'",
                        "default": "surf"
                    }
                },
                "required": ["member_name"]
            }
        ),
    ])

    # Monitor tools
    tools.extend([
        Tool(
            name="start_auto_monitor",
            description="Start automatic monitoring and booking for members. Will continuously check for available slots matching preferences.",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of member names to monitor (optional, monitors all with preferences if not specified)"
                    },
                    "target_dates": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific dates to target (YYYY-MM-DD format, optional)"
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "How long to run the monitor (default: 120 minutes)",
                        "default": 120
                    },
                    "sport": {
                        "type": "string",
                        "description": "Sport type: 'surf' or 'tennis'",
                        "default": "surf"
                    }
                }
            }
        ),
        Tool(
            name="check_monitor_status",
            description="Check the status of a running auto-monitor.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ])

    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "check_availability":
            result = await availability.check_availability(**arguments)
        elif name == "scan_availability":
            result = await availability.scan_availability(**arguments)
        elif name == "book_session":
            result = await booking.book_session(**arguments)
        elif name == "cancel_booking":
            result = await booking.cancel_booking(**arguments)
        elif name == "list_bookings":
            result = await booking.list_bookings(**arguments)
        elif name == "get_members":
            result = await members.get_members(**arguments)
        elif name == "get_member_preferences":
            result = await members.get_member_preferences(**arguments)
        elif name == "start_auto_monitor":
            result = await monitor.start_auto_monitor(**arguments)
        elif name == "check_monitor_status":
            result = await monitor.check_monitor_status()
        else:
            result = f"Unknown tool: {name}"

        return [TextContent(type="text", text=str(result))]

    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return [TextContent(type="text", text=f"Error: {str(e)}")]


# === Resource Registration ===

@server.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="beyond://members",
            name="Members",
            description="List of all members with usage status",
            mimeType="application/json"
        ),
        Resource(
            uri="beyond://bookings",
            name="Active Bookings",
            description="Current active bookings",
            mimeType="application/json"
        ),
        Resource(
            uri="beyond://availability",
            name="Availability Cache",
            description="Cached availability data",
            mimeType="application/json"
        ),
        Resource(
            uri="beyond://preferences",
            name="Member Preferences",
            description="All member preferences",
            mimeType="application/json"
        ),
    ]


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource."""
    if uri == "beyond://members":
        return await context.get_members_resource()
    elif uri == "beyond://bookings":
        return await context.get_bookings_resource()
    elif uri == "beyond://availability":
        return await context.get_availability_resource()
    elif uri == "beyond://preferences":
        return await context.get_preferences_resource()
    else:
        return f"Unknown resource: {uri}"


# === Server Entry Point ===

async def main():
    """Run the MCP server."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )
    logger.info("Starting Beyond The Club MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
