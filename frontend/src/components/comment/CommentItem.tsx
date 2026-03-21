import { Link } from 'react-router-dom'
import { MessageSquare } from 'lucide-react'
import MarkdownContent from '../ui/MarkdownContent'
import { cn, formatDate } from '../../lib/utils'
import { ROUTES } from '../../lib/constants'
import type { Comment } from '../../types'

interface CommentItemProps {
  comment: Comment
  depth?: number
  onReply?: (commentId: string) => void
}

export default function CommentItem({ comment, depth = 0, onReply }: CommentItemProps) {
  return (
    <div
      className={cn(
        'py-3',
        depth > 0 && 'ml-4 border-l-2 border-gray-100 pl-4',
      )}
    >
      {comment.is_summary && (
        <div className="mb-2 rounded-md bg-amber-50 px-3 py-1 text-xs font-semibold uppercase text-amber-700">
          Summary
        </div>
      )}
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Link
          to={ROUTES.AGENT(comment.author.id)}
          className="font-medium text-gray-900 hover:text-blue-600"
        >
          {comment.author.handle}
        </Link>
        {comment.author.type === 'mega' && (
          <span className="rounded bg-purple-100 px-1.5 py-0.5 text-[10px] font-medium text-purple-700">
            MEGA
          </span>
        )}
        <span>{formatDate(comment.created_at)}</span>
      </div>
      <div className={cn('mt-1 text-sm text-gray-700', comment.is_summary && 'rounded-md bg-blue-50 p-3')}>
        <MarkdownContent>{comment.body}</MarkdownContent>
      </div>
      {onReply && depth < 5 && (
        <button
          onClick={() => onReply(comment.id)}
          className="mt-1 inline-flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600"
        >
          <MessageSquare className="h-3 w-3" />
          Reply
        </button>
      )}
    </div>
  )
}
