import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'
import type { ApiTreeNode, TreeNode } from '../types'

/** Merge Tailwind classes with clsx */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Format an ISO date string as a relative time */
export function formatDate(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSeconds = Math.floor(diffMs / 1000)
  const diffMinutes = Math.floor(diffSeconds / 60)
  const diffHours = Math.floor(diffMinutes / 60)
  const diffDays = Math.floor(diffHours / 24)

  if (diffSeconds < 60) return 'just now'
  if (diffMinutes < 60) return `${diffMinutes}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 30) return `${diffDays}d ago`

  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  })
}

/** Truncate a string to a maximum length, adding ellipsis if needed */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str
  return str.slice(0, maxLength - 1) + '\u2026'
}

/**
 * Flatten nested API tree response into a flat TreeNode array for react-flow.
 * Recursively walks the nested structure and adds parent_id references.
 */
export function flattenTree(
  root: ApiTreeNode,
  projectId: string,
  parentId: string | null = null,
): TreeNode[] {
  const provedChildCount = root.children.filter((c) => c.status === 'proved').length

  const node: TreeNode = {
    id: root.id,
    project_id: projectId,
    parent_id: parentId,
    lean_statement: root.lean_statement,
    description: root.description,
    status: root.status,
    priority: root.priority,
    comment_count: root.comment_count,
    child_count: root.children.length,
    proved_child_count: provedChildCount,
  }

  const result: TreeNode[] = [node]

  for (const child of root.children) {
    result.push(...flattenTree(child, projectId, root.id))
  }

  return result
}
