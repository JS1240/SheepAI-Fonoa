"""Graph repository for Supabase database operations."""

import logging
from datetime import datetime
from typing import Any, Optional

from supabase import Client

from app.db.supabase_client import get_supabase_client
from app.models.graph import GraphEdge, GraphNode, NodeType, RelationshipType

logger = logging.getLogger(__name__)


class GraphRepository:
    """Repository for graph node and edge CRUD operations."""

    def __init__(self, client: Optional[Client] = None):
        """Initialize the repository with a Supabase client."""
        self._client = client

    @property
    def client(self) -> Client:
        """Get the Supabase client (lazy initialization)."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    async def create_node(self, node: GraphNode) -> GraphNode:
        """Create a new graph node in the database."""
        data = {
            "id": node.id,
            "node_type": node.node_type.value,
            "label": node.label,
            "properties": node.properties,
            "size": node.size,
        }

        try:
            result = self.client.table("graph_nodes").insert(data).execute()
            logger.debug("Created graph node: %s", node.id)
            return node
        except Exception as e:
            logger.error("Failed to create graph node %s: %s", node.id, str(e))
            raise

    async def upsert_node(self, node: GraphNode) -> GraphNode:
        """Create or update a graph node."""
        data = {
            "id": node.id,
            "node_type": node.node_type.value,
            "label": node.label,
            "properties": node.properties,
            "size": node.size,
        }

        try:
            result = (
                self.client.table("graph_nodes")
                .upsert(data, on_conflict="id")
                .execute()
            )
            logger.debug("Upserted graph node: %s", node.id)
            return node
        except Exception as e:
            logger.error("Failed to upsert graph node %s: %s", node.id, str(e))
            raise

    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a graph node by ID."""
        try:
            result = (
                self.client.table("graph_nodes")
                .select("*")
                .eq("id", node_id)
                .single()
                .execute()
            )

            if result.data:
                return self._row_to_node(result.data)
            return None
        except Exception as e:
            logger.debug("Graph node not found %s: %s", node_id, str(e))
            return None

    async def get_nodes_by_type(
        self,
        node_type: NodeType,
        limit: int = 100,
    ) -> list[GraphNode]:
        """Get all nodes of a specific type."""
        try:
            result = (
                self.client.table("graph_nodes")
                .select("*")
                .eq("node_type", node_type.value)
                .limit(limit)
                .execute()
            )

            return [self._row_to_node(row) for row in result.data]
        except Exception as e:
            logger.error("Failed to get nodes by type %s: %s", node_type.value, str(e))
            return []

    async def get_all_nodes(self, limit: int = 500) -> list[GraphNode]:
        """Get all graph nodes."""
        try:
            result = (
                self.client.table("graph_nodes").select("*").limit(limit).execute()
            )

            return [self._row_to_node(row) for row in result.data]
        except Exception as e:
            logger.error("Failed to get all nodes: %s", str(e))
            return []

    async def delete_node(self, node_id: str) -> bool:
        """Delete a node and its connected edges."""
        try:
            self.client.table("graph_edges").delete().or_(
                f"source_id.eq.{node_id},target_id.eq.{node_id}"
            ).execute()

            self.client.table("graph_nodes").delete().eq("id", node_id).execute()

            logger.debug("Deleted graph node: %s", node_id)
            return True
        except Exception as e:
            logger.error("Failed to delete graph node %s: %s", node_id, str(e))
            return False

    async def create_edge(self, edge: GraphEdge) -> GraphEdge:
        """Create a new graph edge in the database."""
        data = {
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "relationship": edge.relationship.value,
            "weight": edge.weight,
        }

        try:
            result = self.client.table("graph_edges").insert(data).execute()
            logger.debug(
                "Created graph edge: %s -> %s (%s)",
                edge.source_id,
                edge.target_id,
                edge.relationship.value,
            )
            return edge
        except Exception as e:
            if "duplicate" in str(e).lower():
                logger.debug("Edge already exists: %s -> %s", edge.source_id, edge.target_id)
                return edge
            logger.error("Failed to create graph edge: %s", str(e))
            raise

    async def upsert_edge(self, edge: GraphEdge) -> GraphEdge:
        """Create or update a graph edge."""
        data = {
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "relationship": edge.relationship.value,
            "weight": edge.weight,
        }

        try:
            result = (
                self.client.table("graph_edges")
                .upsert(data, on_conflict="source_id,target_id,relationship")
                .execute()
            )
            logger.debug(
                "Upserted graph edge: %s -> %s (%s)",
                edge.source_id,
                edge.target_id,
                edge.relationship.value,
            )
            return edge
        except Exception as e:
            logger.error("Failed to upsert graph edge: %s", str(e))
            raise

    async def get_edges_from_node(self, source_id: str) -> list[GraphEdge]:
        """Get all edges originating from a node."""
        try:
            result = (
                self.client.table("graph_edges")
                .select("*")
                .eq("source_id", source_id)
                .execute()
            )

            return [self._row_to_edge(row) for row in result.data]
        except Exception as e:
            logger.error("Failed to get edges from node %s: %s", source_id, str(e))
            return []

    async def get_edges_to_node(self, target_id: str) -> list[GraphEdge]:
        """Get all edges pointing to a node."""
        try:
            result = (
                self.client.table("graph_edges")
                .select("*")
                .eq("target_id", target_id)
                .execute()
            )

            return [self._row_to_edge(row) for row in result.data]
        except Exception as e:
            logger.error("Failed to get edges to node %s: %s", target_id, str(e))
            return []

    async def get_connected_nodes(
        self,
        node_id: str,
        depth: int = 1,
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Get nodes connected to a given node up to specified depth."""
        visited_nodes: set[str] = {node_id}
        all_nodes: list[GraphNode] = []
        all_edges: list[GraphEdge] = []
        current_layer: set[str] = {node_id}

        try:
            root_node = await self.get_node(node_id)
            if root_node:
                all_nodes.append(root_node)

            for _ in range(depth):
                next_layer: set[str] = set()

                for current_id in current_layer:
                    outgoing = await self.get_edges_from_node(current_id)
                    incoming = await self.get_edges_to_node(current_id)

                    for edge in outgoing + incoming:
                        all_edges.append(edge)

                        connected_id = (
                            edge.target_id
                            if edge.source_id == current_id
                            else edge.source_id
                        )

                        if connected_id not in visited_nodes:
                            visited_nodes.add(connected_id)
                            next_layer.add(connected_id)

                            connected_node = await self.get_node(connected_id)
                            if connected_node:
                                all_nodes.append(connected_node)

                current_layer = next_layer

            return all_nodes, all_edges
        except Exception as e:
            logger.error("Failed to get connected nodes for %s: %s", node_id, str(e))
            return all_nodes, all_edges

    async def get_all_edges(self, limit: int = 1000) -> list[GraphEdge]:
        """Get all graph edges."""
        try:
            result = (
                self.client.table("graph_edges").select("*").limit(limit).execute()
            )

            return [self._row_to_edge(row) for row in result.data]
        except Exception as e:
            logger.error("Failed to get all edges: %s", str(e))
            return []

    async def delete_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: RelationshipType,
    ) -> bool:
        """Delete a specific edge."""
        try:
            result = (
                self.client.table("graph_edges")
                .delete()
                .eq("source_id", source_id)
                .eq("target_id", target_id)
                .eq("relationship", relationship.value)
                .execute()
            )

            logger.debug(
                "Deleted graph edge: %s -> %s (%s)",
                source_id,
                target_id,
                relationship.value,
            )
            return True
        except Exception as e:
            logger.error("Failed to delete graph edge: %s", str(e))
            return False

    async def get_node_count(self) -> int:
        """Get total count of graph nodes."""
        try:
            result = (
                self.client.table("graph_nodes")
                .select("id", count="exact")
                .execute()
            )
            return result.count or 0
        except Exception as e:
            logger.error("Failed to get node count: %s", str(e))
            return 0

    async def get_edge_count(self) -> int:
        """Get total count of graph edges."""
        try:
            result = (
                self.client.table("graph_edges")
                .select("id", count="exact")
                .execute()
            )
            return result.count or 0
        except Exception as e:
            logger.error("Failed to get edge count: %s", str(e))
            return 0

    async def clear_all(self) -> bool:
        """Clear all graph data. Use with caution."""
        try:
            self.client.table("graph_edges").delete().neq("id", -1).execute()
            self.client.table("graph_nodes").delete().neq("id", "").execute()
            logger.info("Cleared all graph data")
            return True
        except Exception as e:
            logger.error("Failed to clear graph data: %s", str(e))
            return False

    def _row_to_node(self, row: dict) -> GraphNode:
        """Convert a database row to a GraphNode model."""
        return GraphNode(
            id=row["id"],
            node_type=NodeType(row["node_type"]),
            label=row["label"],
            properties=row.get("properties", {}),
            size=row.get("size", 1.0),
        )

    def _row_to_edge(self, row: dict) -> GraphEdge:
        """Convert a database row to a GraphEdge model."""
        return GraphEdge(
            source_id=row["source_id"],
            target_id=row["target_id"],
            relationship=RelationshipType(row["relationship"]),
            weight=row.get("weight", 1.0),
            timestamp=datetime.fromisoformat(
                row["created_at"].replace("Z", "+00:00")
            ),
        )
