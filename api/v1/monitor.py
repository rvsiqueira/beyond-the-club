"""
Monitor endpoints.

Handles automatic monitoring with WebSocket support for real-time updates.
"""

import asyncio
import json
import logging
from typing import Optional, List, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from ..deps import ServicesDep, CurrentUser, get_services, ensure_beyond_api

router = APIRouter()
logger = logging.getLogger(__name__)

# Store for active monitors
active_monitors: Dict[str, Dict[str, Any]] = {}


# Request/Response models

class StartMonitorRequest(BaseModel):
    """Start monitor request."""
    member_ids: List[int] = Field(..., description="Member IDs to monitor")
    target_dates: Optional[List[str]] = Field(None, description="Target dates (YYYY-MM-DD)")
    duration_minutes: int = Field(120, description="Duration in minutes")
    check_interval_seconds: int = Field(30, description="Check interval in seconds")


class MonitorStatusResponse(BaseModel):
    """Monitor status response."""
    monitor_id: str
    status: str
    member_ids: List[int]
    target_dates: Optional[List[str]]
    duration_minutes: int
    elapsed_seconds: int
    results: Dict[int, Any]


# Endpoints

@router.post("/start")
async def start_monitor(
    request: StartMonitorRequest,
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport")
):
    """
    Start an automatic monitor session.

    Returns a monitor_id for tracking. Use the WebSocket endpoint
    to receive real-time updates.
    """
    services.context.set_sport(sport)

    # Initialize Beyond API using user's tokens (no auto-SMS)
    ensure_beyond_api(services, current_user)

    # Verify all members exist and have preferences
    for member_id in request.member_ids:
        member = services.members.get_member_by_id(member_id)
        if not member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Member {member_id} not found"
            )

        prefs = services.members.get_member_preferences(member_id, sport)
        if not prefs or not prefs.sessions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Member {member_id} has no preferences configured"
            )

    # Create monitor ID
    monitor_id = str(uuid4())[:8]

    # Store monitor info
    active_monitors[monitor_id] = {
        "status": "pending",
        "member_ids": request.member_ids,
        "target_dates": request.target_dates,
        "duration_minutes": request.duration_minutes,
        "check_interval_seconds": request.check_interval_seconds,
        "sport": sport,
        "user_phone": current_user.phone,
        "results": {},
        "messages": [],
        "started_at": None,
        "elapsed_seconds": 0
    }

    return {
        "monitor_id": monitor_id,
        "status": "pending",
        "message": f"Monitor created. Connect to WebSocket /ws/monitor/{monitor_id} to start.",
        "member_ids": request.member_ids,
        "target_dates": request.target_dates,
        "duration_minutes": request.duration_minutes
    }


@router.get("/{monitor_id}/status", response_model=MonitorStatusResponse)
async def get_monitor_status(
    monitor_id: str,
    services: ServicesDep,
    current_user: CurrentUser
):
    """
    Get the status of a monitor session.
    """
    if monitor_id not in active_monitors:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitor {monitor_id} not found"
        )

    monitor = active_monitors[monitor_id]

    return MonitorStatusResponse(
        monitor_id=monitor_id,
        status=monitor["status"],
        member_ids=monitor["member_ids"],
        target_dates=monitor["target_dates"],
        duration_minutes=monitor["duration_minutes"],
        elapsed_seconds=monitor["elapsed_seconds"],
        results=monitor["results"]
    )


@router.post("/{monitor_id}/stop")
async def stop_monitor(
    monitor_id: str,
    services: ServicesDep,
    current_user: CurrentUser
):
    """
    Stop a running monitor session.
    """
    if monitor_id not in active_monitors:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitor {monitor_id} not found"
        )

    monitor = active_monitors[monitor_id]
    monitor["status"] = "stopping"

    # The actual stop will be handled by the monitor service
    services.monitor.stop()

    return {
        "monitor_id": monitor_id,
        "status": "stopping",
        "message": "Stop request sent"
    }


@router.get("")
async def list_monitors(
    services: ServicesDep,
    current_user: CurrentUser
):
    """
    List all monitor sessions for the current user.
    """
    user_monitors = {
        mid: {
            "status": m["status"],
            "member_ids": m["member_ids"],
            "elapsed_seconds": m["elapsed_seconds"]
        }
        for mid, m in active_monitors.items()
        if m.get("user_phone") == current_user.phone
    }

    return {
        "monitors": user_monitors,
        "total": len(user_monitors)
    }


# WebSocket endpoint for real-time updates

