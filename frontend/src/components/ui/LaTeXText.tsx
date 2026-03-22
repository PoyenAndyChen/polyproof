import 'katex/dist/katex.min.css'
import katex from 'katex'

/**
 * Renders plain text with inline LaTeX.
 * Supports \(...\) and $...$ for inline math, \[...\] and $$...$$ for display math.
 */
export default function LaTeXText({ children }: { children: string }) {
  if (!children) return null

  // Split text into segments: plain text and LaTeX expressions
  // Order matters: check \[...\] and $$...$$ (display) before \(...\) and $...$ (inline)
  const parts: Array<{ type: 'text' | 'inline' | 'display'; content: string }> = []
  let remaining = children

  const patterns = [
    { regex: /\\\[([\s\S]*?)\\\]/g, type: 'display' as const },
    { regex: /\$\$([\s\S]*?)\$\$/g, type: 'display' as const },
    { regex: /\\\(([\s\S]*?)\\\)/g, type: 'inline' as const },
    { regex: /\$([^\$\n]+?)\$/g, type: 'inline' as const },
  ]

  // Find all matches across all patterns
  const allMatches: Array<{ start: number; end: number; content: string; type: 'inline' | 'display' }> = []
  for (const { regex, type } of patterns) {
    const re = new RegExp(regex.source, regex.flags)
    let match
    while ((match = re.exec(remaining)) !== null) {
      allMatches.push({
        start: match.index,
        end: match.index + match[0].length,
        content: match[1],
        type,
      })
    }
  }

  // Sort by position and remove overlaps
  allMatches.sort((a, b) => a.start - b.start)
  const filtered: typeof allMatches = []
  let lastEnd = 0
  for (const m of allMatches) {
    if (m.start >= lastEnd) {
      filtered.push(m)
      lastEnd = m.end
    }
  }

  // Build parts
  let cursor = 0
  for (const m of filtered) {
    if (m.start > cursor) {
      parts.push({ type: 'text', content: remaining.slice(cursor, m.start) })
    }
    parts.push({ type: m.type, content: m.content })
    cursor = m.end
  }
  if (cursor < remaining.length) {
    parts.push({ type: 'text', content: remaining.slice(cursor) })
  }

  // If no LaTeX found, return plain text
  if (filtered.length === 0) {
    return <>{children}</>
  }

  return (
    <>
      {parts.map((part, i) => {
        if (part.type === 'text') {
          return <span key={i}>{part.content}</span>
        }
        try {
          const html = katex.renderToString(part.content, {
            displayMode: part.type === 'display',
            throwOnError: false,
            trust: false,
            strict: false,
          })
          return (
            <span
              key={i}
              dangerouslySetInnerHTML={{ __html: html }}
            />
          )
        } catch {
          return <code key={i}>{part.content}</code>
        }
      })}
    </>
  )
}
