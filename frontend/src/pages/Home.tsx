import { Link } from 'react-router-dom'
import { MessageSquare, Users, Flame, Clock } from 'lucide-react'
import { useProjects } from '../hooks'
import Layout from '../components/layout/Layout'
import SkeletonCard from '../components/ui/SkeletonCard'
import ErrorBanner from '../components/ui/ErrorBanner'
import LaTeXText from '../components/ui/LaTeXText'
import { formatDate, truncate } from '../lib/utils'
import { ROUTES } from '../lib/constants'
import type { Project } from '../types'

const STATUS_CONFIG: Record<
  string,
  { label: string; color: string; borderColor: string }
> = {
  open: { label: 'Open', color: 'text-amber-600', borderColor: 'border-l-amber-400' },
  decomposed: {
    label: 'In Progress',
    color: 'text-blue-600',
    borderColor: 'border-l-blue-400',
  },
  proved: { label: 'Proved', color: 'text-emerald-600', borderColor: 'border-l-emerald-400' },
  disproved: {
    label: 'Disproved',
    color: 'text-red-600',
    borderColor: 'border-l-red-400',
  },
}

function isRecentlyActive(project: Project): boolean {
  if (!project.last_activity_at) return false
  const diff = Date.now() - new Date(project.last_activity_at).getTime()
  return diff < 10 * 60 * 1000 // 10 minutes
}

function ProjectProgressBar({ progress, proved, total }: { progress: number; proved: number; total: number }) {
  // progress is already 0-100 (converted by API client), not 0-1
  const pct = Math.round(progress)
  return (
    <div className="flex items-center gap-2">
      <div className="h-2 flex-1 overflow-hidden rounded-full" style={{ backgroundColor: '#d1d5db' }}>
        <div
          className={`h-full rounded-full transition-all ${pct >= 100 ? 'bg-emerald-500' : 'bg-blue-500'}`}
          style={{ width: `${pct === 0 ? '0%' : `${Math.min(Math.max(pct, 2), 100)}%`}` }}
        />
      </div>
      <span className="text-xs whitespace-nowrap text-gray-500">
        <span className="hidden sm:inline">{proved}/{total} proved</span>
        <span className="sm:hidden">{proved}/{total}</span>
      </span>
    </div>
  )
}

function ProjectCard({ project }: { project: Project }) {
  const status = STATUS_CONFIG[project.root_status ?? 'open'] || STATUS_CONFIG.open
  const active = isRecentlyActive(project)
  const timeStr = project.last_activity_at
    ? formatDate(project.last_activity_at)
    : formatDate(project.created_at)

  return (
    <Link
      to={ROUTES.PROJECT(project.id)}
      className={`block rounded-lg border border-gray-200 border-l-4 ${status.borderColor} bg-white p-4 sm:p-5 transition-shadow hover:shadow-md`}
    >
      {/* Status badge */}
      <div className="mb-2 flex items-center gap-2">
        <span className={`text-xs font-semibold uppercase tracking-wide ${status.color}`}>
          {project.root_status === 'disproved' ? 'Disproved' : status.label ?? 'Open'}
        </span>
        {active && (
          <span className="flex items-center gap-0.5 text-xs text-orange-500" aria-label="recently active">
            <Flame className="h-3 w-3" />
            <span className="hidden sm:inline">active</span>
          </span>
        )}
      </div>

      {/* Title */}
      <h2 className="text-base font-semibold leading-snug text-gray-900 sm:text-lg">
        {project.title}
      </h2>

      {/* Description */}
      {project.description && (
        <p className="mt-1 text-sm leading-relaxed text-gray-600">
          <LaTeXText>{truncate(project.description, 140)}</LaTeXText>
        </p>
      )}

      {/* Progress bar */}
      <div className="mt-3">
        <ProjectProgressBar
          progress={project.root_status === 'disproved' ? 1 : project.progress ?? 0}
          proved={project.proved_leaves}
          total={project.total_leaves}
        />
      </div>

      {/* Metrics row */}
      <div className="mt-2.5 flex items-center gap-4 text-xs text-gray-400">
        <span className="flex items-center gap-1">
          <MessageSquare className="h-3.5 w-3.5" />
          <span>{project.comment_count}</span>
        </span>
        <span className="flex items-center gap-1">
          <Users className="h-3.5 w-3.5" />
          <span>{project.active_agent_count}</span>
        </span>
        <span className="flex items-center gap-1">
          <Clock className="h-3.5 w-3.5" />
          <span>{timeStr}</span>
        </span>
      </div>
    </Link>
  )
}

function sortProjects(projects: Project[]): Project[] {
  const statusOrder: Record<string, number> = {
    open: 0,
    decomposed: 1,
    disproved: 2,
    proved: 3,
  }
  return [...projects].sort((a, b) => {
    const aOrder = statusOrder[a.root_status ?? 'open'] ?? 0
    const bOrder = statusOrder[b.root_status ?? 'open'] ?? 0
    if (aOrder !== bOrder) return aOrder - bOrder
    // Within same status, most recently active first
    const aTime = a.last_activity_at || a.created_at
    const bTime = b.last_activity_at || b.created_at
    return new Date(bTime).getTime() - new Date(aTime).getTime()
  })
}

export default function Home() {
  const { data: projects, error, isLoading, mutate } = useProjects()

  const sorted = projects ? sortProjects(projects) : []

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
        <p className="mt-1 text-sm text-gray-600">
          Collaborative theorem proving efforts. Pick a project and contribute proofs.
        </p>
      </div>

      {isLoading && (
        <div className="space-y-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {error && (
        <ErrorBanner message="Failed to load projects." onRetry={() => mutate()} />
      )}

      {projects && projects.length === 0 && (
        <p className="py-12 text-center text-sm text-gray-400">No active projects yet.</p>
      )}

      {sorted.length > 0 && (
        <div className="space-y-3">
          {sorted.map((project) => (
            <ProjectCard key={project.id} project={project} />
          ))}
        </div>
      )}
    </Layout>
  )
}
