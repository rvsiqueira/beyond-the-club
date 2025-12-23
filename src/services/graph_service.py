"""
Graph service.

High-level service for graph operations and synchronization with other services.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..graph import GraphStore, GraphQueries, NodeType, EdgeType, create_node_id
from ..graph.schema import (
    Node, Edge,
    create_user_node, create_member_node, create_preference_node,
    create_booking_node, create_slot_node, create_date_node,
    create_time_slot_node, create_level_node, create_wave_side_node
)

logger = logging.getLogger(__name__)


class GraphService:
    """
    Service for graph operations.

    Provides:
    - High-level operations for managing the knowledge graph
    - Synchronization with other services (members, bookings)
    - Query interface for semantic searches
    """

    def __init__(self, store: Optional[GraphStore] = None):
        """
        Initialize graph service.

        Args:
            store: Optional GraphStore (creates default if not provided)
        """
        self.store = store or GraphStore()
        self.queries = GraphQueries(self.store)

    def save(self):
        """Persist graph to disk."""
        self.store.save()

    # === User Operations ===

    def sync_user(
        self,
        phone: str,
        name: Optional[str] = None,
        member_ids: Optional[List[int]] = None
    ) -> Node:
        """
        Sync a user to the graph.

        Creates or updates user node and links to members.

        Args:
            phone: User's phone number
            name: Optional user name
            member_ids: Optional list of member IDs to link

        Returns:
            User node
        """
        user_node = create_user_node(phone, name)

        if self.store.has_node(user_node.id):
            self.store.update_node(user_node)
        else:
            self.store.add_node(user_node)

        # Link to members if provided
        if member_ids:
            for member_id in member_ids:
                self.link_user_to_member(phone, member_id)

        return user_node

    def link_user_to_member(self, phone: str, member_id: int) -> bool:
        """
        Create a HAS_MEMBER edge from user to member.

        Args:
            phone: User's phone number
            member_id: Member ID to link

        Returns:
            True if edge created
        """
        user_id = create_node_id(NodeType.USER, phone)
        member_node_id = create_node_id(NodeType.MEMBER, str(member_id))

        if not self.store.has_node(user_id):
            logger.warning(f"User {phone} not found in graph")
            return False

        if not self.store.has_node(member_node_id):
            logger.warning(f"Member {member_id} not found in graph")
            return False

        edge = Edge(
            source=user_id,
            target=member_node_id,
            type=EdgeType.HAS_MEMBER
        )
        return self.store.add_edge(edge)

    # === Member Operations ===

    def sync_member(
        self,
        member_id: int,
        name: str,
        social_name: str,
        is_titular: bool = False
    ) -> Node:
        """
        Sync a member to the graph.

        Args:
            member_id: Beyond member ID
            name: Full name
            social_name: Display name
            is_titular: Whether this is the titular member

        Returns:
            Member node
        """
        member_node = create_member_node(member_id, name, social_name, is_titular)

        if self.store.has_node(member_node.id):
            self.store.update_node(member_node)
        else:
            self.store.add_node(member_node)

        return member_node

    def sync_member_preference(
        self,
        member_id: int,
        sport: str,
        priority: int,
        level: Optional[str] = None,
        wave_side: Optional[str] = None,
        court: Optional[str] = None,
        target_hours: Optional[List[str]] = None
    ) -> Node:
        """
        Sync a member's preference to the graph.

        Creates preference node and links to member and attributes.

        Args:
            member_id: Beyond member ID
            sport: Sport name
            priority: Preference priority (1 = highest)
            level: Level preference (Surf)
            wave_side: Wave side preference (Surf)
            court: Court preference (Tennis)
            target_hours: Preferred time slots

        Returns:
            Preference node
        """
        # Create unique preference ID
        pref_id = f"{member_id}:{sport}:{priority}"
        attributes = {}
        if level:
            attributes["level"] = level
        if wave_side:
            attributes["wave_side"] = wave_side
        if court:
            attributes["court"] = court

        pref_node = create_preference_node(pref_id, sport, priority, attributes)

        # Remove existing preference with same ID
        if self.store.has_node(pref_node.id):
            self.store.delete_node(pref_node.id)

        self.store.add_node(pref_node)

        # Link to member
        member_node_id = create_node_id(NodeType.MEMBER, str(member_id))
        if self.store.has_node(member_node_id):
            edge = Edge(
                source=member_node_id,
                target=pref_node.id,
                type=EdgeType.HAS_PREFERENCE,
                properties={"priority": priority}
            )
            self.store.add_edge(edge)

        # Link to sport
        sport_node_id = create_node_id(NodeType.SPORT, sport)
        if self.store.has_node(sport_node_id):
            edge = Edge(
                source=pref_node.id,
                target=sport_node_id,
                type=EdgeType.FOR_SPORT
            )
            self.store.add_edge(edge)

        # Link to level
        if level:
            level_node_id = create_node_id(NodeType.LEVEL, f"{sport}:{level}")
            if self.store.has_node(level_node_id):
                edge = Edge(
                    source=pref_node.id,
                    target=level_node_id,
                    type=EdgeType.PREFERS_LEVEL
                )
                self.store.add_edge(edge)

        # Link to wave_side
        if wave_side:
            ws_node_id = create_node_id(NodeType.WAVE_SIDE, f"{sport}:{wave_side}")
            if self.store.has_node(ws_node_id):
                edge = Edge(
                    source=pref_node.id,
                    target=ws_node_id,
                    type=EdgeType.PREFERS_WAVE_SIDE
                )
                self.store.add_edge(edge)

        # Link to court
        if court:
            court_node_id = create_node_id(NodeType.COURT, f"{sport}:{court}")
            if self.store.has_node(court_node_id):
                edge = Edge(
                    source=pref_node.id,
                    target=court_node_id,
                    type=EdgeType.PREFERS_COURT
                )
                self.store.add_edge(edge)

        # Link to preferred hours
        if target_hours:
            for hour in target_hours:
                self.sync_member_preferred_hour(member_id, hour)

        return pref_node

    def sync_member_preferred_hour(self, member_id: int, hour: str) -> bool:
        """
        Add a preferred hour for a member.

        Args:
            member_id: Beyond member ID
            hour: Hour string (e.g., "08:00")

        Returns:
            True if edge created
        """
        member_node_id = create_node_id(NodeType.MEMBER, str(member_id))
        time_node = create_time_slot_node(hour)

        if not self.store.has_node(time_node.id):
            self.store.add_node(time_node)

        if not self.store.has_node(member_node_id):
            return False

        edge = Edge(
            source=member_node_id,
            target=time_node.id,
            type=EdgeType.PREFERS_HOUR
        )
        return self.store.add_edge(edge)

    def clear_member_preferences(self, member_id: int, sport: Optional[str] = None):
        """
        Clear all preferences for a member.

        Args:
            member_id: Beyond member ID
            sport: Optional sport filter
        """
        member_node_id = create_node_id(NodeType.MEMBER, str(member_id))

        if not self.store.has_node(member_node_id):
            return

        # Find and delete preference nodes
        pref_nodes = self.store.get_neighbors(
            member_node_id,
            edge_type=EdgeType.HAS_PREFERENCE,
            direction="out"
        )

        for pref in pref_nodes:
            if sport and pref.properties.get("sport") != sport:
                continue
            self.store.delete_node(pref.id)

    # === Booking Operations ===

    def sync_booking(
        self,
        voucher: str,
        access_code: str,
        member_id: int,
        date: str,
        interval: str,
        level: Optional[str] = None,
        wave_side: Optional[str] = None,
        court: Optional[str] = None,
        status: str = "AccessReady"
    ) -> Node:
        """
        Sync a booking to the graph.

        Creates booking node and links to member, slot, and date.

        Args:
            voucher: Booking voucher code
            access_code: Access code
            member_id: Member who booked
            date: Booking date
            interval: Time interval
            level: Level (Surf)
            wave_side: Wave side (Surf)
            court: Court (Tennis)
            status: Booking status

        Returns:
            Booking node
        """
        # Create booking node
        booking_node = create_booking_node(voucher, access_code, status)
        self.store.add_node(booking_node)

        # Link to member
        member_node_id = create_node_id(NodeType.MEMBER, str(member_id))
        if self.store.has_node(member_node_id):
            edge = Edge(
                source=member_node_id,
                target=booking_node.id,
                type=EdgeType.BOOKED,
                properties={"booked_at": datetime.utcnow().isoformat()}
            )
            self.store.add_edge(edge)

        # Create and link slot
        slot_id = f"{date}:{interval}:{level or ''}:{wave_side or court or ''}"
        slot_node = create_slot_node(
            slot_id=slot_id,
            date=date,
            interval=interval,
            available=0,  # After booking
            max_quantity=6,
            level=level,
            wave_side=wave_side,
            court=court
        )

        if not self.store.has_node(slot_node.id):
            self.store.add_node(slot_node)

        edge = Edge(
            source=booking_node.id,
            target=slot_node.id,
            type=EdgeType.FOR_SLOT
        )
        self.store.add_edge(edge)

        # Create and link date
        date_node = create_date_node(date)
        if not self.store.has_node(date_node.id):
            self.store.add_node(date_node)

        edge = Edge(
            source=slot_node.id,
            target=date_node.id,
            type=EdgeType.ON_DATE
        )
        self.store.add_edge(edge)

        return booking_node

    def cancel_booking(self, voucher: str) -> bool:
        """
        Mark a booking as cancelled.

        Args:
            voucher: Booking voucher code

        Returns:
            True if updated
        """
        booking_id = create_node_id(NodeType.BOOKING, voucher)
        node = self.store.get_node(booking_id)

        if not node:
            return False

        node.properties["status"] = "Cancelled"
        node.properties["cancelled_at"] = datetime.utcnow().isoformat()
        return self.store.update_node(node)

    # === Slot Operations ===

    def sync_available_slot(
        self,
        date: str,
        interval: str,
        available: int,
        max_quantity: int,
        level: Optional[str] = None,
        wave_side: Optional[str] = None,
        court: Optional[str] = None
    ) -> Node:
        """
        Sync an available slot to the graph.

        Args:
            date: Slot date
            interval: Time interval
            available: Number of available spots
            max_quantity: Maximum capacity
            level: Level (Surf)
            wave_side: Wave side (Surf)
            court: Court (Tennis)

        Returns:
            Slot node
        """
        slot_id = f"{date}:{interval}:{level or ''}:{wave_side or court or ''}"
        slot_node = create_slot_node(
            slot_id=slot_id,
            date=date,
            interval=interval,
            available=available,
            max_quantity=max_quantity,
            level=level,
            wave_side=wave_side,
            court=court
        )

        if self.store.has_node(slot_node.id):
            self.store.update_node(slot_node)
        else:
            self.store.add_node(slot_node)

            # Link to date
            date_node = create_date_node(date)
            if not self.store.has_node(date_node.id):
                self.store.add_node(date_node)

            edge = Edge(
                source=slot_node.id,
                target=date_node.id,
                type=EdgeType.ON_DATE
            )
            self.store.add_edge(edge)

            # Link to level
            if level:
                level_id = create_node_id(NodeType.LEVEL, f"surf:{level}")
                if self.store.has_node(level_id):
                    edge = Edge(
                        source=slot_node.id,
                        target=level_id,
                        type=EdgeType.HAS_LEVEL
                    )
                    self.store.add_edge(edge)

            # Link to wave_side
            if wave_side:
                ws_id = create_node_id(NodeType.WAVE_SIDE, f"surf:{wave_side}")
                if self.store.has_node(ws_id):
                    edge = Edge(
                        source=slot_node.id,
                        target=ws_id,
                        type=EdgeType.HAS_WAVE_SIDE
                    )
                    self.store.add_edge(edge)

        return slot_node

    # === Query Proxies ===

    def get_member_preferences(self, member_id: int, sport: Optional[str] = None):
        """Get member preferences from graph."""
        return self.queries.get_member_preferences(member_id, sport)

    def get_member_booking_history(self, member_id: int, limit: int = 10):
        """Get member booking history from graph."""
        return self.queries.get_member_booking_history(member_id, limit)

    def find_similar_members(self, member_id: int, sport: str = "surf"):
        """Find members with similar preferences."""
        return self.queries.find_similar_members(member_id, sport)

    def find_optimal_slot(self, member_id: int, sport: str = "surf", date: Optional[str] = None):
        """Find optimal slot for member based on preferences."""
        return self.queries.find_optimal_slot(member_id, sport, date)

    def get_popular_combos(self, sport: str = "surf", limit: int = 5):
        """Get most popular level/wave_side combinations."""
        return self.queries.get_popular_combos(sport, limit)

    def get_user_members(self, phone: str):
        """Get members linked to a user."""
        return self.queries.get_user_members(phone)

    def get_member_summary(self, member_id: int):
        """Get full graph summary for a member."""
        return self.queries.get_member_graph_summary(member_id)

    def stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return self.store.stats()
