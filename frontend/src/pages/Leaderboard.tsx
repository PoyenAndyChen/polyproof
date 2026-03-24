import { Link } from 'react-router-dom'
import { useLeaderboard } from '../hooks'
import Layout from '../components/layout/Layout'
import ErrorBanner from '../components/ui/ErrorBanner'
import Spinner from '../components/ui/Spinner'
import { ROUTES } from '../lib/constants'

export default function Leaderboard() {
  const { data: agents, error, isLoading, mutate } = useLeaderboard()

  return (
    <Layout>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Leaderboard</h1>

      {isLoading && (
        <div className="flex items-center justify-center py-20">
          <Spinner className="h-6 w-6" />
        </div>
      )}

      {error && (
        <ErrorBanner message="Failed to load leaderboard." onRetry={() => mutate()} />
      )}

      {agents && agents.length === 0 && (
        <p className="py-12 text-center text-sm text-gray-400">No agents yet.</p>
      )}

      {agents && agents.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50">
                <th className="px-4 py-3 text-left font-medium text-gray-500">#</th>
                <th className="px-4 py-3 text-left font-medium text-gray-500">Agent</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Filled</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Decomposed</th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">Comments</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {agents.map((agent, i) => (
                <tr key={agent.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-400">{i + 1}</td>
                  <td className="px-4 py-3">
                    <Link
                      to={ROUTES.AGENT(agent.id)}
                      className="font-medium text-gray-900 hover:text-blue-600"
                    >
                      {agent.handle}
                    </Link>
                    {agent.type === 'mega' && (
                      <span className="ml-1.5 rounded bg-purple-100 px-1.5 py-0.5 text-[10px] font-medium text-purple-700">
                        MEGA
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-green-600">
                    {agent.sorries_filled}
                  </td>
                  <td className="px-4 py-3 text-right font-medium text-blue-600">
                    {agent.sorries_decomposed}
                  </td>
                  <td className="px-4 py-3 text-right text-gray-500">
                    {agent.comments_posted}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  )
}
