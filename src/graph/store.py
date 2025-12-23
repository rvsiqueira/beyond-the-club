"""
Graph storage using NetworkX.

Provides persistence to JSON and operations on the knowledge graph.
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List, Set

import networkx as nx

from .schema import (
    Node, Edge, NodeType, EdgeType,
    create_node_id, SPORT_ATTRIBUTES,
    create_sport_node, create_level_node, create_wave_side_node, create_court_node
)

logger = logging.getLogger(__name__)

DEFAULT_GRAPH_FILE = Path(__file__).parent.parent.parent / "data" / "graph.json"


class GraphStore:
    """
    NetworkX-based graph storage with JSON persistence.

    Provides:
    - In-memory graph operations using NetworkX
    - JSON serialization/deserialization
    - Node and edge CRUD operations
    - Graph initialization with sport attributes
    """

    def __init__(self, file_path: Optional[Path] = None):
        """
        Initialize graph store.

        Args:
            file_path: Path to JSON file for persistence
        """
        self.file_path = file_path or DEFAULT_GRAPH_FILE
        self.graph = nx.DiGraph()  # Directed graph
        self._ensure_file()
        self._load()

    def _ensure_file(self):
        """Ensure storage directory exists."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self):
        """Load graph from JSON file."""
        if not self.file_path.exists():
            logger.info("No existing graph file, initializing empty graph")
            self._initialize_base_nodes()
            self._save()
            return

        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)

            # Reconstruct graph from JSON
            for node_data in data.get("nodes", []):
                node = Node.from_dict(node_data)
                self.graph.add_node(node.id, **node.to_dict())

            for edge_data in data.get("edges", []):
                edge = Edge.from_dict(edge_data)
                self.graph.add_edge(
                    edge.source,
                    edge.target,
                    **edge.to_dict()
                )

            logger.info(
                f"Loaded graph: {self.graph.number_of_nodes()} nodes, "
                f"{self.graph.number_of_edges()} edges"
            )

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to load graph: {e}, initializing empty")
            self.graph = nx.DiGraph()
            self._initialize_base_nodes()

    def _save(self):
        """Save graph to JSON file."""
        nodes = []
        for node_id, attrs in self.graph.nodes(data=True):
            nodes.append(attrs)

        edges = []
        for source, target, attrs in self.graph.edges(data=True):
            edges.append(attrs)

        data = {
            "nodes": nodes,
            "edges": edges,
            "metadata": {
                "version": "1.0",
                "updated_at": datetime.utcnow().isoformat()
            }
        }

        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.debug(f"Saved graph: {len(nodes)} nodes, {len(edges)} edges")

    def _initialize_base_nodes(self):
        """Initialize graph with base sport attribute nodes."""
        logger.info("Initializing base sport attribute nodes")

        for sport, attributes in SPORT_ATTRIBUTES.items():
            # Create sport node
            sport_node = create_sport_node(sport)
            self.add_node(sport_node)

            # Create attribute nodes
            for attr_type, values in attributes.items():
                for value in values:
                    if attr_type == "level":
                        node = create_level_node(value, sport)
                    elif attr_type == "wave_side":
                        node = create_wave_side_node(value, sport)
                    elif attr_type == "court":
                        node = create_court_node(value, sport)
                    else:
                        continue
                    self.add_node(node)

    def save(self):
        """Explicitly save the graph to disk."""
        self._save()

    # === Node Operations ===

    def add_node(self, node: Node) -> bool:
        """
        Add a node to the graph.

        Args:
            node: Node to add

        Returns:
            True if added, False if already exists
        """
        if self.graph.has_node(node.id):
            return False

        self.graph.add_node(node.id, **node.to_dict())
        return True

    def update_node(self, node: Node) -> bool:
        """
        Update a node's properties.

        Args:
            node: Node with updated properties

        Returns:
            True if updated, False if not found
        """
        if not self.graph.has_node(node.id):
            return False

        self.graph.nodes[node.id].update(node.to_dict())
        return True

    def get_node(self, node_id: str) -> Optional[Node]:
        """
        Get a node by ID.

        Args:
            node_id: Node identifier

        Returns:
            Node if found, None otherwise
        """
        if not self.graph.has_node(node_id):
            return None

        attrs = self.graph.nodes[node_id]
        return Node.from_dict(attrs)

    def delete_node(self, node_id: str) -> bool:
        """
        Delete a node and all its edges.

        Args:
            node_id: Node identifier

        Returns:
            True if deleted, False if not found
        """
        if not self.graph.has_node(node_id):
            return False

        self.graph.remove_node(node_id)
        return True

    def has_node(self, node_id: str) -> bool:
        """Check if a node exists."""
        return self.graph.has_node(node_id)

    def get_nodes_by_type(self, node_type: NodeType) -> List[Node]:
        """
        Get all nodes of a specific type.

        Args:
            node_type: Type of nodes to find

        Returns:
            List of matching nodes
        """
        nodes = []
        for node_id, attrs in self.graph.nodes(data=True):
            if attrs.get("type") == node_type.value:
                nodes.append(Node.from_dict(attrs))
        return nodes

    # === Edge Operations ===

    def add_edge(self, edge: Edge) -> bool:
        """
        Add an edge to the graph.

        Args:
            edge: Edge to add

        Returns:
            True if added, False if already exists
        """
        if self.graph.has_edge(edge.source, edge.target):
            return False

        self.graph.add_edge(edge.source, edge.target, **edge.to_dict())
        return True

    def update_edge(self, edge: Edge) -> bool:
        """
        Update an edge's properties.

        Args:
            edge: Edge with updated properties

        Returns:
            True if updated, False if not found
        """
        if not self.graph.has_edge(edge.source, edge.target):
            return False

        self.graph.edges[edge.source, edge.target].update(edge.to_dict())
        return True

    def get_edge(self, source: str, target: str) -> Optional[Edge]:
        """
        Get an edge by source and target.

        Args:
            source: Source node ID
            target: Target node ID

        Returns:
            Edge if found, None otherwise
        """
        if not self.graph.has_edge(source, target):
            return None

        attrs = self.graph.edges[source, target]
        return Edge.from_dict(attrs)

    def delete_edge(self, source: str, target: str) -> bool:
        """
        Delete an edge.

        Args:
            source: Source node ID
            target: Target node ID

        Returns:
            True if deleted, False if not found
        """
        if not self.graph.has_edge(source, target):
            return False

        self.graph.remove_edge(source, target)
        return True

    def has_edge(self, source: str, target: str) -> bool:
        """Check if an edge exists."""
        return self.graph.has_edge(source, target)

    def get_edges_by_type(self, edge_type: EdgeType) -> List[Edge]:
        """
        Get all edges of a specific type.

        Args:
            edge_type: Type of edges to find

        Returns:
            List of matching edges
        """
        edges = []
        for source, target, attrs in self.graph.edges(data=True):
            if attrs.get("type") == edge_type.value:
                edges.append(Edge.from_dict(attrs))
        return edges

    # === Traversal Operations ===

    def get_neighbors(
        self,
        node_id: str,
        edge_type: Optional[EdgeType] = None,
        direction: str = "out"
    ) -> List[Node]:
        """
        Get neighboring nodes.

        Args:
            node_id: Starting node ID
            edge_type: Optional filter by edge type
            direction: "out" for outgoing, "in" for incoming, "both" for both

        Returns:
            List of neighboring nodes
        """
        if not self.graph.has_node(node_id):
            return []

        neighbors = set()

        if direction in ("out", "both"):
            for _, target, attrs in self.graph.out_edges(node_id, data=True):
                if edge_type is None or attrs.get("type") == edge_type.value:
                    neighbors.add(target)

        if direction in ("in", "both"):
            for source, _, attrs in self.graph.in_edges(node_id, data=True):
                if edge_type is None or attrs.get("type") == edge_type.value:
                    neighbors.add(source)

        return [self.get_node(n) for n in neighbors if self.has_node(n)]

    def get_path(self, source: str, target: str) -> Optional[List[str]]:
        """
        Find shortest path between two nodes.

        Args:
            source: Source node ID
            target: Target node ID

        Returns:
            List of node IDs in path, or None if no path exists
        """
        try:
            return nx.shortest_path(self.graph, source, target)
        except nx.NetworkXNoPath:
            return None

    def get_subgraph(self, node_ids: List[str]) -> "GraphStore":
        """
        Get a subgraph containing only specified nodes.

        Args:
            node_ids: List of node IDs to include

        Returns:
            New GraphStore with subgraph
        """
        subgraph = self.graph.subgraph(node_ids).copy()
        new_store = GraphStore.__new__(GraphStore)
        new_store.graph = subgraph
        new_store.file_path = None
        return new_store

    # === Statistics ===

    def stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        node_counts = {}
        for _, attrs in self.graph.nodes(data=True):
            node_type = attrs.get("type", "Unknown")
            node_counts[node_type] = node_counts.get(node_type, 0) + 1

        edge_counts = {}
        for _, _, attrs in self.graph.edges(data=True):
            edge_type = attrs.get("type", "Unknown")
            edge_counts[edge_type] = edge_counts.get(edge_type, 0) + 1

        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "nodes_by_type": node_counts,
            "edges_by_type": edge_counts
        }
