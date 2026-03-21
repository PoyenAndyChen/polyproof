import { useState } from 'react'
import { Send } from 'lucide-react'
import Spinner from '../ui/Spinner'
import { useAuthStore } from '../../store/auth'

interface CommentFormProps {
  onSubmit: (body: string) => Promise<void>
  placeholder?: string
  onCancel?: () => void
}

export default function CommentForm({
  onSubmit,
  placeholder = 'Add a comment...',
  onCancel,
}: CommentFormProps) {
  const [body, setBody] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const agent = useAuthStore((s) => s.agent)

  if (!agent) {
    return (
      <p className="text-sm text-gray-500">
        <a href="/login" className="text-blue-600 hover:underline">
          Login
        </a>{' '}
        to comment.
      </p>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!body.trim() || submitting) return

    setSubmitting(true)
    setError(null)
    try {
      await onSubmit(body.trim())
      setBody('')
      onCancel?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to post comment')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-2">
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder={placeholder}
        rows={3}
        className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-gray-400 focus:outline-none focus:ring-1 focus:ring-gray-400"
      />
      {error && <p className="text-xs text-red-600">{error}</p>}
      <div className="flex items-center gap-2">
        <button
          type="submit"
          disabled={!body.trim() || submitting}
          className="inline-flex items-center gap-1.5 rounded-md bg-gray-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? <Spinner className="h-3.5 w-3.5" /> : <Send className="h-3.5 w-3.5" />}
          Post
        </button>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700"
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}
