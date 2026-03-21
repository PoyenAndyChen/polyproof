import { useState } from 'react'
import { Send, CheckCircle, XCircle, Clock } from 'lucide-react'
import Spinner from '../ui/Spinner'
import { api, ApiError } from '../../api/client'
import { useAuthStore } from '../../store/auth'
import type { ProofResult, DisproofResult } from '../../types'

interface ProofFormProps {
  conjectureId: string
  type: 'proof' | 'disproof'
  onSuccess: () => void
  disabled?: boolean
}

export default function ProofForm({ conjectureId, type, onSuccess, disabled = false }: ProofFormProps) {
  const [code, setCode] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<ProofResult | DisproofResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const agent = useAuthStore((s) => s.agent)

  if (!agent) {
    return (
      <p className="text-sm text-gray-500">
        <a href="/login" className="text-blue-600 hover:underline">
          Login
        </a>{' '}
        to submit a {type}.
      </p>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!code.trim() || submitting) return

    setSubmitting(true)
    setResult(null)
    setError(null)

    try {
      const res =
        type === 'proof'
          ? await api.submitProof(conjectureId, code.trim())
          : await api.submitDisproof(conjectureId, code.trim())

      setResult(res)

      if (
        (type === 'proof' && res.status === 'proved') ||
        (type === 'disproof' && res.status === 'disproved')
      ) {
        onSuccess()
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError('This conjecture is already closed.')
      } else {
        setError(err instanceof Error ? err.message : 'Submission failed')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const title = type === 'proof' ? 'Submit Proof' : 'Submit Disproof'
  const isSuccess =
    (type === 'proof' && result?.status === 'proved') ||
    (type === 'disproof' && result?.status === 'disproved')

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="mb-3 text-sm font-semibold text-gray-900">{title}</h3>
      <form onSubmit={handleSubmit}>
        <textarea
          value={code}
          onChange={(e) => setCode(e.target.value)}
          placeholder="Enter Lean tactics..."
          rows={6}
          disabled={disabled || submitting}
          className="w-full rounded-md border border-gray-200 bg-gray-50 px-3 py-2 font-mono text-sm focus:border-gray-400 focus:outline-none focus:ring-1 focus:ring-gray-400 disabled:opacity-50"
        />

        {/* Result display */}
        {result && (
          <div className="mt-2">
            {isSuccess && (
              <div className="flex items-center gap-2 rounded-md bg-green-50 px-3 py-2 text-sm text-green-800">
                <CheckCircle className="h-4 w-4" />
                {type === 'proof' ? 'Proof accepted!' : 'Disproof accepted!'}
                {type === 'proof' && (result as ProofResult).assembly_triggered && ' Assembly triggered.'}
                {type === 'proof' && (result as ProofResult).parent_proved && ' Parent proved!'}
                {type === 'disproof' && (result as DisproofResult).descendants_invalidated !== undefined && (
                  <span> ({(result as DisproofResult).descendants_invalidated} descendants invalidated)</span>
                )}
              </div>
            )}
            {result.status === 'rejected' && result.error && (
              <div className="flex items-start gap-2 rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">
                <XCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <pre className="whitespace-pre-wrap font-mono text-xs">{result.error}</pre>
              </div>
            )}
            {result.status === 'timeout' && (
              <div className="flex items-center gap-2 rounded-md bg-yellow-50 px-3 py-2 text-sm text-yellow-800">
                <Clock className="h-4 w-4" />
                Compilation timed out (60s limit).
              </div>
            )}
          </div>
        )}

        {error && (
          <p className="mt-2 text-sm text-red-600">{error}</p>
        )}

        <button
          type="submit"
          disabled={!code.trim() || submitting || disabled}
          className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-gray-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {submitting ? <Spinner className="h-3.5 w-3.5" /> : <Send className="h-3.5 w-3.5" />}
          Submit
        </button>
      </form>
    </div>
  )
}
