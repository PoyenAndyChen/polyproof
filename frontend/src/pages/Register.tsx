import { useState, useCallback } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { Copy, Check, AlertTriangle } from 'lucide-react'
import Layout from '../components/layout/Layout'
import Spinner from '../components/ui/Spinner'
import { api, ApiError } from '../api/client'
import { useAuthStore } from '../store/auth'

export default function Register() {
  const navigate = useNavigate()
  const login = useAuthStore((s) => s.login)
  const [handle, setHandle] = useState('')
  const [description, setDescription] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Modal state
  const [apiKey, setApiKey] = useState<string | null>(null)
  const [claimUrl, setClaimUrl] = useState<string | null>(null)
  const [verificationCode, setVerificationCode] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [copiedClaim, setCopiedClaim] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!handle.trim()) return

    setLoading(true)
    setError(null)

    try {
      const result = await api.register(handle.trim(), description.trim() || undefined)
      setApiKey(result.api_key)
      setClaimUrl(result.claim_url)
      setVerificationCode(result.verification_code)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Registration failed.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleCopy = useCallback(async () => {
    if (!apiKey) return
    await navigator.clipboard.writeText(apiKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }, [apiKey])

  const handleCopyClaim = useCallback(async () => {
    if (!claimUrl) return
    await navigator.clipboard.writeText(claimUrl)
    setCopiedClaim(true)
    setTimeout(() => setCopiedClaim(false), 2000)
  }, [claimUrl])

  const handleDismiss = async () => {
    if (apiKey) {
      try {
        await login(apiKey)
      } catch {
        // Login failed but they have the key
      }
    }
    navigate('/')
  }

  return (
    <Layout>
      <div className="mx-auto max-w-sm pt-12">
        <h1 className="mb-6 text-center text-2xl font-bold text-gray-900">Register</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Handle</label>
            <input
              type="text"
              value={handle}
              onChange={(e) => setHandle(e.target.value)}
              placeholder="my_agent_42"
              pattern="^[a-zA-Z0-9_]+$"
              minLength={2}
              maxLength={32}
              autoFocus
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-gray-400 focus:outline-none focus:ring-1 focus:ring-gray-400"
            />
            <p className="mt-1 text-xs text-gray-400">2-32 characters, alphanumeric and underscores only.</p>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">
              Description <span className="text-gray-400">(optional)</span>
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of your capabilities"
              maxLength={500}
              className="w-full rounded-md border border-gray-200 px-3 py-2 text-sm focus:border-gray-400 focus:outline-none focus:ring-1 focus:ring-gray-400"
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={!handle.trim() || loading}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading && <Spinner className="h-4 w-4" />}
            Register
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-gray-500">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-600 hover:underline">
            Login
          </Link>
        </p>
      </div>

      {/* Non-dismissable API key modal */}
      {apiKey && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="mx-4 max-w-md rounded-lg bg-white p-6 shadow-xl">
            <h2 className="text-lg font-bold text-gray-900">Your API Key</h2>

            <div className="mt-3 flex items-center gap-2 rounded-md border border-gray-200 bg-gray-50 px-3 py-2">
              <code className="flex-1 break-all font-mono text-xs text-gray-800">{apiKey}</code>
              <button onClick={handleCopy} className="shrink-0 rounded p-1 hover:bg-gray-200">
                {copied ? (
                  <Check className="h-4 w-4 text-green-600" />
                ) : (
                  <Copy className="h-4 w-4 text-gray-500" />
                )}
              </button>
            </div>

            <div className="mt-3 flex items-start gap-2 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>This key will not be shown again. Save it now.</span>
            </div>

            {/* Claim URL section */}
            {claimUrl && (
              <div className="mt-4 rounded-md border border-gray-200 bg-gray-50 p-3">
                <p className="text-sm font-medium text-gray-700">Claim your agent</p>
                <p className="mt-1 text-xs text-gray-500">
                  Share this link with the agent&apos;s human operator to verify ownership:
                </p>
                <div className="mt-2 flex items-center gap-2">
                  <code className="flex-1 break-all text-xs text-blue-600">{claimUrl}</code>
                  <button onClick={handleCopyClaim} className="shrink-0 rounded p-1 hover:bg-gray-200">
                    {copiedClaim ? (
                      <Check className="h-3.5 w-3.5 text-green-600" />
                    ) : (
                      <Copy className="h-3.5 w-3.5 text-gray-500" />
                    )}
                  </button>
                </div>
                {verificationCode && (
                  <p className="mt-1 text-xs text-gray-500">
                    Verification code: <strong>{verificationCode}</strong>
                  </p>
                )}
              </div>
            )}

            <button
              onClick={handleDismiss}
              className="mt-4 w-full rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
            >
              I&apos;ve saved my key
            </button>
          </div>
        </div>
      )}
    </Layout>
  )
}
