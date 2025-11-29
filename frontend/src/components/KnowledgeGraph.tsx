import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Network, ZoomIn, ZoomOut, Maximize2, ExternalLink, Filter, Link2, Eye, EyeOff } from 'lucide-react'
import type { GraphVisualization } from '../types'

type NodeType = 'article' | 'vulnerability' | 'threat_actor' | 'category' | 'entity' | 'product' | 'technique'

const NODE_TYPE_CONFIG: Record<NodeType, { color: string; label: string }> = {
  article: { color: '#0ca5eb', label: 'Article' },
  vulnerability: { color: '#ef4444', label: 'Vulnerability' },
  threat_actor: { color: '#f97316', label: 'Threat Actor' },
  category: { color: '#22c55e', label: 'Category' },
  entity: { color: '#8b5cf6', label: 'Entity' },
  product: { color: '#06b6d4', label: 'Product' },
  technique: { color: '#ec4899', label: 'Technique' },
}

interface SelectedNodeInfo {
  id: string
  type: string
  label: string
  properties?: Record<string, string>
  connectionCount?: number
  connectedTypes?: string[]
}

interface SelectedEdgeInfo {
  id: string
  relationship: string
  sourceLabel: string
  targetLabel: string
  weight: number
}

interface KnowledgeGraphProps {
  graph?: GraphVisualization
  onNodeClick?: (nodeId: string, nodeType: string) => void
  onFilterByEntity?: (entityType: string, entityLabel: string) => void
}

