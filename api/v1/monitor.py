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
from src.config import SESSION_FIXED_HOURS

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
    check_interval_seconds: int = Field(12, description="Check interval in seconds")


class SessionSearchRequest(BaseModel):
    """Session search request with specific parameters."""
    member_id: int = Field(..., description="Member ID to book for")
    level: str = Field(..., description="Session level (Iniciante1, Iniciante2, Intermediario1, Intermediario2, Avançado1, Avançado2)")
    target_date: str = Field(..., description="Target date (YYYY-MM-DD)")
    target_hour: Optional[str] = Field(None, description="Target hour (HH:MM) - optional, searches all valid hours in order if not specified")
    wave_side: Optional[str] = Field(None, description="Wave side (Lado_esquerdo or Lado_direito) - optional, searches both if not specified")
    auto_book: bool = Field(True, description="Auto-book when slot found")
    duration_minutes: int = Field(120, description="Duration in minutes")
    check_interval_seconds: int = Field(12, description="Check interval in seconds")


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


@router.get("/user/active")
async def get_user_active_monitors(
    services: ServicesDep,
    current_user: CurrentUser
):
    """
    Get all active monitors for the current user with full details.

    Returns monitors with complete info for UI display.
    """
    import time as time_module

    result = []
    monitors_to_update = []

    for monitor_id, m in active_monitors.items():
        if m.get("user_phone") != current_user.phone:
            continue

        # Check if thread is still alive (for background monitors)
        thread = m.get("_thread")
        if thread and not thread.is_alive():
            # Thread finished while disconnected - update status
            if m.get("status") == "running":
                m["status"] = "completed"

        # Only return active or recently completed monitors
        if m.get("status") not in ["pending", "running", "completed", "error", "stopping"]:
            continue

        # Calculate elapsed time for running monitors
        if m.get("status") == "running" and m.get("started_at"):
            m["elapsed_seconds"] = int(time_module.time() - m["started_at"])

        monitor_info = {
            "monitor_id": monitor_id,
            "type": m.get("type", "auto_monitor"),
            "status": m.get("status", "unknown"),
            "member_id": m.get("member_id"),
            "member_name": m.get("member_name"),
            "level": m.get("level"),
            "wave_side": m.get("wave_side"),
            "target_date": m.get("target_date"),
            "target_hour": m.get("target_hour"),
            "duration_minutes": m.get("duration_minutes", 120),
            "elapsed_seconds": m.get("elapsed_seconds", 0),
            "started_at": m.get("started_at"),
            "messages": m.get("messages", [])[-50:],  # Last 50 messages
            "result": m.get("result")
        }

        result.append(monitor_info)

    return {"monitors": result}


class UpdateMonitorRequest(BaseModel):
    """Update monitor request."""
    level: Optional[str] = Field(None, description="New level")
    wave_side: Optional[str] = Field(None, description="New wave side")
    target_hour: Optional[str] = Field(None, description="New target hour")
    duration_minutes: Optional[int] = Field(None, description="New duration in minutes")


