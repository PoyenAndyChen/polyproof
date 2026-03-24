import { useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useSorry, useProject } from '../hooks'
import Layout from '../components/layout/Layout'
import BreadcrumbNav from '../components/ui/BreadcrumbNav'
import MarkdownContent from '../components/ui/MarkdownContent'
import type { ReferenceMap } from '../components/ui/MarkdownContent'
import StatusBadge from '../components/ui/StatusBadge'
import PriorityBadge from '../components/ui/PriorityBadge'
import LeanCodeBlock from '../components/code/LeanCodeBlock'
import ErrorBanner from '../components/ui/ErrorBanner'
import Spinner from '../components/ui/Spinner'
import CommentThread from '../components/comment/CommentThread'
import FillForm from '../components/proof/FillForm'
import { ROUTES } from '../lib/constants'
import { truncate } from '../lib/utils'
import type { SorrySummary } from '../types'

function SorryCard({ sorry }: { sorry: SorrySummary }) {
  return (
    <Link
      to={ROUTES.SORRY(sorry.id)}
      className="block rounded-md border border-gray-200 bg-white p-3 hover:shadow-sm"
    >
      <div className="flex items-center gap-2">
        <StatusBadge status={sorry.status} />
        <span className="font-mono text-xs text-gray-700">
          {truncate(sorry.declaration_name, 40)}
          {sorry.sorry_index > 0 && <span className="text-gray-400"> #{sorry.sorry_index}</span>}
        </span>
      </div>
      <p className="mt-1 font-mono text-xs text-gray-500">
        {truncate(sorry.goal_state, 80)}
      </p>
      {sorry.filled_by_handle && (
        <p className="mt-1 text-xs text-gray-400">
          Filled by{' '}
          <span className="font-medium text-gray-600">{sorry.filled_by_handle}</span>
        </p>
      )}
    </Link>
  )
}

export default function SorryPage() {
  const { id } = useParams<{ id: string }>()
  const { data: sorry, error, isLoading, mutate } = useSorry(id!)

  // Fetch project title for breadcrumb
  const { data: project } = useProject(sorry?.project_id ?? '')

  // Build UUID -> declaration_name map for resolving sorry references
  const refs: ReferenceMap = useMemo(() => {
    const map: ReferenceMap = {}
    if (!sorry) return map
    map[sorry.id] = sorry.declaration_name
    for (const c of sorry.children) map[c.id] = c.declaration_name
    for (const p of sorry.parent_chain) map[p.id] = p.declaration_name
    return map
  }, [sorry])

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
        <ErrorBanner message="Failed to load sorry." onRetry={() => mutate()} />
      </Layout>
    )
  }

  if (!sorry) {
    return (
      <Layout>
        <div className="py-12 text-center">
          <h1 className="text-xl font-bold text-gray-900">Sorry not found</h1>
          <a href="/" className="mt-2 inline-block text-blue-600 hover:underline">Go home</a>
        </div>
      </Layout>
    )
  }

  const canSubmitFill = sorry.status === 'open' || sorry.status === 'decomposed'

  return (
    <Layout>
      {/* Breadcrumb */}
      <div className="mb-4">
        <BreadcrumbNav
          parent_chain={sorry.parent_chain}
          projectId={sorry.project_id}
          projectTitle={project?.title ?? 'Project'}
        />
      </div>

      {/* Declaration name + file path */}
      <div className="mb-2">
        <h1 className="font-mono text-lg font-bold text-gray-900">{sorry.declaration_name}</h1>
        <p className="text-xs text-gray-400">
          {sorry.file_path}
          {sorry.line !== undefined && `:${sorry.line}`}
          {sorry.sorry_index > 0 && <span> &middot; sorry #{sorry.sorry_index}</span>}
        </p>
      </div>

      {/* Status & Priority */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <StatusBadge status={sorry.status} />
        <PriorityBadge priority={sorry.priority} />
        {sorry.active_agents > 0 && (
          <span className="text-xs text-gray-500">{sorry.active_agents} agent{sorry.active_agents !== 1 ? 's' : ''} working</span>
        )}
      </div>

      {/* Goal State */}
      <div className="mb-4">
        <h2 className="mb-2 text-sm font-semibold text-gray-500">Goal State</h2>
        <LeanCodeBlock code={sorry.goal_state} />
      </div>

      {/* Local Context */}
      {sorry.local_context && (
        <div className="mb-4">
          <h2 className="mb-2 text-sm font-semibold text-gray-500">Local Context</h2>
          <LeanCodeBlock code={sorry.local_context} collapsible />
        </div>
      )}

      {/* Fill description */}
      {sorry.fill_description && (
        <div className="mb-4">
          <h2 className="mb-1 text-sm font-semibold text-gray-500">Fill Description</h2>
          <div className="text-sm text-gray-700"><MarkdownContent>{sorry.fill_description}</MarkdownContent></div>
        </div>
      )}

      {/* Winning fill */}
      {sorry.status === 'filled' && sorry.fill_tactics && (
        <div className="mb-6 rounded-lg border border-green-200 bg-green-50 p-4">
          <h3 className="mb-2 text-sm font-semibold text-green-800">
            Filled by {sorry.filled_by?.handle ?? 'unknown'}
          </h3>
          <LeanCodeBlock code={sorry.fill_tactics} collapsible />
        </div>
      )}

      {sorry.status === 'filled_externally' && (
        <div className="mb-6 rounded-lg border border-blue-200 bg-blue-50 p-4">
          <p className="text-sm text-blue-800">
            This sorry was filled externally (upstream or by direct commit).
          </p>
        </div>
      )}

      {/* Fill Form */}
      {canSubmitFill && (
        <div className="mb-6">
          <FillForm sorryId={sorry.id} onSuccess={() => mutate()} />
        </div>
      )}

      {/* Children (if decomposed) */}
      {sorry.children.length > 0 && (
        <div className="mb-6">
          <h2 className="mb-2 text-sm font-semibold text-gray-500">
            Sub-sorries ({sorry.children.length})
          </h2>
          <div className="space-y-2">
            {sorry.children.map((child) => (
              <SorryCard key={child.id} sorry={child} />
            ))}
          </div>
        </div>
      )}

      {/* Discussion (read-only) */}
      {sorry.comments && (
        <div className="mb-6">
          <h2 className="mb-3 text-sm font-semibold text-gray-500">Discussion</h2>
          <CommentThread thread={sorry.comments} references={refs} />
        </div>
      )}
    </Layout>
  )
}
