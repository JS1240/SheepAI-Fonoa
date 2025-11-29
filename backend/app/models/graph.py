"""Knowledge graph data models."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""

    ARTICLE = "article"
    ENTITY = "entity"
    VULNERABILITY = "vulnerability"
    THREAT_ACTOR = "threat_actor"
    PRODUCT = "product"
    TECHNIQUE = "technique"


class RelationshipType(str, Enum):
    """Types of relationships between nodes."""

    MENTIONS = "mentions"
    EXPLOITS = "exploits"
    RELATED_TO = "related_to"
    EVOLVES_FROM = "evolves_from"
    TARGETS = "targets"
    USES = "uses"
    ATTRIBUTED_TO = "attributed_to"


class GraphNode(BaseModel):
    """A node in the knowledge graph."""

    id: str = Field(..., description="Unique node identifier")
    node_type: NodeType = Field(..., description="Type of the node")
    label: str = Field(..., description="Display label for the node")
    properties: dict[str, Any] = Field(default_factory=dict)

    # Visualization hints
    size: float = Field(default=1.0, description="Relative size for visualization")
    color: Optional[str] = Field(default=None, description="Node color override")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "vuln-cve-2025-1234",
                "node_type": "vulnerability",
                "label": "CVE-2025-1234",
                "properties": {"cvss": 9.8, "severity": "critical"},
                "size": 2.0,
            }
        }


class GraphEdge(BaseModel):
    """An edge connecting two nodes in the knowledge graph."""

    source_id: str = Field(..., description="Source node ID")
    target_id: str = Field(..., description="Target node ID")
    relationship: RelationshipType = Field(..., description="Type of relationship")
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    properties: dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "source_id": "thn-2025-001",
                "target_id": "vuln-cve-2025-1234",
                "relationship": "mentions",
                "weight": 0.95,
            }
        }


class GraphVisualization(BaseModel):
    """Data structure for graph visualization in the frontend."""

    nodes: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of nodes with id, label, type, size, color",
    )
    edges: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of edges with source, target, label, weight",
    )
    focus_node: Optional[str] = Field(
        default=None,
        description="ID of the central/focus node",
    )
    depth: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Number of hops from focus node",
    )
    total_nodes: int = Field(default=0)
    total_edges: int = Field(default=0)

    def to_vis_js_format(self) -> dict[str, Any]:
        """Convert to vis.js compatible format."""
        return {
            "nodes": [
                {
                    "id": n.get("id"),
                    "label": n.get("label"),
                    "group": n.get("type"),
                    "value": n.get("size", 1),
                    "title": n.get("tooltip", n.get("label")),
                }
                for n in self.nodes
            ],
            "edges": [
                {
                    "from": e.get("source"),
                    "to": e.get("target"),
                    "label": e.get("label", ""),
                    "value": e.get("weight", 1),
                }
                for e in self.edges
            ],
        }
