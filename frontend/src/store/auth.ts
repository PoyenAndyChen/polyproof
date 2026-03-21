import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { api } from '../api/client'
import type { Agent } from '../types'

interface AuthStore {
  apiKey: string | null
  agent: Agent | null
  isHydrating: boolean
  login: (apiKey: string) => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      apiKey: null,
      agent: null,
      isHydrating: true,

      login: async (apiKey: string) => {
        api.setApiKey(apiKey)
        const agent = await api.getMe()
        set({ apiKey, agent })
      },

      logout: () => {
        api.setApiKey(null)
        set({ apiKey: null, agent: null })
      },

      refresh: async () => {
        try {
          const agent = await api.getMe()
          set({ agent })
        } catch {
          api.setApiKey(null)
          set({ apiKey: null, agent: null })
        }
      },
    }),
    {
      name: 'polyproof-auth',
      partialize: (state) => ({ apiKey: state.apiKey }),
      onRehydrateStorage: () => (state) => {
        if (state?.apiKey) {
          api.setApiKey(state.apiKey)
          state.refresh().finally(() => {
            useAuthStore.setState({ isHydrating: false })
          })
        } else {
          useAuthStore.setState({ isHydrating: false })
        }
      },
    },
  ),
)

// Sync API key to the client whenever auth store changes
useAuthStore.subscribe((state) => {
  api.setApiKey(state.apiKey)
})
