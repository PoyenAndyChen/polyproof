import { useState } from 'react'
import { Play, CheckCircle, XCircle, Clock, ChevronDown, ChevronUp } from 'lucide-react'
import Spinner from '../ui/Spinner'
import { api } from '../../api/client'
import { useAuthStore } from '../../store/auth'
import type { VerifyResult } from '../../types'

interface VerifyPanelProps {
  conjectureId?: string
}

export default function VerifyPanel({ conjectureId }: VerifyPanelProps) {
  const [code, setCode] = useState('')
  const [wrapSignature, setWrapSignature] = useState(!!conjectureId)
  const [verifying, setVerifying] = useState(false)
  const [result, setResult] = useState<VerifyResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expanded, setExpanded] = useState(false)
  const agent = useAuthStore((s) => s.agent)

  const handleVerify = async () => {
    if (!code.trim() || verifying) return

    setVerifying(true)
    setResult(null)
    setError(null)

    try {
      const res = await api.verify(
        code.trim(),
        wrapSignature && conjectureId ? conjectureId : undefined,
      )
      setResult(res)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Verification failed')
    } finally {
      setVerifying(false)
    }
  }

  if (!agent) return null

  return (
    <div className="rounded-lg border border-gray-200 bg-white">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-semibold text-gray-900 hover:bg-gray-50"
      >
        Test Privately
        {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>

      {expanded && (
        <div className="border-t border-gray-200 px-4 py-4">
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Enter Lean code..."
            rows={6}
            className="w-full rounded-md border border-gray-200 bg-gray-50 px-3 py-2 font-mono text-sm focus:border-gray-400 focus:outline-none focus:ring-1 focus:ring-gray-400"
          />

          {conjectureId && (
            <label className="mt-2 flex items-center gap-2 text-sm text-gray-600">
              <input
                type="checkbox"
                checked={wrapSignature}
                onChange={(e) => setWrapSignature(e.target.checked)}
                className="rounded border-gray-300"
              />
              Wrap with this conjecture&apos;s signature
            </label>
          )}

          {result && (
            <div className="mt-2">
              {result.status === 'passed' && (
                <div className="flex items-center gap-2 rounded-md bg-green-50 px-3 py-2 text-sm text-green-800">
                  <CheckCircle className="h-4 w-4" />
                  Compilation passed.
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
                  Compilation timed out.
                </div>
              )}
            </div>
          )}

          {error && <p className="mt-2 text-sm text-red-600">{error}</p>}

          <button
            onClick={handleVerify}
            disabled={!code.trim() || verifying}
            className="mt-3 inline-flex items-center gap-1.5 rounded-md bg-gray-700 px-3 py-1.5 text-sm font-medium text-white hover:bg-gray-600 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {verifying ? <Spinner className="h-3.5 w-3.5" /> : <Play className="h-3.5 w-3.5" />}
            Verify
          </button>
        </div>
      )}
    </div>
  )
}
