import { create } from 'zustand'
import type { ConjectureStatus } from '../types'

interface UIStore {
  selectedNodeId: string | null
  treeCollapsed: Set<string>
  highlightCritical: boolean
  statusFilter: Set<ConjectureStatus>
  setSelectedNode: (id: string | null) => void
  toggleCollapse: (id: string) => void
  setHighlightCritical: (on: boolean) => void
  toggleStatusFilter: (status: ConjectureStatus) => void
  resetTreeState: () => void
}

export const useUIStore = create<UIStore>()((set) => ({
  selectedNodeId: null,
  treeCollapsed: new Set<string>(),
  highlightCritical: false,
  statusFilter: new Set<ConjectureStatus>(),

  setSelectedNode: (id) => set({ selectedNodeId: id }),

  toggleCollapse: (id) =>
    set((state) => {
      const next = new Set(state.treeCollapsed)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return { treeCollapsed: next }
    }),

  setHighlightCritical: (on) => set({ highlightCritical: on }),

  toggleStatusFilter: (status) =>
    set((state) => {
      const next = new Set(state.statusFilter)
      if (next.has(status)) {
        next.delete(status)
      } else {
        next.add(status)
      }
      return { statusFilter: next }
    }),

  resetTreeState: () =>
    set({
      selectedNodeId: null,
      treeCollapsed: new Set<string>(),
      highlightCritical: false,
      statusFilter: new Set<ConjectureStatus>(),
    }),
}))
