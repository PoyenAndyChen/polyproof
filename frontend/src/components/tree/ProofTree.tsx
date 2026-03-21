import { useMemo, useCallback, useEffect } from 'react'
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
  type Node,
  type Edge,
} from '@xyflow/react'
import dagre from 'dagre'
import '@xyflow/react/dist/style.css'
import { useNavigate } from 'react-router-dom'
import { Maximize2, Zap, Filter } from 'lucide-react'
import ConjectureNodeComponent, { type ConjectureNodeData } from './ConjectureNode'
import MobileTreeList from './MobileTreeList'
import { cn } from '../../lib/utils'
import { ROUTES } from '../../lib/constants'
import { useUIStore } from '../../store/ui'
import type { TreeNode, ConjectureStatus } from '../../types'

const NODE_WIDTH = 240
const NODE_HEIGHT = 80

const nodeTypes = {
  conjecture: ConjectureNodeComponent,
}

function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
): { nodes: Node[]; edges: Edge[] } {
  const g = new dagre.graphlib.Graph()
  g.setGraph({ rankdir: 'TB', ranksep: 60, nodesep: 40 })
  g.setDefaultEdgeLabel(() => ({}))

  nodes.forEach((node) => {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT })
  })

  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target)
  })

  dagre.layout(g)

  const layoutedNodes = nodes.map((node) => {
    const pos = g.node(node.id)
    return {
      ...node,
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - NODE_HEIGHT / 2,
      },
    }
  })

  return { nodes: layoutedNodes, edges }
}

interface ProofTreeInnerProps {
  tree: TreeNode[]
  highlightCritical: boolean
  statusFilter: Set<ConjectureStatus>
  collapsed: Set<string>
  onToggleCollapse: (id: string) => void
  onSetHighlightCritical: (on: boolean) => void
  onToggleStatusFilter: (status: ConjectureStatus) => void
}

function ProofTreeInner({
  tree,
  highlightCritical,
  statusFilter,
  collapsed,
  onToggleCollapse,
  onSetHighlightCritical,
  onToggleStatusFilter,
}: ProofTreeInnerProps) {
  const navigate = useNavigate()
  const { fitView } = useReactFlow()

  const handleNodeClick = useCallback(
    (id: string) => {
      navigate(ROUTES.CONJECTURE(id))
    },
    [navigate],
  )

  // Filter out children of collapsed nodes
  const visibleNodes = useMemo(() => {
    const collapsedAncestors = new Set<string>()

    // Find all nodes that are descendants of collapsed nodes
    function markHidden(nodeId: string) {
      const children = tree.filter((n) => n.parent_id === nodeId)
      for (const child of children) {
        collapsedAncestors.add(child.id)
        markHidden(child.id)
      }
    }

    for (const id of collapsed) {
      markHidden(id)
    }

    return tree.filter((n) => !collapsedAncestors.has(n.id))
  }, [tree, collapsed])

  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    const rfNodes: Node[] = visibleNodes.map((node) => {
      const isDimmed =
        (statusFilter.size > 0 && !statusFilter.has(node.status)) ||
        (highlightCritical && node.priority !== 'critical' && node.status !== 'proved')

      return {
        id: node.id,
        type: 'conjecture',
        position: { x: 0, y: 0 },
        data: {
          id: node.id,
          lean_statement: node.lean_statement,
          status: node.status,
          priority: node.priority,
          comment_count: node.comment_count,
          child_count: node.child_count,
          proved_child_count: node.proved_child_count,
          collapsed: collapsed.has(node.id),
          dimmed: isDimmed,
          onToggleCollapse,
          onNodeClick: handleNodeClick,
        } satisfies ConjectureNodeData,
      }
    })

    const visibleIds = new Set(visibleNodes.map((n) => n.id))
    const rfEdges: Edge[] = visibleNodes
      .filter((n) => n.parent_id && visibleIds.has(n.parent_id))
      .map((n) => ({
        id: `${n.parent_id}-${n.id}`,
        source: n.parent_id!,
        target: n.id,
        type: 'smoothstep',
        style: { stroke: '#94a3b8', strokeWidth: 1.5 },
      }))

    return getLayoutedElements(rfNodes, rfEdges)
  }, [visibleNodes, collapsed, highlightCritical, statusFilter, onToggleCollapse, handleNodeClick])

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  // Update nodes/edges when data changes
  useEffect(() => {
    setNodes(initialNodes)
    setEdges(initialEdges)
  }, [initialNodes, initialEdges, setNodes, setEdges])

  const statusOptions: ConjectureStatus[] = ['open', 'decomposed', 'proved', 'disproved', 'invalid']

  return (
    <div>
      {/* Toolbar */}
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <button
          onClick={() => fitView({ padding: 0.1 })}
          className="inline-flex items-center gap-1 rounded-md border border-gray-200 bg-white px-2.5 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
        >
          <Maximize2 className="h-3 w-3" />
          Fit
        </button>
        <button
          onClick={() => onSetHighlightCritical(!highlightCritical)}
          className={cn(
            'inline-flex items-center gap-1 rounded-md border px-2.5 py-1.5 text-xs font-medium',
            highlightCritical
              ? 'border-yellow-300 bg-yellow-50 text-yellow-800'
              : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50',
          )}
        >
          <Zap className="h-3 w-3" />
          Critical Path
        </button>
        <div className="relative inline-flex items-center gap-1">
          <Filter className="h-3 w-3 text-gray-500" />
          {statusOptions.map((s) => (
            <button
              key={s}
              onClick={() => onToggleStatusFilter(s)}
              className={cn(
                'rounded-md px-2 py-1 text-xs capitalize',
                statusFilter.has(s)
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
              )}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Tree */}
      <div className="h-[500px] rounded-lg border border-gray-200 bg-white">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.1 }}
          minZoom={0.1}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        />
      </div>
    </div>
  )
}

interface ProofTreeProps {
  tree: TreeNode[]
}

export default function ProofTree({ tree }: ProofTreeProps) {
  const {
    highlightCritical,
    statusFilter,
    treeCollapsed,
    toggleCollapse,
    setHighlightCritical,
    toggleStatusFilter,
  } = useUIStore()

  return (
    <>
      {/* Desktop: react-flow tree */}
      <div className="hidden md:block">
        <ReactFlowProvider>
          <ProofTreeInner
            tree={tree}
            highlightCritical={highlightCritical}
            statusFilter={statusFilter}
            collapsed={treeCollapsed}
            onToggleCollapse={toggleCollapse}
            onSetHighlightCritical={setHighlightCritical}
            onToggleStatusFilter={toggleStatusFilter}
          />
        </ReactFlowProvider>
      </div>

      {/* Mobile: indented list */}
      <div className="md:hidden">
        <MobileTreeList
          nodes={tree}
          collapsed={treeCollapsed}
          onToggleCollapse={toggleCollapse}
        />
      </div>
    </>
  )
}
