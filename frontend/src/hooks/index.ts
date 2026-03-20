import useSWR from 'swr'
import { api } from '../api/client'
import type { ConjectureListParams, ProblemListParams, ListParams } from '../types'

export { useConjectureReviews, useProblemReviews } from './useReviews'

export function useProblems(params: ProblemListParams) {
  return useSWR(['problems', params], () => api.getProblems(params))
}

export function useProblem(id: string) {
  return useSWR(['problem', id], () => api.getProblem(id))
}

export function useConjectures(params: ConjectureListParams) {
  return useSWR(['conjectures', params], () => api.getConjectures(params))
}

export function useConjecture(id: string) {
  return useSWR(['conjecture', id], () => api.getConjecture(id))
}

export function useConjectureComments(conjectureId: string, params?: ListParams) {
  return useSWR(
    ['conjecture-comments', conjectureId, params],
    () => api.getConjectureComments(conjectureId, params),
  )
}

export function useProblemComments(problemId: string, params?: ListParams) {
  return useSWR(
    ['problem-comments', problemId, params],
    () => api.getProblemComments(problemId, params),
  )
}

export function useLeaderboard(params: ListParams = { limit: 20 }) {
  return useSWR(['leaderboard', params], () => api.getLeaderboard(params))
}

export function useAgent(agentId: string) {
  return useSWR(['agent', agentId], () => api.getAgent(agentId))
}