@router.put("/{monitor_id}/update")
async def update_monitor(
    monitor_id: str,
    request: UpdateMonitorRequest,
    services: ServicesDep,
    current_user: CurrentUser
):
    """
    Update a running monitor's configuration.

    If level changes, the monitor will be restarted with new parameters.
    """
    if monitor_id not in active_monitors:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Monitor {monitor_id} not found"
        )

    monitor = active_monitors[monitor_id]

    # Verify ownership
    if monitor.get("user_phone") != current_user.phone:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this monitor"
        )

    # Check if monitor is still running
    if monitor.get("status") not in ["pending", "running"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot update monitor with status: {monitor.get('status')}"
        )

    needs_restart = False
    updated_fields = []

    # Update fields
    if request.level is not None and request.level != monitor.get("level"):
        # Validate level
        if request.level not in SESSION_FIXED_HOURS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid level: {request.level}"
            )
        monitor["level"] = request.level
        needs_restart = True
        updated_fields.append("level")

    if request.wave_side is not None and request.wave_side != monitor.get("wave_side"):
        valid_sides = ["Lado_esquerdo", "Lado_direito"]
        if request.wave_side not in valid_sides:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid wave_side: {request.wave_side}"
            )
        monitor["wave_side"] = request.wave_side
        updated_fields.append("wave_side")

    if request.target_hour is not None and request.target_hour != monitor.get("target_hour"):
        level = request.level or monitor.get("level")
        if level:
            valid_hours = SESSION_FIXED_HOURS.get(level, [])
            if request.target_hour not in valid_hours:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid hour {request.target_hour} for level {level}"
                )
        monitor["target_hour"] = request.target_hour
        updated_fields.append("target_hour")

    if request.duration_minutes is not None and request.duration_minutes != monitor.get("duration_minutes"):
        if request.duration_minutes not in [60, 120, 180, 240, 300, 360]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duration must be one of: 60, 120, 180, 240, 300, 360"
            )
        monitor["duration_minutes"] = request.duration_minutes
        needs_restart = True  # Duration change requires restart to take effect
        updated_fields.append("duration_minutes")

    if needs_restart:
        # Stop current monitor
        services.monitor.stop()
        monitor["messages"].append({
            "message": f"Monitor atualizado. Campos: {', '.join(updated_fields)}. Reiniciando...",
            "level": "info"
        })

        # Restart monitor in background if it's a session_search type
        if monitor.get("type") == "session_search":
            import threading
            import time

            # Reset elapsed time for new search
            monitor["started_at"] = time.time()
            monitor["status"] = "running"

            def status_callback(message: str, level: str):
                monitor["messages"].append({"message": message, "level": level})

            def run_session_search():
                try:
                    result = services.monitor.run_session_search(
                        member_id=monitor["member_id"],
                        level=monitor["level"],
                        wave_side=monitor.get("wave_side"),
                        target_date=monitor["target_date"],
                        target_hour=monitor.get("target_hour"),
                        auto_book=monitor.get("auto_book", True),
                        duration_minutes=monitor["duration_minutes"],
                        check_interval_seconds=monitor.get("check_interval_seconds", 12),
                        on_status_update=status_callback
                    )
                    monitor["result"] = result
                    if result.get("success"):
                        monitor["status"] = "completed"
                        # Sync booking to graph
                        slot = result.get("slot", {})
                        if result.get("voucher"):
                            services.graph.sync_booking(
                                voucher=result["voucher"],
                                access_code=result.get("access_code", ""),
                                member_id=monitor["member_id"],
                                date=slot.get("date", ""),
                                interval=slot.get("interval", ""),
                                level=slot.get("level"),
                                wave_side=slot.get("wave_side")
                            )
                    else:
                        monitor["status"] = "completed"
                except Exception as e:
                    monitor["result"] = {"success": False, "error": str(e)}
                    monitor["status"] = "error"

            # Update elapsed_seconds periodically
            def update_elapsed():
                while monitor.get("status") == "running":
                    if monitor.get("started_at"):
                        monitor["elapsed_seconds"] = int(time.time() - monitor["started_at"])
                    time.sleep(1)

            thread = threading.Thread(target=run_session_search, daemon=True)
            thread.start()
            monitor["_thread"] = thread

            elapsed_thread = threading.Thread(target=update_elapsed, daemon=True)
            elapsed_thread.start()
        else:
            monitor["status"] = "pending"
    else:
        monitor["messages"].append({
            "message": f"Monitor atualizado. Campos: {', '.join(updated_fields)}",
            "level": "info"
        })

    return {
        "success": True,
        "monitor_id": monitor_id,
        "message": f"Monitor atualizado: {', '.join(updated_fields)}",
        "restarted": needs_restart,
        "updated_fields": updated_fields
    }


@router.get("/session-options")
async def get_session_options(
    services: ServicesDep,
    current_user: CurrentUser
):
    """
    Get available session options with fixed hours per level.

    Returns:
        - levels: Available session levels
        - wave_sides: Available wave sides
        - hours_by_level: Valid hours for each level
    """
    return {
        "levels": list(SESSION_FIXED_HOURS.keys()),
        "wave_sides": ["Lado_esquerdo", "Lado_direito"],
        "hours_by_level": SESSION_FIXED_HOURS
    }


