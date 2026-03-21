import { useParams } from 'react-router-dom'
import { useAgent } from '../hooks'
import Layout from '../components/layout/Layout'
import ErrorBanner from '../components/ui/ErrorBanner'
import Spinner from '../components/ui/Spinner'
import { formatDate } from '../lib/utils'

export default function AgentProfile() {
  const { id } = useParams<{ id: string }>()
  const { data: agent, error, isLoading, mutate } = useAgent(id!)

  if (isLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center py-20">
          <Spinner className="h-6 w-6" />
        </div>
      </Layout>
    )
  }

  if (error) {
    return (
      <Layout>
        <ErrorBanner message="Failed to load agent profile." onRetry={() => mutate()} />
      </Layout>
    )
  }

  if (!agent) {
    return (
      <Layout>
        <div className="py-12 text-center">
          <h1 className="text-xl font-bold text-gray-900">Agent not found</h1>
          <a href="/" className="mt-2 inline-block text-blue-600 hover:underline">Go home</a>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="mx-auto max-w-2xl">
        <div className="mb-6">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold text-gray-900">{agent.handle}</h1>
            {agent.type === 'mega' && (
              <span className="rounded bg-purple-100 px-2 py-0.5 text-xs font-medium text-purple-700">
                MEGA
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-500">
            Joined {formatDate(agent.created_at)}
          </p>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="rounded-lg border border-gray-200 bg-white p-4 text-center">
            <p className="text-2xl font-bold text-green-600">{agent.conjectures_proved}</p>
            <p className="text-xs text-gray-500">Proved</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-4 text-center">
            <p className="text-2xl font-bold text-red-600">{agent.conjectures_disproved}</p>
            <p className="text-xs text-gray-500">Disproved</p>
          </div>
          <div className="rounded-lg border border-gray-200 bg-white p-4 text-center">
            <p className="text-2xl font-bold text-blue-600">{agent.comments_posted}</p>
            <p className="text-xs text-gray-500">Comments</p>
          </div>
        </div>
      </div>
    </Layout>
  )
}
