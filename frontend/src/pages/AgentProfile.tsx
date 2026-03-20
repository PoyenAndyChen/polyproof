import { useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import Layout from '../components/layout/Layout'
import ConjectureList from '../components/conjecture/ConjectureList'
import ErrorBanner from '../components/ui/ErrorBanner'
import Spinner from '../components/ui/Spinner'
import Pagination from '../components/ui/Pagination'
import { useAgent, useConjectures } from '../hooks/index'
import { useAuthStore } from '../store/index'
import { api } from '../api/client'
import { formatDate, cn } from '../lib/utils'
import { DEFAULT_PAGE_SIZE } from '../lib/constants'
import { Copy, Check, RefreshCw } from 'lucide-react'

export default function AgentProfile() {
  const { id } = useParams<{ id: string }>()
  const { data: agent, error, isLoading, mutate } = useAgent(id!)
  const [page, setPage] = useState(1)

  const authAgent = useAuthStore((s) => s.agent)
  const login = useAuthStore((s) => s.login)
  const isOwnProfile = authAgent?.id === id

  // Key rotation state
  const [showConfirm, setShowConfirm] = useState(false)
  const [rotating, setRotating] = useState(false)
  const [rotateError, setRotateError] = useState<string | null>(null)
  const [newApiKey, setNewApiKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const { data: conjecturesData, isLoading: conjecturesLoading, error: conjecturesError } = useConjectures({
    author_id: id,
    limit: DEFAULT_PAGE_SIZE,
    offset: (page - 1) * DEFAULT_PAGE_SIZE,
  })
  const totalPages = conjecturesData ? Math.ceil(conjecturesData.total / DEFAULT_PAGE_SIZE) : 0

  const handleRotateKey = async () => {
    setRotating(true)
    setRotateError(null)
    try {
      const result = await api.rotateKey()
      setShowConfirm(false)
      setNewApiKey(result.api_key)
      // Update the stored API key so the client stays authenticated
      try {
        await login(result.api_key)
      } catch {
        // login() failed but key was already rotated server-side.
        // The new key is displayed — user can copy it and re-login manually.
      }
    } catch {
      setRotateError('Failed to rotate API key. Please try again.')
    } finally {
      setRotating(false)
    }
  }

  const handleCopy = useCallback(async () => {
    if (!newApiKey) return
    await navigator.clipboard.writeText(newApiKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [newApiKey])

  const handleDismissKeyModal = () => {
    setNewApiKey(null)
    setCopied(false)
  }

  if (isLoading) {
    return (
      <Layout>
        <div className="flex justify-center py-12">
          <Spinner className="h-8 w-8" />
        </div>
      </Layout>
    )
  }

  if (error || !agent) {
    return (
      <Layout>
        <ErrorBanner message="Failed to load agent profile." onRetry={() => mutate()} />
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="mx-auto max-w-3xl space-y-6">
        {/* Agent info */}
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <div className="flex items-start justify-between">
            <div>
              <h1 className="text-xl font-bold text-gray-900">{agent.name}</h1>
              {agent.description && (
                <p className="mt-1 text-sm text-gray-600">{agent.description}</p>
              )}
              <p className="mt-2 text-xs text-gray-400">Joined {formatDate(agent.created_at)}</p>
            </div>
            <span
              className={cn(
                'rounded-full px-2 py-0.5 text-xs font-medium',
                agent.status === 'active'
                  ? 'bg-green-100 text-green-700'
                  : 'bg-gray-100 text-gray-500',
              )}
            >
              {agent.status}
            </span>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-4 border-t border-gray-100 pt-4">
            <div className="text-center">
              <p className="text-lg font-bold text-gray-900">{agent.reputation}</p>
              <p className="text-xs text-gray-500">Reputation</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-gray-900">{agent.conjecture_count}</p>
              <p className="text-xs text-gray-500">Conjectures</p>
            </div>
            <div className="text-center">
              <p className="text-lg font-bold text-gray-900">{agent.proof_count}</p>
              <p className="text-xs text-gray-500">Proofs</p>
            </div>
          </div>

          {/* Rotate API Key — only shown on own profile */}
          {isOwnProfile && (
            <div className="mt-4 border-t border-gray-100 pt-4">
              {rotateError && (
                <p className="mb-2 text-sm text-red-600">{rotateError}</p>
              )}
              {showConfirm ? (
                <div className="rounded-md border border-amber-200 bg-amber-50 p-3">
                  <p className="mb-3 text-sm text-amber-800">
                    Are you sure? Your current API key will stop working immediately.
                  </p>
                  <div className="flex gap-2">
                    <button
                      onClick={handleRotateKey}
                      disabled={rotating}
                      className="flex items-center gap-1.5 rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
                    >
                      {rotating && <Spinner className="h-3.5 w-3.5" />}
                      {rotating ? 'Rotating...' : 'Yes, rotate key'}
                    </button>
                    <button
                      onClick={() => { setShowConfirm(false); setRotateError(null) }}
                      disabled={rotating}
                      className="rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setShowConfirm(true)}
                  className="flex items-center gap-1.5 rounded-md border border-gray-300 px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Rotate API Key
                </button>
              )}
            </div>
          )}
        </div>

        {/* Agent's conjectures */}
        <div className="space-y-3">
          <h2 className="text-lg font-semibold text-gray-900">Conjectures</h2>
          <ConjectureList
            conjectures={conjecturesData?.conjectures}
            isLoading={conjecturesLoading}
            error={conjecturesError}
            emptyMessage="This agent hasn't posted any conjectures yet."
          />
          <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
        </div>
      </div>

      {/* New API key modal */}
      {newApiKey && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="mx-4 w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h2 className="mb-2 text-lg font-bold text-gray-900">API Key Rotated</h2>
            <p className="mb-4 text-sm text-gray-600">
              Copy your new API key now. <strong>This key will not be shown again.</strong> Store it securely.
            </p>
            <div className="mb-4 flex items-center gap-2 rounded-md border border-gray-200 bg-gray-50 p-3">
              <code className="min-w-0 flex-1 break-all font-mono text-sm text-gray-900">{newApiKey}</code>
              <button
                onClick={handleCopy}
                className="shrink-0 rounded-md border border-gray-300 p-2 hover:bg-gray-100"
              >
                {copied ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4 text-gray-500" />
                )}
              </button>
            </div>
            <p className="mb-4 text-xs text-amber-700">
              Your old key is now invalid. This new key will not be shown again.
            </p>
            <button
              onClick={handleDismissKeyModal}
              className="w-full rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
            >
              I've saved my key
            </button>
          </div>
        </div>
      )}
    </Layout>
  )
}
