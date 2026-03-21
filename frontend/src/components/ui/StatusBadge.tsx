import { cn } from '../../lib/utils'
import type { ConjectureStatus } from '../../types'

const statusStyles: Record<ConjectureStatus, string> = {
  open: 'bg-white text-gray-700 border-gray-300',
  decomposed: 'bg-blue-500 text-white border-blue-500',
  proved: 'bg-green-500 text-white border-green-500',
  disproved: 'bg-red-500 text-white border-red-500',
  invalid: 'bg-gray-300 text-gray-500 border-gray-300 line-through',
}

export default function StatusBadge({ status }: { status: ConjectureStatus }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide',
        statusStyles[status],
      )}
    >
      {status}
    </span>
  )
}
