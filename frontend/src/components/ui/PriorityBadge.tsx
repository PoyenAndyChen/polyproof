import { AlertTriangle } from 'lucide-react'
import { cn } from '../../lib/utils'
import type { Priority } from '../../types'

export default function PriorityBadge({ priority }: { priority: Priority }) {
  if (priority === 'normal') return null

  return (
    <span
      className={cn(
        'inline-flex items-center gap-0.5 text-xs font-semibold uppercase',
        priority === 'critical' && 'text-red-600',
        priority === 'high' && 'text-orange-500',
        priority === 'low' && 'text-gray-400',
      )}
    >
      {priority === 'critical' && <AlertTriangle className="h-3 w-3" />}
      {priority}
    </span>
  )
}
