import { Link } from 'react-router-dom'
import { ChevronRight, ChevronDown, MessageSquare, Check, X } from 'lucide-react'
import { cn, truncate } from '../../lib/utils'
import { ROUTES } from '../../lib/constants'
import type { TreeNode, ConjectureStatus } from '../../types'

const statusDot: Record<ConjectureStatus, string> = {
  open: 'bg-gray-400',
  decomposed: 'bg-blue-500',
  proved: 'bg-green-500',
  disproved: 'bg-red-500',
  invalid: 'bg-gray-400',
}

interface MobileTreeListProps {
  nodes: TreeNode[]
  collapsed: Set<string>
  onToggleCollapse: (id: string) => void
}

export default function MobileTreeList({ nodes, collapsed, onToggleCollapse }: MobileTreeListProps) {
  // Build a map of parent -> children
  const childrenMap = new Map<string | null, TreeNode[]>()
  for (const node of nodes) {
    const parentId = node.parent_id
    if (!childrenMap.has(parentId)) {
      childrenMap.set(parentId, [])
    }
    childrenMap.get(parentId)!.push(node)
  }

  const rootNodes = childrenMap.get(null) ?? []

  function renderNode(node: TreeNode, depth: number): React.ReactNode {
    const children = childrenMap.get(node.id) ?? []
    const isCollapsed = collapsed.has(node.id)
    const hasChildren = children.length > 0

    return (
      <div key={node.id}>
        <div
          className={cn(
            'flex items-center gap-2 border-b border-gray-100 py-2',
            node.status === 'invalid' && 'opacity-50',
          )}
          style={{ paddingLeft: `${depth * 20 + 8}px` }}
        >
          {hasChildren ? (
            <button
              onClick={() => onToggleCollapse(node.id)}
              className="shrink-0 rounded p-0.5 hover:bg-gray-100"
            >
              {isCollapsed ? (
                <ChevronRight className="h-3.5 w-3.5 text-gray-400" />
              ) : (
                <ChevronDown className="h-3.5 w-3.5 text-gray-400" />
              )}
            </button>
          ) : (
            <span className="w-[18px]" />
          )}

          <div className={cn('h-2 w-2 shrink-0 rounded-full', statusDot[node.status])} />

          <Link
            to={ROUTES.CONJECTURE(node.id)}
            className={cn(
              'min-w-0 flex-1 font-mono text-xs hover:text-blue-600',
              node.status === 'invalid' && 'line-through text-gray-400',
            )}
          >
            {truncate(node.lean_statement, 50)}
          </Link>

          {node.status === 'proved' && <Check className="h-3 w-3 text-green-600" />}
          {node.status === 'disproved' && <X className="h-3 w-3 text-red-600" />}

          {node.comment_count > 0 && (
            <span className="inline-flex items-center gap-0.5 text-xs text-gray-400">
              <MessageSquare className="h-3 w-3" />
              {node.comment_count}
            </span>
          )}
        </div>

        {hasChildren && !isCollapsed && children.map((child) => renderNode(child, depth + 1))}
      </div>
    )
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      {rootNodes.map((node) => renderNode(node, 0))}
    </div>
  )
}
