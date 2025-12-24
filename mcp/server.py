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

from .tools import booking, availability, members, monitor, auth
from .resources import context

logger = logging.getLogger(__name__)

# Create server instance
server = Server("beyond-the-club")


# === Tool Registration ===

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    tools = []

    # Authentication tools (use these first!)
    tools.extend([
        Tool(
            name="check_auth_status",
            description="Check if a phone number has valid Beyond API authentication. USE THIS FIRST before calling other tools to verify the user can access the system.",
            inputSchema={
                "type": "object",
                "properties": {
                    "phone": {
                        "type": "string",
                        "description": "Phone number to check (e.g., '+5511999999999')"
                    }
                },
                "required": ["phone"]
            }
        ),
        Tool(
            name="request_beyond_sms",
            description="Request an SMS verification code for Beyond API authentication. Sends a 6-digit code to the phone number. Save the session_info for verify_beyond_sms.",
            inputSchema={
                "type": "object",
                "properties": {
                    "phone": {
                        "type": "string",
                        "description": "Phone number to send SMS to (e.g., '+5511999999999')"
                    }
                },
                "required": ["phone"]
            }
        ),
        Tool(
            name="verify_beyond_sms",
            description="Verify the SMS code and complete Beyond API authentication. After success, the user can use all booking features.",
            inputSchema={
                "type": "object",
                "properties": {
                    "phone": {
                        "type": "string",
                        "description": "Phone number that received the SMS"
                    },
                    "code": {
                        "type": "string",
                        "description": "6-digit code from SMS"
                    },
                    "session_info": {
                        "type": "string",
                        "description": "Session info from request_beyond_sms (optional, auto-retrieved)"
                    }
                },
                "required": ["phone", "code"]
            }
        ),
        Tool(
            name="get_authenticated_phones",
            description="Get a list of all phones with valid Beyond authentication.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ])

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
        Tool(
            name="swap_booking",
            description="Swap a booking to a different member. Cancels the original and creates a new booking for the new member.",
            inputSchema={
                "type": "object",
                "properties": {
                    "voucher_code": {
                        "type": "string",
                        "description": "Current booking voucher code"
                    },
                    "new_member_name": {
                        "type": "string",
                        "description": "Name of the new member to transfer the booking to"
                    },
                    "sport": {
                        "type": "string",
                        "description": "Sport type: 'surf' or 'tennis'",
                        "default": "surf"
                    }
                },
                "required": ["voucher_code", "new_member_name"]
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
        Tool(
            name="set_member_preferences",
            description="Set session preferences for a member. Use this to add or update preferred levels, wave sides, hours, and dates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_name": {
                        "type": "string",
                        "description": "Member's name"
                    },
                    "sessions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "level": {"type": "string", "description": "Level (e.g., 'Avançado2', 'Intermediario1')"},
                                "wave_side": {"type": "string", "description": "Wave side (e.g., 'Lado_direito', 'Lado_esquerdo')"},
                                "court": {"type": "string", "description": "Court (for tennis)"}
                            }
                        },
                        "description": "List of session preferences. Example: [{\"level\": \"Avançado2\", \"wave_side\": \"Lado_direito\"}]"
                    },
                    "target_hours": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Preferred hours (e.g., ['08:00', '09:00'])"
                    },
                    "target_dates": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Target dates (YYYY-MM-DD format)"
                    },
                    "sport": {
                        "type": "string",
                        "description": "Sport context: 'surf' or 'tennis'",
                        "default": "surf"
                    }
                },
                "required": ["member_name", "sessions"]
            }
        ),
        Tool(
            name="delete_member_preferences",
            description="Delete all preferences for a member.",
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
        Tool(
            name="get_session_options",
            description="Get available session options with fixed hours per level. Shows valid levels, wave sides, and which hours are available for each level.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="search_session",
            description="MONITOR and book a specific session over time. Use this when the user wants to keep checking until a slot becomes available. For immediate availability check, use check_session_availability instead.",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_name": {
                        "type": "string",
                        "description": "Member's name to book for"
                    },
                    "level": {
                        "type": "string",
                        "description": "Session level: Iniciante1 (13:00/15:00), Iniciante2 (09:00/17:00), Intermediario1 (10:00/16:00), Intermediario2 (08:00/12:00/18:00), Avançado1 (11:00/14:00), Avançado2 (07:00/19:00)"
                    },
                    "target_date": {
                        "type": "string",
                        "description": "Target date (YYYY-MM-DD format)"
                    },
                    "target_hour": {
                        "type": "string",
                        "description": "Target hour (HH:MM format). Must be valid for the selected level."
                    },
                    "wave_side": {
                        "type": "string",
                        "description": "Wave side: 'Lado_esquerdo' or 'Lado_direito' (optional - searches both if not specified)"
                    },
                    "auto_book": {
                        "type": "boolean",
                        "description": "Auto-book when slot found (default: true)",
                        "default": True
                    },
                    "duration_minutes": {
                        "type": "integer",
                        "description": "How long to search (default: 120 minutes)",
                        "default": 120
                    },
                    "sport": {
                        "type": "string",
                        "description": "Sport type: 'surf' or 'tennis'",
                        "default": "surf"
                    }
                },
                "required": ["member_name", "level", "target_date", "target_hour"]
            }
        ),
        Tool(
            name="check_session_availability",
            description="Check what sessions are available RIGHT NOW for a level/date. Returns all available slots so the user can choose. Use this first, then book_specific_slot to book, or search_session to monitor.",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_name": {
                        "type": "string",
                        "description": "Member's name to check for"
                    },
                    "level": {
                        "type": "string",
                        "description": "Session level (Iniciante1, Iniciante2, Intermediario1, Intermediario2, Avançado1, Avançado2)"
                    },
                    "target_date": {
                        "type": "string",
                        "description": "Target date (YYYY-MM-DD format)"
                    },
                    "wave_side": {
                        "type": "string",
                        "description": "Wave side (optional - checks both if not specified)"
                    },
                    "target_hour": {
                        "type": "string",
                        "description": "Target hour (optional - checks all valid hours if not specified)"
                    },
                    "sport": {
                        "type": "string",
                        "description": "Sport type",
                        "default": "surf"
                    }
                },
                "required": ["member_name", "level", "target_date"]
            }
        ),
        Tool(
            name="book_specific_slot",
            description="Book a specific slot IMMEDIATELY. Use after check_session_availability when user has chosen a slot. Requires all parameters (no monitoring).",
            inputSchema={
                "type": "object",
                "properties": {
                    "member_name": {
                        "type": "string",
                        "description": "Member's name to book for"
                    },
                    "level": {
                        "type": "string",
                        "description": "Session level"
                    },
                    "wave_side": {
                        "type": "string",
                        "description": "Wave side: 'Lado_esquerdo' or 'Lado_direito'"
                    },
                    "target_date": {
                        "type": "string",
                        "description": "Date (YYYY-MM-DD)"
                    },
                    "target_hour": {
                        "type": "string",
                        "description": "Hour (HH:MM)"
                    },
                    "sport": {
                        "type": "string",
                        "description": "Sport type",
                        "default": "surf"
                    }
                },
                "required": ["member_name", "level", "wave_side", "target_date", "target_hour"]
            }
        ),
    ])

    return tools


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        # Authentication tools
        if name == "check_auth_status":
            result = await auth.check_auth_status(**arguments)
        elif name == "request_beyond_sms":
            result = await auth.request_beyond_sms(**arguments)
        elif name == "verify_beyond_sms":
            result = await auth.verify_beyond_sms(**arguments)
        elif name == "get_authenticated_phones":
            result = await auth.get_authenticated_phone()
        # Availability tools
        elif name == "check_availability":
            result = await availability.check_availability(**arguments)
        elif name == "scan_availability":
            result = await availability.scan_availability(**arguments)
        elif name == "book_session":
            result = await booking.book_session(**arguments)
        elif name == "cancel_booking":
            result = await booking.cancel_booking(**arguments)
        elif name == "list_bookings":
            result = await booking.list_bookings(**arguments)
        elif name == "swap_booking":
            result = await booking.swap_booking(**arguments)
        elif name == "get_members":
            result = await members.get_members(**arguments)
        elif name == "get_member_preferences":
            result = await members.get_member_preferences(**arguments)
        elif name == "set_member_preferences":
            result = await members.set_member_preferences(**arguments)
        elif name == "delete_member_preferences":
            result = await members.delete_member_preferences(**arguments)
        elif name == "start_auto_monitor":
            result = await monitor.start_auto_monitor(**arguments)
        elif name == "check_monitor_status":
            result = await monitor.check_monitor_status()
        elif name == "get_session_options":
            result = await monitor.get_session_options()
        elif name == "search_session":
            result = await monitor.search_session(**arguments)
        elif name == "check_session_availability":
            result = await monitor.check_session_availability(**arguments)
        elif name == "book_specific_slot":
            result = await monitor.book_specific_slot(**arguments)
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
            uri="beyond://auth",
            name="Authentication Status",
            description="All authenticated phones and their token status",
            mimeType="application/json"
        ),
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
    if uri == "beyond://auth":
        return await context.get_auth_resource()
    elif uri == "beyond://members":
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
