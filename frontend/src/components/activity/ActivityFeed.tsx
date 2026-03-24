import { Link } from 'react-router-dom'
import {
  CheckCircle,
  MessageSquare,
  Wrench,
  Undo2,
  Zap,
  Loader2,
} from 'lucide-react'
import { useProjectActivity } from '../../hooks'
import { formatDate, truncate } from '../../lib/utils'
import { ROUTES } from '../../lib/constants'
import ErrorBanner from '../ui/ErrorBanner'
import type { ActivityEvent, ActivityEventType } from '../../types'

const eventConfig: Record<
  ActivityEventType,
  { icon: React.ReactNode; verb: string; color: string }
> = {
  fill: { icon: <CheckCircle className="h-4 w-4" />, verb: 'filled', color: 'text-green-600' },
  comment: { icon: <MessageSquare className="h-4 w-4" />, verb: 'commented on', color: 'text-blue-600' },
  decomposition: { icon: <Wrench className="h-4 w-4" />, verb: 'decomposed', color: 'text-purple-600' },
  fill_reverted: { icon: <Undo2 className="h-4 w-4" />, verb: 'reverted fill of', color: 'text-orange-600' },
  priority_changed: { icon: <Zap className="h-4 w-4" />, verb: 'changed priority of', color: 'text-yellow-600' },
}

function ActivityItem({ event }: { event: ActivityEvent }) {
  const config = eventConfig[event.event_type]
  const agentName = event.agent?.handle ?? 'System'
  const sorryLabel = event.sorry_declaration_name
    ? truncate(event.sorry_declaration_name, 50)
    : event.sorry_goal_state
      ? truncate(event.sorry_goal_state, 50)
      : 'a sorry'

  return (
    <div className="flex items-start gap-3 py-2.5">
      <span className={config.color}>{config.icon}</span>
      <div className="min-w-0 flex-1 text-sm">
        <span className="font-medium text-gray-900">
          {event.agent ? (
            <Link to={ROUTES.AGENT(event.agent.id)} className="hover:text-blue-600">
              {agentName}
            </Link>
          ) : (
            agentName
          )}
        </span>{' '}
        <span className="text-gray-600">{config.verb}</span>{' '}
        {event.sorry_id ? (
          <Link
            to={ROUTES.SORRY(event.sorry_id)}
            className="font-mono text-sm text-gray-700 hover:text-blue-600"
          >
            {sorryLabel}
          </Link>
        ) : (
          <span className="font-mono text-sm text-gray-700">{sorryLabel}</span>
        )}
      </div>
      <span className="shrink-0 text-xs text-gray-400">{formatDate(event.created_at)}</span>
    </div>
  )
}

interface ActivityFeedProps {
  projectId: string
}

export default function ActivityFeed({ projectId }: ActivityFeedProps) {
  const { data, error, isLoading, mutate } = useProjectActivity(projectId)

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error) {
    return <ErrorBanner message="Failed to load activity." onRetry={() => mutate()} />
  }

  if (!data || data.events.length === 0) {
    return <p className="py-4 text-center text-sm text-gray-400">No activity yet.</p>
  }

  return (
    <div className="divide-y divide-gray-100">
      {data.events.map((event) => (
        <ActivityItem key={event.id} event={event} />
      ))}
    </div>
  )
}
