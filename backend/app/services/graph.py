"""Knowledge graph service for article connections."""

import logging
from typing import Any, Optional

import networkx as nx

from app.db.repositories import GraphRepository
from app.models.article import Article
from app.models.graph import (
    GraphEdge,
    GraphNode,
    GraphVisualization,
    NodeType,
    RelationshipType,
)

logger = logging.getLogger(__name__)


class GraphService:
    """Service for managing the knowledge graph."""

    def __init__(self, graph_repo: Optional[GraphRepository] = None) -> None:
        self.graph = nx.DiGraph()
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._graph_repo = graph_repo or GraphRepository()

    async def add_article_node(self, article: Article) -> GraphNode:
        """Add an article as a node in the graph."""
        node = GraphNode(
            id=article.id,
            node_type=NodeType.ARTICLE,
            label=article.title[:50] + "..." if len(article.title) > 50 else article.title,
            properties={
                "url": article.url,
                "published_at": article.published_at.isoformat(),
                "categories": article.categories,
            },
            size=1.5,
        )

        self._nodes[node.id] = node
        self.graph.add_node(
            node.id,
            node_type=node.node_type.value,
            label=node.label,
            **node.properties,
        )

        # Persist to database
        try:
            await self._graph_repo.upsert_node(node)
        except Exception as e:
            logger.warning("Failed to persist article node to DB: %s", e)

        # Add entity nodes
        for vuln in article.vulnerabilities:
            await self._add_entity_node(
                vuln,
                NodeType.VULNERABILITY,
                article.id,
                RelationshipType.MENTIONS,
            )

        for actor in article.threat_actors:
            await self._add_entity_node(
                actor,
                NodeType.THREAT_ACTOR,
                article.id,
                RelationshipType.MENTIONS,
            )

        for category in article.categories:
            await self._add_entity_node(
                category,
                NodeType.ENTITY,
                article.id,
                RelationshipType.MENTIONS,
            )

        return node

    async def _add_entity_node(
        self,
        entity_name: str,
        node_type: NodeType,
        source_article_id: str,
        relationship: RelationshipType,
    ) -> None:
        """Add an entity node and connect to source article."""
        entity_id = f"{node_type.value}-{entity_name.lower().replace(' ', '-')}"

        if entity_id not in self._nodes:
            node = GraphNode(
                id=entity_id,
                node_type=node_type,
                label=entity_name,
                size=1.0,
            )
            self._nodes[entity_id] = node
            self.graph.add_node(
                entity_id,
                node_type=node_type.value,
                label=entity_name,
            )

            # Persist to database
            try:
                await self._graph_repo.upsert_node(node)
            except Exception as e:
                logger.warning("Failed to persist entity node to DB: %s", e)

        # Add edge from article to entity
        await self.add_edge(source_article_id, entity_id, relationship)

    async def add_edge(
        self,
        source_id: str,
        target_id: str,
        relationship: RelationshipType,
        weight: float = 1.0,
    ) -> Optional[GraphEdge]:
        """Add an edge between two nodes."""
        if source_id not in self._nodes or target_id not in self._nodes:
            return None

        edge = GraphEdge(
            source_id=source_id,
            target_id=target_id,
            relationship=relationship,
            weight=weight,
        )

        self._edges.append(edge)
        self.graph.add_edge(
            source_id,
            target_id,
            relationship=relationship.value,
            weight=weight,
        )

        # Persist to database
        try:
            await self._graph_repo.upsert_edge(edge)
        except Exception as e:
            logger.warning("Failed to persist edge to DB: %s", e)

        return edge

    async def connect_similar_articles(
        self,
        article: Article,
        similar_articles: list[tuple[Article, float]],
    ) -> None:
        """Create edges between similar articles."""
        for similar_article, similarity in similar_articles:
            await self.add_edge(
                article.id,
                similar_article.id,
                RelationshipType.RELATED_TO,
                weight=similarity,
            )
            article.related_article_ids.append(similar_article.id)

    def get_subgraph(
        self,
        center_node_id: str,
        depth: int = 2,
    ) -> GraphVisualization:
        """Get a subgraph centered on a specific node."""
        if center_node_id not in self.graph:
            return GraphVisualization(focus_node=center_node_id)

        # Get all nodes within depth hops
        nodes_in_subgraph = {center_node_id}

        for _ in range(depth):
            new_nodes = set()
            for node in nodes_in_subgraph:
                # Add predecessors and successors
                new_nodes.update(self.graph.predecessors(node))
                new_nodes.update(self.graph.successors(node))
            nodes_in_subgraph.update(new_nodes)

        # Build visualization data
        vis_nodes = []
        for node_id in nodes_in_subgraph:
            if node_id in self._nodes:
                node = self._nodes[node_id]
                vis_nodes.append({
                    "id": node.id,
                    "label": node.label,
                    "node_type": node.node_type.value,
                    "size": node.size * (2 if node_id == center_node_id else 1),
                    "properties": node.properties or {},
                })

        vis_edges = []
        for edge in self._edges:
            if edge.source_id in nodes_in_subgraph and edge.target_id in nodes_in_subgraph:
                vis_edges.append({
                    "source": edge.source_id,
                    "target": edge.target_id,
                    "relationship": edge.relationship.value,
                    "weight": edge.weight,
                })

        return GraphVisualization(
            nodes=vis_nodes,
            edges=vis_edges,
            focus_node=center_node_id,
            depth=depth,
            total_nodes=len(vis_nodes),
            total_edges=len(vis_edges),
        )

    def find_connections_between(
        self,
        article_id1: str,
        article_id2: str,
    ) -> list[list[str]]:
        """Find paths connecting two articles."""
        if article_id1 not in self.graph or article_id2 not in self.graph:
            return []

        try:
            # Find up to 3 shortest paths
            paths = []
            for path in nx.all_shortest_paths(
                self.graph.to_undirected(),
                article_id1,
                article_id2,
            ):
                paths.append(path)
                if len(paths) >= 3:
                    break
            return paths
        except nx.NetworkXNoPath:
            return []

    def get_article_connections(
        self,
        article_id: str,
    ) -> dict[str, Any]:
        """Get all connections for an article."""
        if article_id not in self.graph:
            return {"connections": [], "entities": []}

        connections = []
        entities = []

        for successor in self.graph.successors(article_id):
            node = self._nodes.get(successor)
            if not node:
                continue

            edge_data = self.graph.get_edge_data(article_id, successor)
            relationship = edge_data.get("relationship", "related_to")

            if node.node_type == NodeType.ARTICLE:
                connections.append({
                    "article_id": successor,
                    "label": node.label,
                    "relationship": relationship,
                })
            else:
                entities.append({
                    "entity_id": successor,
                    "type": node.node_type.value,
                    "label": node.label,
                })

        return {
            "connections": connections,
            "entities": entities,
        }

    def get_statistics(self) -> dict[str, int]:
        """Get graph statistics."""
        return {
            "total_nodes": self.graph.number_of_nodes(),
            "total_edges": self.graph.number_of_edges(),
            "article_nodes": len(
                [n for n in self._nodes.values() if n.node_type == NodeType.ARTICLE]
            ),
            "entity_nodes": len(
                [n for n in self._nodes.values() if n.node_type != NodeType.ARTICLE]
            ),
        }

    def get_prediction_context(self, article_id: str) -> dict[str, Any]:
        """Extract graph context for prediction enhancement.

        Returns intelligence about related threats, actors, and CVEs
        that can inform prediction confidence and reasoning.
        """
        if article_id not in self.graph:
            return {"has_graph_data": False}

        context = {
            "has_graph_data": True,
            "connection_count": 0,
            "connection_density": 0.0,
            "related_cves": [],
            "related_threat_actors": [],
            "related_articles": [],
            "threat_actor_history": [],
            "cve_severity_context": [],
        }

        # Get all connected nodes
        connections = self.get_article_connections(article_id)

        # Process entities
        for entity in connections.get("entities", []):
            entity_type = entity.get("type", "")
            entity_label = entity.get("label", "")
            entity_id = entity.get("entity_id", "")

            if entity_type == "vulnerability":
                context["related_cves"].append(entity_label)
                # Find other articles mentioning this CVE
                cve_articles = self._find_articles_mentioning(entity_id)
                context["cve_severity_context"].append({
                    "cve": entity_label,
                    "article_count": len(cve_articles),
                    "is_trending": len(cve_articles) > 2,
                })
            elif entity_type == "threat_actor":
                context["related_threat_actors"].append(entity_label)
                # Find actor's attack history
                actor_articles = self._find_articles_mentioning(entity_id)
                context["threat_actor_history"].append({
                    "actor": entity_label,
                    "article_count": len(actor_articles),
                    "active_campaigns": len(actor_articles) > 1,
                })

        # Get related articles
        for conn in connections.get("connections", []):
            context["related_articles"].append({
                "id": conn.get("article_id", ""),
                "title": conn.get("label", ""),
                "relationship": conn.get("relationship", "related_to"),
            })

        # Compute connection density score (normalize to 0-1)
        total_connections = len(connections.get("entities", [])) + len(connections.get("connections", []))
        context["connection_count"] = total_connections
        context["connection_density"] = min(1.0, total_connections / 10.0)

        return context

    def _find_articles_mentioning(self, entity_id: str) -> list[str]:
        """Find all articles connected to an entity."""
        if entity_id not in self.graph:
            return []

        articles = []
        # Check predecessors (articles that mention this entity)
        for predecessor in self.graph.predecessors(entity_id):
            node = self._nodes.get(predecessor)
            if node and node.node_type == NodeType.ARTICLE:
                articles.append(predecessor)
        return articles

    async def load_from_database(self) -> int:
        """Load graph data from database into memory."""
        try:
            # Load all nodes
            nodes = await self._graph_repo.get_all_nodes()
            for node in nodes:
                self._nodes[node.id] = node
                self.graph.add_node(
                    node.id,
                    node_type=node.node_type.value,
                    label=node.label,
                    **node.properties,
                )

            # Load all edges
            edges = await self._graph_repo.get_all_edges()
            for edge in edges:
                self._edges.append(edge)
                self.graph.add_edge(
                    edge.source_id,
                    edge.target_id,
                    relationship=edge.relationship.value,
                    weight=edge.weight,
                )

            logger.info(
                "Loaded graph from database: %d nodes, %d edges",
                len(nodes),
                len(edges),
            )
            return len(nodes)
        except Exception as e:
            logger.error("Failed to load graph from database: %s", e)
            return 0

    async def clear_and_rebuild(self) -> None:
        """Clear in-memory graph and reload from database."""
        self.graph.clear()
        self._nodes.clear()
        self._edges.clear()
        await self.load_from_database()


# Singleton instance
graph_service = GraphService()