export default function KnowledgeGraph({ graph, onNodeClick, onFilterByEntity }: KnowledgeGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const networkRef = useRef<any>(null)
  const nodesDataSetRef = useRef<any>(null)
  const edgesDataSetRef = useRef<any>(null)
  const originalNodesRef = useRef<any[]>([])
  const originalEdgesRef = useRef<any[]>([])
  const navigate = useNavigate()
  const [selectedNode, setSelectedNode] = useState<SelectedNodeInfo | null>(null)
  const [selectedEdge, setSelectedEdge] = useState<SelectedEdgeInfo | null>(null)
  const [isLoaded, setIsLoaded] = useState(false)
  const [hoveredNode, setHoveredNode] = useState<string | null>(null)
  const [visibleTypes, setVisibleTypes] = useState<Set<NodeType>>(new Set(Object.keys(NODE_TYPE_CONFIG) as NodeType[]))

  const toggleNodeType = useCallback((type: NodeType) => {
    setVisibleTypes(prev => {
      const next = new Set(prev)
      if (next.has(type)) {
        next.delete(type)
      } else {
        next.add(type)
      }
      return next
    })
  }, [])

  useEffect(() => {
    if (!nodesDataSetRef.current || !edgesDataSetRef.current || originalNodesRef.current.length === 0) return

    const visibleNodeIds = new Set<string>()
    const filteredNodes = originalNodesRef.current.filter(node => {
      const isVisible = visibleTypes.has(node.nodeType as NodeType)
      if (isVisible) visibleNodeIds.add(node.id)
      return isVisible
    })

    const filteredEdges = originalEdgesRef.current.filter(edge =>
      visibleNodeIds.has(edge.from) && visibleNodeIds.has(edge.to)
    )

    nodesDataSetRef.current.clear()
    edgesDataSetRef.current.clear()
    nodesDataSetRef.current.add(filteredNodes)
    edgesDataSetRef.current.add(filteredEdges)

    if (networkRef.current) {
      networkRef.current.fit({ animation: { duration: 300, easingFunction: 'easeInOutQuad' } })
    }
  }, [visibleTypes])

  useEffect(() => {
    if (!graph || !containerRef.current) return

    const loadVisNetwork = async () => {
      if (!containerRef.current) return
      const container = containerRef.current
      const { Network, DataSet } = await import('vis-network/standalone')

      const nodeColors: Record<string, { background: string; border: string; highlight: { background: string; border: string } }> = {
        article: { background: '#0ca5eb', border: '#0086c9', highlight: { background: '#3dbcff', border: '#0ca5eb' } },
        vulnerability: { background: '#ef4444', border: '#dc2626', highlight: { background: '#f87171', border: '#ef4444' } },
        threat_actor: { background: '#f97316', border: '#ea580c', highlight: { background: '#fb923c', border: '#f97316' } },
        category: { background: '#22c55e', border: '#16a34a', highlight: { background: '#4ade80', border: '#22c55e' } },
        entity: { background: '#8b5cf6', border: '#7c3aed', highlight: { background: '#a78bfa', border: '#8b5cf6' } },
        product: { background: '#06b6d4', border: '#0891b2', highlight: { background: '#22d3ee', border: '#06b6d4' } },
        technique: { background: '#ec4899', border: '#db2777', highlight: { background: '#f472b6', border: '#ec4899' } },
      }

      const dimmedColor = { background: '#374151', border: '#4b5563', highlight: { background: '#4b5563', border: '#6b7280' } }

      const nodesArray = graph.nodes.map((node) => ({
        id: node.id,
        label: node.label,
        title: `${node.node_type}: ${node.label}`,
        color: nodeColors[node.node_type] || nodeColors.entity,
        originalColor: nodeColors[node.node_type] || nodeColors.entity,
        font: { color: '#ffffff', size: 12 },
        shape: node.node_type === 'article' ? 'box' : 'dot',
        size: node.node_type === 'article' ? 20 : 15,
        nodeType: node.node_type,
        properties: node.properties || {},
      }))
      originalNodesRef.current = nodesArray
      const nodes = new DataSet(nodesArray)
      nodesDataSetRef.current = nodes

      const edgesArray = graph.edges.map((edge, index) => ({
        id: `edge-${index}`,
        from: edge.source,
        to: edge.target,
        label: edge.relationship,
        font: { color: '#64748b', size: 10, align: 'middle' },
        color: { color: '#475569', highlight: '#0ca5eb', hover: '#94a3b8' },
        originalColor: { color: '#475569', highlight: '#0ca5eb', hover: '#94a3b8' },
        width: Math.max(1, edge.weight * 3),
        arrows: { to: { enabled: true, scaleFactor: 0.5 } },
        relationship: edge.relationship,
        weight: edge.weight,
      }))
      originalEdgesRef.current = edgesArray
      const edges = new DataSet(edgesArray)
      edgesDataSetRef.current = edges

      const getConnectedInfo = (nodeId: string) => {
        const connectedEdges = edges.get().filter((e: any) => e.from === nodeId || e.to === nodeId)
        const connectedNodeIds = new Set<string>()
        connectedEdges.forEach((e: any) => {
          if (e.from !== nodeId) connectedNodeIds.add(e.from)
          if (e.to !== nodeId) connectedNodeIds.add(e.to)
        })
        const connectedNodes = nodes.get().filter((n: any) => connectedNodeIds.has(n.id))
        const connectedTypes = [...new Set(connectedNodes.map((n: any) => n.nodeType))]
        return { count: connectedEdges.length, types: connectedTypes, edgeIds: connectedEdges.map((e: any) => e.id) }
      }

      const highlightConnected = (nodeId: string) => {
        const allNodes = nodes.get()
        const allEdges = edges.get()
        const connectedEdges = allEdges.filter((e: any) => e.from === nodeId || e.to === nodeId)
        const connectedNodeIds = new Set([nodeId, ...connectedEdges.map((e: any) => e.from === nodeId ? e.to : e.from)])
        const connectedEdgeIds = new Set(connectedEdges.map((e: any) => e.id))

        nodes.update(allNodes.map((n: any) => ({
          id: n.id,
          color: connectedNodeIds.has(n.id) ? n.originalColor : dimmedColor,
        })))
        edges.update(allEdges.map((e: any) => ({
          id: e.id,
          color: connectedEdgeIds.has(e.id) ? { color: '#0ca5eb', highlight: '#3dbcff' } : { color: '#1e293b', highlight: '#334155' },
          width: connectedEdgeIds.has(e.id) ? Math.max(2, e.width * 1.5) : 1,
        })))
      }

      const resetHighlight = () => {
        const allNodes = nodes.get()
        const allEdges = edges.get()
        nodes.update(allNodes.map((n: any) => ({ id: n.id, color: n.originalColor })))
        edges.update(allEdges.map((e: any) => ({
          id: e.id,
          color: e.originalColor,
          width: Math.max(1, (e.weight || 1) * 3),
        })))
      }

      const options = {
        nodes: {
          borderWidth: 2,
          shadow: true,
          font: {
            face: 'Inter',
          },
        },
        edges: {
          smooth: {
            enabled: true,
            type: 'continuous',
            roundness: 0.5,
          },
          selectionWidth: 2,
        },
        physics: {
          enabled: true,
          barnesHut: {
            gravitationalConstant: -3000,
            centralGravity: 0.3,
            springLength: 120,
            springConstant: 0.04,
          },
          stabilization: {
            enabled: true,
            iterations: 100,
          },
        },
        interaction: {
          hover: true,
          hoverConnectedEdges: true,
          selectConnectedEdges: true,
          tooltipDelay: 150,
          zoomView: true,
          dragView: true,
          navigationButtons: true,
          keyboard: {
            enabled: true,
            bindToWindow: false,
          },
        },
      }

      if (networkRef.current) {
        networkRef.current.destroy()
      }

      networkRef.current = new Network(
        container,
        { nodes, edges },
        options
      )

      networkRef.current.on('click', (params: any) => {
        setSelectedEdge(null)
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0]
          const nodeData = graph.nodes.find(n => n.id === nodeId)
          if (nodeData) {
            const connInfo = getConnectedInfo(nodeId)
            setSelectedNode({
              id: nodeId,
              type: nodeData.node_type || 'entity',
              label: nodeData.label,
              properties: nodeData.properties,
              connectionCount: connInfo.count,
              connectedTypes: connInfo.types,
            })
            onNodeClick?.(nodeId, nodeData.node_type || 'entity')
          }
        } else if (params.edges.length > 0) {
          const edgeId = params.edges[0]
          const edgeData = edges.get(edgeId) as any
          if (edgeData) {
            const sourceNode = nodes.get(edgeData.from) as any
            const targetNode = nodes.get(edgeData.to) as any
            setSelectedNode(null)
            setSelectedEdge({
              id: edgeId,
              relationship: edgeData.relationship || edgeData.label,
              sourceLabel: sourceNode?.label || edgeData.from,
              targetLabel: targetNode?.label || edgeData.to,
              weight: edgeData.weight || 1,
            })
          }
        } else {
          setSelectedNode(null)
          setSelectedEdge(null)
        }
      })

      networkRef.current.on('doubleClick', (params: any) => {
        if (params.nodes.length > 0) {
          const nodeId = params.nodes[0]
          const nodeData = graph.nodes.find(n => n.id === nodeId)
          if (nodeData && nodeData.node_type === 'article') {
            navigate(`/articles/${nodeId}`)
          }
        }
      })

      networkRef.current.on('hoverNode', (params: any) => {
        setHoveredNode(params.node)
        highlightConnected(params.node)
        if (containerRef.current) {
          containerRef.current.style.cursor = 'pointer'
        }
      })

      networkRef.current.on('blurNode', () => {
        setHoveredNode(null)
        resetHighlight()
        if (containerRef.current) {
          containerRef.current.style.cursor = 'default'
        }
      })

      networkRef.current.on('hoverEdge', () => {
        if (containerRef.current) {
          containerRef.current.style.cursor = 'pointer'
        }
      })

      networkRef.current.on('blurEdge', () => {
        if (containerRef.current && !hoveredNode) {
          containerRef.current.style.cursor = 'default'
        }
      })

      networkRef.current.on('stabilized', () => {
        setIsLoaded(true)
        networkRef.current.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } })
      })
    }

    setIsLoaded(false)
    loadVisNetwork()

    return () => {
      if (networkRef.current) {
        networkRef.current.destroy()
      }
    }
  }, [graph])

  const handleZoomIn = () => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale()
      networkRef.current.moveTo({ scale: scale * 1.3 })
    }
  }

  const handleZoomOut = () => {
    if (networkRef.current) {
      const scale = networkRef.current.getScale()
      networkRef.current.moveTo({ scale: scale * 0.7 })
    }
  }

  const handleFit = () => {
    if (networkRef.current) {
      networkRef.current.fit({ animation: true })
    }
  }

  if (!graph) {
    return (
      <div className="p-8 text-center h-full flex flex-col items-center justify-center">
        <div className="w-16 h-16 mx-auto mb-4 bg-muted rounded-full flex items-center justify-center">
          <Network className="w-8 h-8 text-muted-foreground" />
        </div>
        <h3 className="text-lg font-medium text-foreground mb-2">Knowledge Graph</h3>
        <p className="text-muted-foreground text-sm">
          Explore connections between threats, actors, and vulnerabilities
        </p>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      {/* Controls */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="text-sm text-muted-foreground">
            <span className="text-foreground font-medium">{graph.statistics?.node_count ?? graph.total_nodes ?? graph.nodes.length}</span> nodes
            <span className="mx-2">|</span>
            <span className="text-foreground font-medium">{graph.statistics?.edge_count ?? graph.total_edges ?? graph.edges.length}</span> connections
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleZoomIn}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4 text-muted-foreground" />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="w-4 h-4 text-muted-foreground" />
          </button>
          <button
            onClick={handleFit}
            className="p-2 hover:bg-muted rounded-lg transition-colors"
            title="Fit to View"
          >
            <Maximize2 className="w-4 h-4 text-muted-foreground" />
          </button>
        </div>
      </div>

      {/* Filter Legend */}
      <div className="px-4 py-2 flex flex-wrap gap-2 border-b border-border">
        {(Object.entries(NODE_TYPE_CONFIG) as [NodeType, { color: string; label: string }][]).map(([type, config]) => (
          <FilterButton
            key={type}
            color={config.color}
            label={config.label}
            active={visibleTypes.has(type)}
            onClick={() => toggleNodeType(type)}
          />
        ))}
      </div>

      <div
        ref={containerRef}
        className={`flex-1 graph-container min-h-[400px] transition-opacity duration-500 ${
          isLoaded ? 'opacity-100' : 'opacity-0'
        }`}
      />

      {/* Selected Node Info */}
      {selectedNode && (
        <div className="p-4 border-t border-border bg-card">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="text-foreground font-medium">{selectedNode.label}</span>
              <span className="px-2 py-0.5 text-xs rounded-full bg-muted text-foreground/80">
                {selectedNode.type.replace('_', ' ')}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {selectedNode.type === 'article' ? (
                <button
                  onClick={() => navigate(`/articles/${selectedNode.id}`)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                >
                  <ExternalLink className="w-4 h-4" />
                  View Article
                </button>
              ) : onFilterByEntity && (
                <button
                  onClick={() => onFilterByEntity(selectedNode.type, selectedNode.label)}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-muted text-foreground rounded-lg hover:bg-muted/80 transition-colors"
                >
                  <Filter className="w-4 h-4" />
                  Filter Articles
                </button>
              )}
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            {selectedNode.connectionCount !== undefined && (
              <span>{selectedNode.connectionCount} connection{selectedNode.connectionCount !== 1 ? 's' : ''}</span>
            )}
            {selectedNode.connectedTypes && selectedNode.connectedTypes.length > 0 && (
              <span>Connected to: {selectedNode.connectedTypes.map(t => t.replace('_', ' ')).join(', ')}</span>
            )}
          </div>
          {selectedNode.type === 'article' && (
            <p className="text-xs text-muted-foreground mt-2">Double-click to open article details</p>
          )}
        </div>
      )}

      {/* Selected Edge Info */}
      {selectedEdge && !selectedNode && (
        <div className="p-4 border-t border-border bg-card">
          <div className="flex items-center gap-2 mb-2">
            <Link2 className="w-4 h-4 text-primary" />
            <span className="text-foreground font-medium">{selectedEdge.relationship}</span>
            <span className="px-2 py-0.5 text-xs rounded-full bg-muted text-foreground/80">relationship</span>
          </div>
          <div className="text-xs text-muted-foreground">
            <span className="text-foreground/80">{selectedEdge.sourceLabel}</span>
            <span className="mx-2">→</span>
            <span className="text-foreground/80">{selectedEdge.targetLabel}</span>
            {selectedEdge.weight > 1 && (
              <span className="ml-3">Weight: {selectedEdge.weight.toFixed(1)}</span>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

interface FilterButtonProps {
  color: string
  label: string
  active: boolean
  onClick: () => void
}

function FilterButton({ color, label, active, onClick }: FilterButtonProps) {
  return (
    <button
      onClick={onClick}
      className={`
        flex items-center gap-1.5 px-2 py-1 rounded-md text-xs transition-all duration-200
        ${active
          ? 'bg-muted/50 text-foreground'
          : 'bg-card/30 text-muted-foreground opacity-50'
        }
        hover:bg-muted/70
      `}
    >
      <div
        className={`w-2.5 h-2.5 rounded-full transition-opacity ${active ? 'opacity-100' : 'opacity-30'}`}
        style={{ backgroundColor: color }}
      />
      <span>{label}</span>
      {active ? (
        <Eye className="w-3 h-3 ml-1" />
      ) : (
        <EyeOff className="w-3 h-3 ml-1" />
      )}
    </button>
  )
}
