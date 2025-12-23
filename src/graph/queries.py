"""
Semantic graph queries.

Provides high-level query operations for the knowledge graph.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import Counter

from .schema import NodeType, EdgeType, create_node_id, Node
from .store import GraphStore

logger = logging.getLogger(__name__)


class GraphQueries:
    """
    High-level semantic queries on the knowledge graph.

    Provides domain-specific queries for:
    - Finding optimal slots based on preferences
    - Member similarity analysis
    - Booking history and patterns
    - Recommendations
    """

    def __init__(self, store: GraphStore):
        """
        Initialize query interface.

        Args:
            store: GraphStore instance
        """
        self.store = store

    # === Member Queries ===

    def get_member_preferences(
        self,
        member_id: int,
        sport: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all preferences for a member.

        Args:
            member_id: Beyond member ID
            sport: Optional sport filter

        Returns:
            List of preference dictionaries with full details
        """
        member_node_id = create_node_id(NodeType.MEMBER, str(member_id))

        if not self.store.has_node(member_node_id):
            return []

        # Get preferences linked to member
        pref_nodes = self.store.get_neighbors(
            member_node_id,
            edge_type=EdgeType.HAS_PREFERENCE,
            direction="out"
        )

        preferences = []
        for pref_node in pref_nodes:
            pref_data = pref_node.properties.copy()
            pref_data["preference_id"] = pref_node.id

            # Filter by sport if specified
            if sport and pref_data.get("sport") != sport:
                continue

            # Get linked attributes (level, wave_side, court)
            for neighbor in self.store.get_neighbors(pref_node.id, direction="out"):
                if neighbor.type == NodeType.LEVEL:
                    pref_data["level"] = neighbor.properties.get("name")
                elif neighbor.type == NodeType.WAVE_SIDE:
                    pref_data["wave_side"] = neighbor.properties.get("name")
                elif neighbor.type == NodeType.COURT:
                    pref_data["court"] = neighbor.properties.get("name")

            preferences.append(pref_data)

        # Sort by priority
        preferences.sort(key=lambda p: p.get("priority", 99))
        return preferences

    def get_member_booking_history(
        self,
        member_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get booking history for a member.

        Args:
            member_id: Beyond member ID
            limit: Maximum number of bookings to return

        Returns:
            List of booking dictionaries with slot details
        """
        member_node_id = create_node_id(NodeType.MEMBER, str(member_id))

        if not self.store.has_node(member_node_id):
            return []

        bookings = []
        booking_nodes = self.store.get_neighbors(
            member_node_id,
            edge_type=EdgeType.BOOKED,
            direction="out"
        )

        for booking_node in booking_nodes:
            booking_data = booking_node.properties.copy()
            booking_data["booking_id"] = booking_node.id

            # Get linked slot
            slot_nodes = self.store.get_neighbors(
                booking_node.id,
                edge_type=EdgeType.FOR_SLOT,
                direction="out"
            )
            if slot_nodes:
                slot = slot_nodes[0]
                booking_data["slot"] = slot.properties

            bookings.append(booking_data)

        # Sort by created_at descending
        bookings.sort(
            key=lambda b: b.get("created_at", ""),
            reverse=True
        )

        return bookings[:limit]

    def get_member_preferred_hours(self, member_id: int) -> List[str]:
        """
        Get preferred hours for a member.

        Args:
            member_id: Beyond member ID

        Returns:
            List of preferred hours (e.g., ["08:00", "09:00"])
        """
        member_node_id = create_node_id(NodeType.MEMBER, str(member_id))

        if not self.store.has_node(member_node_id):
            return []

        time_slots = self.store.get_neighbors(
            member_node_id,
            edge_type=EdgeType.PREFERS_HOUR,
            direction="out"
        )

        return [ts.properties.get("hour") for ts in time_slots if ts.properties.get("hour")]

    # === Similarity Queries ===

    def find_similar_members(
        self,
        member_id: int,
        sport: str = "surf"
    ) -> List[Dict[str, Any]]:
        """
        Find members with similar preferences.

        Args:
            member_id: Reference member ID
            sport: Sport to compare preferences for

        Returns:
            List of similar members with similarity scores
        """
        # Get reference member's preferences
        ref_prefs = self.get_member_preferences(member_id, sport)
        if not ref_prefs:
            return []

        # Extract preference attributes
        ref_attrs = set()
        for pref in ref_prefs:
            if pref.get("level"):
                ref_attrs.add(("level", pref["level"]))
            if pref.get("wave_side"):
                ref_attrs.add(("wave_side", pref["wave_side"]))
            if pref.get("court"):
                ref_attrs.add(("court", pref["court"]))

        # Find all members
        member_nodes = self.store.get_nodes_by_type(NodeType.MEMBER)
        similar = []

        for member_node in member_nodes:
            other_id = member_node.properties.get("member_id")
            if other_id == member_id:
                continue

            other_prefs = self.get_member_preferences(other_id, sport)
            if not other_prefs:
                continue

            # Extract other member's attributes
            other_attrs = set()
            for pref in other_prefs:
                if pref.get("level"):
                    other_attrs.add(("level", pref["level"]))
                if pref.get("wave_side"):
                    other_attrs.add(("wave_side", pref["wave_side"]))
                if pref.get("court"):
                    other_attrs.add(("court", pref["court"]))

            # Calculate Jaccard similarity
            intersection = len(ref_attrs & other_attrs)
            union = len(ref_attrs | other_attrs)
            similarity = intersection / union if union > 0 else 0

            if similarity > 0:
                similar.append({
                    "member_id": other_id,
                    "name": member_node.properties.get("social_name"),
                    "similarity": round(similarity, 2),
                    "shared_preferences": list(ref_attrs & other_attrs)
                })

        # Sort by similarity descending
        similar.sort(key=lambda x: x["similarity"], reverse=True)
        return similar

    # === Slot Queries ===

    def find_slots_for_preference(
        self,
        level: Optional[str] = None,
        wave_side: Optional[str] = None,
        court: Optional[str] = None,
        date: Optional[str] = None,
        min_available: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Find available slots matching preference criteria.

        Args:
            level: Level filter (Surf)
            wave_side: Wave side filter (Surf)
            court: Court filter (Tennis)
            date: Date filter (YYYY-MM-DD)
            min_available: Minimum available spots

        Returns:
            List of matching slot dictionaries
        """
        slot_nodes = self.store.get_nodes_by_type(NodeType.SLOT)
        matching = []

        for slot in slot_nodes:
            props = slot.properties

            # Check availability
            if props.get("available", 0) < min_available:
                continue

            # Check date
            if date and props.get("date") != date:
                continue

            # Check attributes
            if level and props.get("level") != level:
                continue
            if wave_side and props.get("wave_side") != wave_side:
                continue
            if court and props.get("court") != court:
                continue

            matching.append({
                "slot_id": slot.id,
                **props
            })

        # Sort by date and interval
        matching.sort(key=lambda s: (s.get("date", ""), s.get("interval", "")))
        return matching

    def find_optimal_slot(
        self,
        member_id: int,
        sport: str = "surf",
        date: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find the best available slot based on member's preferences.

        Args:
            member_id: Member ID
            sport: Sport type
            date: Optional date filter

        Returns:
            Best matching slot or None
        """
        prefs = self.get_member_preferences(member_id, sport)
        if not prefs:
            return None

        preferred_hours = self.get_member_preferred_hours(member_id)

        # Try each preference in priority order
        for pref in prefs:
            slots = self.find_slots_for_preference(
                level=pref.get("level"),
                wave_side=pref.get("wave_side"),
                court=pref.get("court"),
                date=date
            )

            if not slots:
                continue

            # Prefer slots at preferred hours
            if preferred_hours:
                for slot in slots:
                    if slot.get("interval") in preferred_hours:
                        return slot

            # Return first available
            return slots[0]

        return None

    # === Analytics Queries ===

    def get_popular_combos(
        self,
        sport: str = "surf",
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get most popular level/wave_side or court combinations.

        Args:
            sport: Sport to analyze
            limit: Number of top combos to return

        Returns:
            List of combo dictionaries with booking counts
        """
        # Count bookings by combo
        combo_counts = Counter()

        booking_nodes = self.store.get_nodes_by_type(NodeType.BOOKING)
        for booking in booking_nodes:
            # Get linked slot
            slot_nodes = self.store.get_neighbors(
                booking.id,
                edge_type=EdgeType.FOR_SLOT,
                direction="out"
            )
            if not slot_nodes:
                continue

            slot = slot_nodes[0].properties
            if sport == "surf":
                level = slot.get("level")
                wave_side = slot.get("wave_side")
                if level and wave_side:
                    combo_counts[(level, wave_side)] += 1
            elif sport == "tennis":
                court = slot.get("court")
                if court:
                    combo_counts[(court,)] += 1

        # Format results
        results = []
        for combo, count in combo_counts.most_common(limit):
            if sport == "surf":
                results.append({
                    "level": combo[0],
                    "wave_side": combo[1],
                    "booking_count": count
                })
            elif sport == "tennis":
                results.append({
                    "court": combo[0],
                    "booking_count": count
                })

        return results

    def get_booking_stats_by_date(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Get booking counts grouped by date.

        Args:
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary mapping dates to booking counts
        """
        date_counts = Counter()

        booking_nodes = self.store.get_nodes_by_type(NodeType.BOOKING)
        for booking in booking_nodes:
            slot_nodes = self.store.get_neighbors(
                booking.id,
                edge_type=EdgeType.FOR_SLOT,
                direction="out"
            )
            if not slot_nodes:
                continue

            date = slot_nodes[0].properties.get("date")
            if not date:
                continue

            # Apply date filters
            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue

            date_counts[date] += 1

        return dict(sorted(date_counts.items()))

    # === User Queries ===

    def get_user_members(self, phone: str) -> List[Dict[str, Any]]:
        """
        Get all members linked to a user.

        Args:
            phone: User's phone number

        Returns:
            List of member dictionaries
        """
        user_node_id = create_node_id(NodeType.USER, phone)

        if not self.store.has_node(user_node_id):
            return []

        member_nodes = self.store.get_neighbors(
            user_node_id,
            edge_type=EdgeType.HAS_MEMBER,
            direction="out"
        )

        return [
            {
                "member_id": m.properties.get("member_id"),
                "name": m.properties.get("name"),
                "social_name": m.properties.get("social_name"),
                "is_titular": m.properties.get("is_titular", False)
            }
            for m in member_nodes
        ]

    def get_member_graph_summary(self, member_id: int) -> Dict[str, Any]:
        """
        Get a summary of all graph data for a member.

        Args:
            member_id: Beyond member ID

        Returns:
            Dictionary with preferences, bookings, and stats
        """
        return {
            "member_id": member_id,
            "preferences": self.get_member_preferences(member_id),
            "preferred_hours": self.get_member_preferred_hours(member_id),
            "recent_bookings": self.get_member_booking_history(member_id, limit=5),
            "similar_members": self.find_similar_members(member_id)[:3]
        }
