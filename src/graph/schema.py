"""
Graph schema definitions.

Defines node types, edge types, and their properties for the knowledge graph.
Based on the ontology designed in the plan.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict


class NodeType(str, Enum):
    """Types of nodes in the graph."""
    USER = "User"
    MEMBER = "Member"
    SPORT = "Sport"
    PREFERENCE = "Preference"
    LEVEL = "Level"           # Surf-specific
    WAVE_SIDE = "WaveSide"    # Surf-specific
    COURT = "Court"           # Tennis-specific
    TIME_SLOT = "TimeSlot"
    BOOKING = "Booking"
    SLOT = "Slot"
    DATE = "Date"


class EdgeType(str, Enum):
    """Types of edges (relationships) in the graph."""
    # User -> Member
    HAS_MEMBER = "HAS_MEMBER"

    # Member -> Preference
    HAS_PREFERENCE = "HAS_PREFERENCE"

    # Preference -> Sport
    FOR_SPORT = "FOR_SPORT"

    # Preference -> Level (Surf)
    PREFERS_LEVEL = "PREFERS_LEVEL"

    # Preference -> WaveSide (Surf)
    PREFERS_WAVE_SIDE = "PREFERS_WAVE_SIDE"

    # Preference -> Court (Tennis)
    PREFERS_COURT = "PREFERS_COURT"

    # Member -> TimeSlot
    PREFERS_HOUR = "PREFERS_HOUR"

    # Member -> Booking
    BOOKED = "BOOKED"

    # Booking -> Slot
    FOR_SLOT = "FOR_SLOT"

    # Slot -> Date
    ON_DATE = "ON_DATE"

    # Slot -> Level (attribute)
    HAS_LEVEL = "HAS_LEVEL"

    # Slot -> WaveSide (attribute)
    HAS_WAVE_SIDE = "HAS_WAVE_SIDE"

    # Slot -> Court (attribute)
    HAS_COURT = "HAS_COURT"


def create_node_id(node_type: NodeType, identifier: str) -> str:
    """
    Create a unique node ID.

    Args:
        node_type: Type of the node
        identifier: Unique identifier within the type

    Returns:
        Formatted node ID (e.g., "user:+5511999999999")
    """
    return f"{node_type.value.lower()}:{identifier}"


# Sport-specific attributes configuration
SPORT_ATTRIBUTES: Dict[str, Dict[str, List[str]]] = {
    "surf": {
        "level": [
            "Iniciante1", "Iniciante2",
            "Intermediario1", "Intermediario2",
            "Avançado1", "Avançado2"
        ],
        "wave_side": ["Lado_esquerdo", "Lado_direito"]
    },
    "tennis": {
        "court": ["Quadra_Saibro"]
    }
}


@dataclass
class Node:
    """Base node representation."""
    id: str
    type: NodeType
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "properties": self.properties
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Node":
        return cls(
            id=data["id"],
            type=NodeType(data["type"]),
            properties=data.get("properties", {})
        )


@dataclass
class Edge:
    """Edge (relationship) representation."""
    source: str
    target: str
    type: EdgeType
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type.value,
            "properties": self.properties
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Edge":
        return cls(
            source=data["source"],
            target=data["target"],
            type=EdgeType(data["type"]),
            properties=data.get("properties", {})
        )


# Node factory functions for common node types

def create_user_node(phone: str, name: Optional[str] = None) -> Node:
    """Create a User node."""
    return Node(
        id=create_node_id(NodeType.USER, phone),
        type=NodeType.USER,
        properties={"phone": phone, "name": name}
    )


def create_member_node(
    member_id: int,
    name: str,
    social_name: str,
    is_titular: bool = False
) -> Node:
    """Create a Member node."""
    return Node(
        id=create_node_id(NodeType.MEMBER, str(member_id)),
        type=NodeType.MEMBER,
        properties={
            "member_id": member_id,
            "name": name,
            "social_name": social_name,
            "is_titular": is_titular
        }
    )


def create_sport_node(sport: str) -> Node:
    """Create a Sport node."""
    return Node(
        id=create_node_id(NodeType.SPORT, sport),
        type=NodeType.SPORT,
        properties={"name": sport}
    )


def create_preference_node(
    preference_id: str,
    sport: str,
    priority: int = 1,
    attributes: Optional[Dict[str, str]] = None
) -> Node:
    """Create a Preference node."""
    return Node(
        id=create_node_id(NodeType.PREFERENCE, preference_id),
        type=NodeType.PREFERENCE,
        properties={
            "sport": sport,
            "priority": priority,
            "attributes": attributes or {}
        }
    )


def create_level_node(level: str, sport: str = "surf") -> Node:
    """Create a Level node (Surf-specific)."""
    return Node(
        id=create_node_id(NodeType.LEVEL, f"{sport}:{level}"),
        type=NodeType.LEVEL,
        properties={"name": level, "sport": sport}
    )


def create_wave_side_node(wave_side: str, sport: str = "surf") -> Node:
    """Create a WaveSide node (Surf-specific)."""
    return Node(
        id=create_node_id(NodeType.WAVE_SIDE, f"{sport}:{wave_side}"),
        type=NodeType.WAVE_SIDE,
        properties={"name": wave_side, "sport": sport}
    )


def create_court_node(court: str, sport: str = "tennis") -> Node:
    """Create a Court node (Tennis-specific)."""
    return Node(
        id=create_node_id(NodeType.COURT, f"{sport}:{court}"),
        type=NodeType.COURT,
        properties={"name": court, "sport": sport}
    )


def create_time_slot_node(hour: str) -> Node:
    """Create a TimeSlot node."""
    return Node(
        id=create_node_id(NodeType.TIME_SLOT, hour),
        type=NodeType.TIME_SLOT,
        properties={"hour": hour}
    )


def create_booking_node(
    voucher: str,
    access_code: str,
    status: str = "AccessReady",
    created_at: Optional[str] = None
) -> Node:
    """Create a Booking node."""
    from datetime import datetime
    return Node(
        id=create_node_id(NodeType.BOOKING, voucher),
        type=NodeType.BOOKING,
        properties={
            "voucher": voucher,
            "access_code": access_code,
            "status": status,
            "created_at": created_at or datetime.utcnow().isoformat()
        }
    )


def create_slot_node(
    slot_id: str,
    date: str,
    interval: str,
    available: int,
    max_quantity: int,
    level: Optional[str] = None,
    wave_side: Optional[str] = None,
    court: Optional[str] = None
) -> Node:
    """Create a Slot node."""
    props = {
        "date": date,
        "interval": interval,
        "available": available,
        "max_quantity": max_quantity
    }
    if level:
        props["level"] = level
    if wave_side:
        props["wave_side"] = wave_side
    if court:
        props["court"] = court

    return Node(
        id=create_node_id(NodeType.SLOT, slot_id),
        type=NodeType.SLOT,
        properties=props
    )


def create_date_node(date: str) -> Node:
    """Create a Date node."""
    return Node(
        id=create_node_id(NodeType.DATE, date),
        type=NodeType.DATE,
        properties={"value": date}
    )
