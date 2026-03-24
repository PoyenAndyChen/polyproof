import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { truncate } from '../../lib/utils'
import { ROUTES } from '../../lib/constants'
import type { SorrySummary } from '../../types'

interface BreadcrumbNavProps {
  parent_chain: SorrySummary[]
  projectId: string
  projectTitle: string
}

export default function BreadcrumbNav({ parent_chain, projectId, projectTitle }: BreadcrumbNavProps) {
  return (
    <nav className="flex flex-wrap items-center gap-1 text-sm text-gray-500">
      <Link to={ROUTES.PROJECT(projectId)} className="hover:text-gray-900">
        {truncate(projectTitle, 30)}
      </Link>
      {parent_chain.map((ancestor) => (
        <span key={ancestor.id} className="flex items-center gap-1">
          <ChevronRight className="h-3 w-3" />
          <Link to={ROUTES.SORRY(ancestor.id)} className="font-mono hover:text-gray-900">
            {truncate(ancestor.declaration_name, 30)}
          </Link>
        </span>
      ))}
    </nav>
  )
}
