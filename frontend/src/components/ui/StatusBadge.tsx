import { cn } from '../../lib/utils'

const statusStyles: Record<string, string> = {
  open: 'bg-white text-gray-700 border-gray-300',
  decomposed: 'bg-blue-500 text-white border-blue-500',
  filled: 'bg-green-500 text-white border-green-500',
  filled_externally: 'bg-emerald-400 text-white border-emerald-400',
  invalid: 'bg-gray-300 text-gray-500 border-gray-300 line-through',
}

const statusLabels: Record<string, string> = {
  open: 'open',
  decomposed: 'decomposed',
  filled: 'filled',
  filled_externally: 'filled externally',
  invalid: 'invalid',
}

export default function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide',
        statusStyles[status] ?? statusStyles.open,
      )}
    >
      {statusLabels[status] ?? status}
    </span>
  )
}
