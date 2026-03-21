import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'
import { MessageSquare, ChevronRight, ChevronDown, Check, X } from 'lucide-react'
import { cn, truncate } from '../../lib/utils'
import type { ConjectureStatus, Priority } from '../../types'

export interface ConjectureNodeData {
  id: string
  lean_statement: string
  status: ConjectureStatus
  priority: Priority
  comment_count: number
  child_count: number
  proved_child_count: number
  collapsed: boolean
  dimmed: boolean
  onToggleCollapse: (id: string) => void
  onNodeClick: (id: string) => void
}

const statusBg: Record<ConjectureStatus, string> = {
  open: 'bg-white',
  decomposed: 'bg-blue-50',
  proved: 'bg-green-50',
  disproved: 'bg-red-50',
  invalid: 'bg-gray-100 opacity-60',
}

const statusDot: Record<ConjectureStatus, string> = {
  open: 'bg-gray-400',
  decomposed: 'bg-blue-500',
  proved: 'bg-green-500',
  disproved: 'bg-red-500',
  invalid: 'bg-gray-400',
}

const priorityBorder: Record<Priority, string> = {
  critical: 'border-red-500 border-2',
  high: 'border-orange-400 border-2',
  normal: 'border-gray-200 border',
  low: 'border-gray-200 border',
}

function ConjectureNodeComponent({ data }: NodeProps & { data: ConjectureNodeData }) {
  const isDecomposed = data.status === 'decomposed'

  return (
    <div
      className={cn(
        'cursor-pointer rounded-lg px-3 py-2 shadow-sm transition-shadow hover:shadow-md',
        'min-w-[180px] max-w-[260px]',
        statusBg[data.status],
        priorityBorder[data.priority],
        data.dimmed && 'opacity-40',
        data.status === 'invalid' && 'line-through',
      )}
      onClick={(e) => {
        e.stopPropagation()
        data.onNodeClick(data.id)
      }}
    >
      <Handle type="target" position={Position.Top} className="!bg-gray-400 !w-2 !h-2" />

      <div className="flex items-start gap-2">
        <div className={cn('mt-1 h-2.5 w-2.5 shrink-0 rounded-full', statusDot[data.status])} />
        <div className="min-w-0 flex-1">
          <p className="font-mono text-xs leading-relaxed text-gray-800">
            {truncate(data.lean_statement, 60)}
          </p>
        </div>
        {data.status === 'proved' && <Check className="h-3.5 w-3.5 shrink-0 text-green-600" />}
        {data.status === 'disproved' && <X className="h-3.5 w-3.5 shrink-0 text-red-600" />}
      </div>

      <div className="mt-1.5 flex items-center gap-3 text-xs text-gray-500">
        {data.comment_count > 0 && (
          <span className="inline-flex items-center gap-0.5">
            <MessageSquare className="h-3 w-3" />
            {data.comment_count}
          </span>
        )}
        {isDecomposed && data.child_count > 0 && (
          <button
            onClick={(e) => {
              e.stopPropagation()
              data.onToggleCollapse(data.id)
            }}
            className="inline-flex items-center gap-0.5 rounded px-1 py-0.5 hover:bg-gray-200"
          >
            {data.collapsed ? (
              <ChevronRight className="h-3 w-3" />
            ) : (
              <ChevronDown className="h-3 w-3" />
            )}
            <span>
              {data.proved_child_count}/{data.child_count} proved
            </span>
          </button>
        )}
      </div>

      <Handle type="source" position={Position.Bottom} className="!bg-gray-400 !w-2 !h-2" />
    </div>
  )
}

export default memo(ConjectureNodeComponent)
