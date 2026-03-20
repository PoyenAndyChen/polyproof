import { useState } from 'react'
import Layout from '../components/layout/Layout'
import ConjectureList from '../components/conjecture/ConjectureList'
import SortTabs from '../components/ui/SortTabs'
import Pagination from '../components/ui/Pagination'
import { useConjectures } from '../hooks/index'
import { useFeedStore } from '../store/index'
import { DEFAULT_PAGE_SIZE } from '../lib/constants'
import { cn } from '../lib/utils'

const statusFilters = [
  { value: 'all' as const, label: 'All' },
  { value: 'open' as const, label: 'Open' },
  { value: 'proved' as const, label: 'Proved' },
  { value: 'disproved' as const, label: 'Disproved' },
]

export default function Home() {
  const { sort, statusFilter, page, setSort, setStatusFilter, setPage } = useFeedStore()
  const [searchQuery, setSearchQuery] = useState('')

  const params = {
    sort,
    status: statusFilter === 'all' ? undefined : statusFilter,
    q: searchQuery.trim() || undefined,
    limit: DEFAULT_PAGE_SIZE,
    offset: (page - 1) * DEFAULT_PAGE_SIZE,
  }

  const { data, error, isLoading, mutate } = useConjectures(params)
  const totalPages = data ? Math.ceil(data.total / DEFAULT_PAGE_SIZE) : 0

  return (
    <Layout sidebar>
      <div className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-xl font-bold text-gray-900">Conjectures</h1>
          <SortTabs value={sort} onChange={setSort} />
        </div>
        <div className="relative">
          <svg
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <input
            type="text"
            placeholder="Search conjectures..."
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value)
              setPage(1)
            }}
            className="w-full rounded-lg border border-gray-200 bg-white py-2 pl-9 pr-3 text-sm text-gray-900 placeholder-gray-400 outline-none focus:border-gray-400 focus:ring-1 focus:ring-gray-400"
          />
        </div>
        <div className="flex flex-wrap gap-1">
          {statusFilters.map((f) => (
            <button
              key={f.value}
              onClick={() => setStatusFilter(f.value)}
              className={cn(
                'rounded-full px-3 py-1 text-xs font-medium transition-colors',
                statusFilter === f.value
                  ? 'bg-gray-900 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200',
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
        <ConjectureList
          conjectures={data?.conjectures}
          isLoading={isLoading}
          error={error}
          onRetry={() => mutate()}
          emptyMessage={
            searchQuery.trim()
              ? 'No conjectures match your search.'
              : statusFilter !== 'all'
                ? 'No conjectures match your filters.'
                : 'No conjectures posted yet. Be the first!'
          }
          emptyActionLabel={searchQuery.trim() || statusFilter !== 'all' ? undefined : 'Post Conjecture'}
          emptyActionTo={searchQuery.trim() || statusFilter !== 'all' ? undefined : '/submit'}
        />
        <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
      </div>
    </Layout>
  )
}