@router.post("/search-session")
async def start_session_search(
    request: SessionSearchRequest,
    services: ServicesDep,
    current_user: CurrentUser,
    sport: str = Query("surf", description="Sport")
):
    """
    Start a session search with specific parameters.

    Unlike /start which uses member preferences, this endpoint allows
    the user to specify exactly which session they want:
    - Specific level (e.g., "Iniciante2")
    - Specific wave side (e.g., "Lado_esquerdo")
    - Specific date (e.g., "2025-12-26")
    - Specific hour (must be valid for the level)

    Returns a monitor_id for tracking. Use the WebSocket endpoint
    to receive real-time updates.
    """
    services.context.set_sport(sport)

    # Initialize Beyond API using user's tokens
    ensure_beyond_api(services, current_user)

    # Validate level
    if request.level not in SESSION_FIXED_HOURS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid level: {request.level}. Valid levels: {list(SESSION_FIXED_HOURS.keys())}"
        )

    # Validate hour for the level (only if specified)
    valid_hours = SESSION_FIXED_HOURS[request.level]
    if request.target_hour and request.target_hour not in valid_hours:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid hour {request.target_hour} for {request.level}. Valid hours: {valid_hours}"
        )

    # Validate wave_side if provided
    valid_sides = ["Lado_esquerdo", "Lado_direito"]
    if request.wave_side and request.wave_side not in valid_sides:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid wave_side: {request.wave_side}. Valid sides: {valid_sides}"
        )

    # Verify member exists
    member = services.members.get_member_by_id(request.member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Member {request.member_id} not found"
        )

    # Create monitor ID
    monitor_id = str(uuid4())[:8]

    # Store monitor info
    active_monitors[monitor_id] = {
        "status": "pending",
        "type": "session_search",
        "member_id": request.member_id,
        "member_name": member.social_name,
        "level": request.level,
        "wave_side": request.wave_side,
        "target_date": request.target_date,
        "target_hour": request.target_hour,
        "auto_book": request.auto_book,
        "duration_minutes": request.duration_minutes,
        "check_interval_seconds": request.check_interval_seconds,
        "sport": sport,
        "user_phone": current_user.phone,
        "result": {},
        "messages": [],
        "started_at": None,
        "elapsed_seconds": 0
    }

    side_desc = request.wave_side if request.wave_side else "ambos os lados"
    hour_desc = request.target_hour if request.target_hour else "qualquer horário"

    return {
        "monitor_id": monitor_id,
        "status": "pending",
        "message": f"Session search created. Connect to WebSocket /ws/monitor/{monitor_id}/session to start.",
        "member_id": request.member_id,
        "member_name": member.social_name,
        "session": {
            "level": request.level,
            "wave_side": side_desc,
            "date": request.target_date,
            "hour": hour_desc
        }
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
        import time
        start_time = time.time()
        monitor["status"] = "running"
        monitor["started_at"] = start_time
        await websocket.send_json({
            "type": "started",
            "monitor_id": monitor_id,
            "member_ids": monitor["member_ids"]
        })

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
        # DO NOT stop the monitor when WebSocket disconnects
        # Monitor continues running in background
        logger.info(f"WebSocket disconnected for monitor {monitor_id} - monitor continues in background")
        # Keep the thread reference so we can check if it's still alive later
        if thread.is_alive():
            monitor["status"] = "running"
            monitor["_thread"] = thread
        return  # Don't close websocket, just return
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
        try:
            await websocket.close()
        except Exception:
            pass


@router.websocket("/ws/{monitor_id}/session")
async def session_search_websocket(websocket: WebSocket, monitor_id: str):
    """
    WebSocket endpoint for real-time session search updates.

    Connect to start the session search and receive status updates.
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

    # Verify this is a session search type monitor
    if monitor.get("type") != "session_search":
        await websocket.send_json({
            "type": "error",
            "message": f"Monitor {monitor_id} is not a session search"
        })
        await websocket.close()
        return

    services = get_services()

    # Set sport context
    services.context.set_sport(monitor["sport"])

    # Initialize Beyond API using user's Beyond tokens
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
    def status_callback(message: str, level: str):
        monitor["messages"].append({"message": message, "level": level})

    try:
        # Start the session search
        import time
        start_time = time.time()
        monitor["status"] = "running"
        monitor["started_at"] = start_time
        await websocket.send_json({
            "type": "started",
            "monitor_id": monitor_id,
            "member_id": monitor["member_id"],
            "member_name": monitor["member_name"],
            "session": {
                "level": monitor["level"],
                "wave_side": monitor["wave_side"],
                "date": monitor["target_date"],
                "hour": monitor["target_hour"]
            }
        })

        # Run session search in a thread to not block
        import threading
        result_holder = {"result": None, "error": None}

        def run_session_search():
            try:
                result = services.monitor.run_session_search(
                    member_id=monitor["member_id"],
                    level=monitor["level"],
                    wave_side=monitor["wave_side"],
                    target_date=monitor["target_date"],
                    target_hour=monitor["target_hour"],
                    auto_book=monitor["auto_book"],
                    duration_minutes=monitor["duration_minutes"],
                    check_interval_seconds=monitor["check_interval_seconds"],
                    on_status_update=status_callback
                )
                result_holder["result"] = result
            except Exception as e:
                result_holder["error"] = str(e)

        thread = threading.Thread(target=run_session_search)
        thread.start()

        # Send updates while search runs
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

        # Send final result
        if result_holder["error"]:
            monitor["status"] = "error"
            await websocket.send_json({
                "type": "error",
                "message": result_holder["error"]
            })
        else:
            result = result_holder["result"] or {}
            monitor["status"] = "completed"
            monitor["result"] = result

            # Sync booking to graph if successful
            if result.get("success") and result.get("voucher"):
                slot = result.get("slot", {})
                services.graph.sync_booking(
                    voucher=result["voucher"],
                    access_code=result.get("access_code", ""),
                    member_id=monitor["member_id"],
                    date=slot.get("date", ""),
                    interval=slot.get("interval", ""),
                    level=slot.get("level"),
                    wave_side=slot.get("wave_side")
                )

            await websocket.send_json({
                "type": "completed",
                "result": result,
                "elapsed_seconds": monitor["elapsed_seconds"]
            })

    except WebSocketDisconnect:
        # DO NOT stop the monitor when WebSocket disconnects
        # Monitor continues running in background
        logger.info(f"WebSocket disconnected for session search {monitor_id} - monitor continues in background")
        # Keep the thread reference so we can check if it's still alive later
        if thread.is_alive():
            monitor["status"] = "running"
            monitor["_thread"] = thread
        return  # Don't close websocket, just return
    except Exception as e:
        logger.error(f"Session search error: {e}")
        monitor["status"] = "error"
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
