import { useState, useMemo } from 'react'
import CommentItem from './CommentItem'
import CommentForm from './CommentForm'
import type { Comment, CommentThread as CommentThreadType } from '../../types'
import { MAX_COMMENT_DEPTH } from '../../lib/constants'

interface CommentThreadProps {
  thread: CommentThreadType
  onPostComment: (body: string, parentCommentId?: string) => Promise<void>
}

/** Build a tree of comments from flat list using parent_comment_id */
function buildReplyTree(comments: Comment[]): { roots: Comment[]; childrenMap: Map<string, Comment[]> } {
  const childrenMap = new Map<string, Comment[]>()
  const roots: Comment[] = []

  for (const comment of comments) {
    if (comment.parent_comment_id) {
      if (!childrenMap.has(comment.parent_comment_id)) {
        childrenMap.set(comment.parent_comment_id, [])
      }
      childrenMap.get(comment.parent_comment_id)!.push(comment)
    } else {
      roots.push(comment)
    }
  }

  return { roots, childrenMap }
}

function CommentWithReplies({
  comment,
  childrenMap,
  depth,
  onReply,
}: {
  comment: Comment
  childrenMap: Map<string, Comment[]>
  depth: number
  onReply: (parentCommentId: string) => void
}) {
  const children = childrenMap.get(comment.id) ?? []

  return (
    <>
      <CommentItem
        comment={comment}
        depth={depth}
        onReply={depth < MAX_COMMENT_DEPTH ? () => onReply(comment.id) : undefined}
      />
      {children.map((child) => (
        <CommentWithReplies
          key={child.id}
          comment={child}
          childrenMap={childrenMap}
          depth={depth + 1}
          onReply={onReply}
        />
      ))}
    </>
  )
}

export default function CommentThread({ thread, onPostComment }: CommentThreadProps) {
  const [replyingTo, setReplyingTo] = useState<string | null>(null)

  const { roots, childrenMap } = useMemo(
    () => buildReplyTree(thread.comments_after_summary),
    [thread.comments_after_summary],
  )

  const handleReply = (parentCommentId: string) => {
    setReplyingTo(parentCommentId)
  }

  const handleSubmitReply = async (body: string) => {
    if (replyingTo) {
      await onPostComment(body, replyingTo)
      setReplyingTo(null)
    }
  }

  return (
    <div className="space-y-1">
      {/* Summary comment */}
      {thread.summary && (
        <CommentItem comment={thread.summary} depth={0} />
      )}

      {/* Comments after summary */}
      {roots.length === 0 && !thread.summary && (
        <p className="py-4 text-center text-sm text-gray-400">No discussion yet. Be the first to comment.</p>
      )}

      {roots.map((comment) => (
        <div key={comment.id}>
          <CommentWithReplies
            comment={comment}
            childrenMap={childrenMap}
            depth={0}
            onReply={handleReply}
          />
          {replyingTo === comment.id && (
            <div className="ml-8 mt-2">
              <CommentForm
                onSubmit={handleSubmitReply}
                placeholder="Write a reply..."
                onCancel={() => setReplyingTo(null)}
              />
            </div>
          )}
        </div>
      ))}

      {/* Inline reply forms for nested comments */}
      {replyingTo && !roots.find((r) => r.id === replyingTo) && (
        <div className="ml-8 mt-2">
          <CommentForm
            onSubmit={handleSubmitReply}
            placeholder="Write a reply..."
            onCancel={() => setReplyingTo(null)}
          />
        </div>
      )}

      {/* New top-level comment */}
      <div className="pt-4">
        <CommentForm
          onSubmit={(body) => onPostComment(body)}
          placeholder="Add a comment..."
        />
      </div>
    </div>
  )
}
