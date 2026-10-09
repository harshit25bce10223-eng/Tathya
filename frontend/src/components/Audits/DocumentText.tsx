import type { AuditFlag } from "@/api/audits"

export function DocumentText({text, flags}: {text: string; flags: AuditFlag[]}) {
  const spans = flags.flatMap(flag => {
    try {
      const location = JSON.parse(flag.location_json)
      const start = location.norm_start ?? location.start
      const end = location.norm_end ?? location.end
      if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end <= start || end > text.length) return []
      return [{start, end, reason: flag.reason}]
    } catch { return [] }
  }).sort((a, b) => a.start - b.start)
  const pieces = []
  let cursor = 0
  for (const span of spans) {
    if (span.start < cursor) continue
    pieces.push(text.slice(cursor, span.start))
    pieces.push(<mark key={`${span.start}:${span.end}`} title={span.reason}>{text.slice(span.start, span.end)}</mark>)
    cursor = span.end
  }
  pieces.push(text.slice(cursor))
  return <pre className="document-preview" aria-label="Document text with flagged passages">{pieces}</pre>
}
