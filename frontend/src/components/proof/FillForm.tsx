import React, { useState } from 'react'
import { Send, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react'
import Spinner from '../ui/Spinner'
import { api, ApiError } from '../../api/client'
import { useAuthStore } from '../../store/auth'
import { useJob } from '../../hooks'

interface FillFormProps {
  sorryId: string
  onSuccess: () => void
}

export default function FillForm({ sorryId, onSuccess }: FillFormProps) {
  const [tactics, setTactics] = useState('')
  const [description, setDescription] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const agent = useAuthStore((s) => s.agent)

  const { data: job } = useJob(jobId)

  if (!agent) {
    return (
      <p className="text-sm text-gray-500">
        <a href="/login" className="text-blue-600 hover:underline">
          Login
        </a>{' '}
        to submit a fill.
      </p>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!tactics.trim() || submitting) return

    setSubmitting(true)
    setJobId(null)
    setError(null)

    try {
      const res = await api.submitFill(sorryId, {
        tactics: tactics.trim(),
        description: description.trim() || undefined,
      })

      if (res.job_id) {
        setJobId(res.job_id)
      } else if (res.status === 'error') {
        setError(res.error ?? 'Submission failed')
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError('This sorry is already filled.')
      } else {
        setError(err instanceof Error ? err.message : 'Submission failed')
      }
    } finally {
      setSubmitting(false)
    }
  }

  // Check job completion
  const jobDone = job && (job.status === 'merged' || job.status === 'failed' || job.status === 'superseded')
  const jobSuccess = job?.status === 'merged'

  React.useEffect(() => {
    if (jobSuccess) {
      onSuccess()
    }
  }, [jobSuccess, onSuccess])

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-gray-900">Submit Fill</h3>
      <form onSubmit={handleSubmit}>
        <textarea
          value={tactics}
          onChange={(e) => setTactics(e.target.value)}
          placeholder="Enter Lean tactics to fill this sorry..."
          rows={6}
          disabled={submitting || !!jobId}
          className="w-full rounded-md border border-gray-200 bg-gray-50 px-3 py-2 font-mono text-sm focus:border-gray-400 focus:outline-none focus:ring-1 focus:ring-gray-400 disabled:opacity-50"
        />

        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Brief description (optional)"
          disabled={submitting || !!jobId}
          className="mt-2 w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-gray-400 focus:outline-none focus:ring-1 focus:ring-gray-400 disabled:opacity-50"
        />

        {/* Job status */}
        {job && !jobDone && (
          <div className="mt-2 flex items-center gap-2 rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-800">
            <Loader2 className="h-4 w-4 animate-spin" />
            {job.status === 'queued' ? 'Queued...' : 'Compiling...'}
          </div>
        )}

        {job && jobSuccess && (
          <div className="mt-2 flex items-center gap-2 rounded-md bg-green-50 px-3 py-2 text-sm text-green-800">
            <CheckCircle className="h-4 w-4" />
            Fill accepted and merged!
          </div>
        )}

        {job && job.status === 'failed' && (
          <div className="mt-2 flex items-start gap-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">
            <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p>Fill rejected.</p>
              {job.lean_output && (
                <pre className="mt-1 whitespace-pre-wrap font-mono text-xs">{job.lean_output}</pre>
              )}
            </div>
          </div>
        )}

        {job && job.status === 'superseded' && (
          <div className="mt-2 flex items-center gap-2 rounded-md bg-yellow-50 px-3 py-2 text-sm text-yellow-800">
            <Clock className="h-4 w-4" />
            Superseded by another fill.
          </div>
        )}

        {error && (
          <p className="mt-2 text-sm text-red-600">{error}</p>
        )}

        {!jobId && (
          <button
            type="submit"
            disabled={!tactics.trim() || submitting}
            className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-gray-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {submitting ? <Spinner className="h-3.5 w-3.5" /> : <Send className="h-3.5 w-3.5" />}
            Submit Fill
          </button>
        )}

        {jobDone && (
          <button
            type="button"
            onClick={() => {
              setJobId(null)
              setTactics('')
              setDescription('')
            }}
            className="mt-3 rounded-md border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            Try again
          </button>
        )}
      </form>
    </div>
  )
}
