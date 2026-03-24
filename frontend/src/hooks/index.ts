import useSWR from 'swr'
import { api } from '../api/client'

export function useProjects() {
  return useSWR('projects', () => api.getProjects())
}

export function useProject(id: string) {
  return useSWR(['project', id], () => api.getProject(id))
}

export function useProjectSorries(projectId: string) {
  return useSWR(['project-sorries', projectId], () => api.getProjectSorries(projectId))
}

export function useProjectTree(projectId: string) {
  return useSWR(['project-tree', projectId], () => api.getProjectTree(projectId))
}

export function useProjectOverview(projectId: string) {
  return useSWR(['project-overview', projectId], () => api.getProjectOverview(projectId))
}

export function useSorry(id: string) {
  return useSWR(['sorry', id], () => api.getSorry(id))
}

export function useSorryComments(sorryId: string) {
  return useSWR(['sorry-comments', sorryId], () =>
    api.getSorryComments(sorryId),
  )
}

export function useProjectComments(projectId: string) {
  return useSWR(['project-comments', projectId], () => api.getProjectComments(projectId))
}

export function useAgent(agentId: string) {
  return useSWR(['agent', agentId], () => api.getAgent(agentId))
}

export function useLeaderboard() {
  return useSWR('leaderboard', () => api.getLeaderboard())
}

export function useProjectActivity(projectId: string, limit = 50) {
  return useSWR(['project-activity', projectId], () =>
    api.getProjectActivity(projectId, limit),
  )
}

export function useJob(jobId: string | null) {
  return useSWR(
    jobId ? ['job', jobId] : null,
    () => api.getJob(jobId!),
    {
      refreshInterval: (data) => {
        // Poll every 2s while job is in progress
        if (data && (data.status === 'queued' || data.status === 'compiling')) {
          return 2000
        }
        return 0
      },
    },
  )
}

export function useClaimInfo(token: string | null) {
  return useSWR(token ? ['claim-info', token] : null, () => api.getClaimInfo(token!))
}

export function useStats() {
  return useSWR('platform-stats', () => api.getStats())
}