@router.websocket("/ws/{monitor_id}")
async def monitor_websocket(websocket: WebSocket, monitor_id: str):
    """
    WebSocket endpoint for real-time monitor updates.

    Connect to start the monitor and receive status updates.
    """
    await websocket.accept()

    if monitor_id not in active_monitors:
        await websocket.send_json({
            "type": "error",
            "message": f"Monitor {monitor_id} not found"
        })
        await websocket.close()
        return

    monitor = active_monitors[monitor_id]
    services = get_services()

    # Set sport context
    services.context.set_sport(monitor["sport"])

    # Initialize Beyond API using user's Beyond tokens (no auto-SMS)
    if not services.context.api:
        user_phone = monitor.get("user_phone")
        user_token = services.beyond_tokens.get_token(user_phone) if user_phone else None

        if user_token and services.beyond_tokens.has_valid_token(user_phone):
            try:
                from src.firebase_auth import FirebaseTokens
                tokens = FirebaseTokens(
                    id_token=user_token.id_token,
                    refresh_token=user_token.refresh_token,
                    expires_at=user_token.expires_at
                )
                services.auth.initialize_with_tokens(tokens)
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Beyond API initialization failed: {str(e)}"
                })
                await websocket.close()
                return
        else:
            await websocket.send_json({
                "type": "error",
                "message": "Beyond verification required. Please verify via SMS first."
            })
            await websocket.close()
            return

    # Status update callback
    async def send_status(message: str, level: str):
        try:
            await websocket.send_json({
                "type": "status",
                "level": level,
                "message": message
            })
        except Exception:
            pass

    # Sync wrapper for async callback
    def status_callback(message: str, level: str):
        monitor["messages"].append({"message": message, "level": level})
        # We'll send these in the main loop

    try:
        # Start the monitor
        monitor["status"] = "running"
        await websocket.send_json({
            "type": "started",
            "monitor_id": monitor_id,
            "member_ids": monitor["member_ids"]
        })

        import time
        start_time = time.time()

        # Run monitor in a thread to not block
        import threading
        result_holder = {"results": None, "error": None}

        def run_monitor():
            try:
                results = services.monitor.run_auto_monitor(
                    member_ids=monitor["member_ids"],
                    target_dates=monitor["target_dates"],
                    duration_minutes=monitor["duration_minutes"],
                    check_interval_seconds=monitor["check_interval_seconds"],
                    on_status_update=status_callback
                )
                result_holder["results"] = results
            except Exception as e:
                result_holder["error"] = str(e)

        thread = threading.Thread(target=run_monitor)
        thread.start()

        # Send updates while monitor runs
        last_msg_idx = 0
        while thread.is_alive():
            # Check for new messages
            if len(monitor["messages"]) > last_msg_idx:
                for msg in monitor["messages"][last_msg_idx:]:
                    await websocket.send_json({
                        "type": "status",
                        "level": msg["level"],
                        "message": msg["message"]
                    })
                last_msg_idx = len(monitor["messages"])

            monitor["elapsed_seconds"] = int(time.time() - start_time)

            # Check for client messages (like stop)
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=1.0
                )
                if data == "stop":
                    services.monitor.stop()
                    monitor["status"] = "stopping"
            except asyncio.TimeoutError:
                pass

            await asyncio.sleep(0.5)

        thread.join()

        # Send any remaining messages
        for msg in monitor["messages"][last_msg_idx:]:
            await websocket.send_json({
                "type": "status",
                "level": msg["level"],
                "message": msg["message"]
            })

        # Send final results
        if result_holder["error"]:
            monitor["status"] = "error"
            await websocket.send_json({
                "type": "error",
                "message": result_holder["error"]
            })
        else:
            monitor["status"] = "completed"
            monitor["results"] = result_holder["results"] or {}

            # Sync bookings to graph
            for member_id, result in monitor["results"].items():
                if result.get("success") and result.get("voucher"):
                    slot = result.get("slot", {})
                    services.graph.sync_booking(
                        voucher=result["voucher"],
                        access_code=result.get("access_code", ""),
                        member_id=member_id,
                        date=slot.get("date", ""),
                        interval=slot.get("interval", ""),
                        level=slot.get("level"),
                        wave_side=slot.get("wave_side")
                    )

            await websocket.send_json({
                "type": "completed",
                "results": monitor["results"],
                "elapsed_seconds": monitor["elapsed_seconds"]
            })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for monitor {monitor_id}")
        services.monitor.stop()
        monitor["status"] = "disconnected"
    except Exception as e:
        logger.error(f"Monitor error: {e}")
        monitor["status"] = "error"
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass
    finally:
        await websocket.close()
