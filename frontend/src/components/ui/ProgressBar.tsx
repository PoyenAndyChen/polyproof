interface ProgressBarProps {
  percent: number
  label?: string
}

export default function ProgressBar({ percent, label }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, percent))

  return (
    <div className="flex items-center gap-3">
      <div className="h-2 flex-1 rounded-full bg-gray-200">
        <div
          className="h-2 rounded-full bg-green-500 transition-all duration-300"
          style={{ width: `${clamped}%` }}
        />
      </div>
      {label ? (
        <span className="shrink-0 text-sm text-gray-600">{label}</span>
      ) : (
        <span className="shrink-0 text-sm font-medium text-gray-700">{clamped}%</span>
      )}
    </div>
  )
}
