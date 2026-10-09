import { z } from "zod"
import { apiFetch } from "./transport"

const citation = z.object({
  id: z.string(),
  document_id: z.string(),
  filename: z.string(),
  version_no: z.number(),
  text_hash: z.string(),
  sentence_id: z.string(),
  quote: z.string(),
  start_offset: z.number(),
  end_offset: z.number(),
  score: z.number(),
})
const answer = z.object({
  status: z.enum([
    "answered",
    "insufficient_evidence",
    "generation_unavailable",
  ]),
  answer: z.string(),
  citations: z.array(citation),
  retrieval_mode: z.enum(["lexical", "hybrid"]),
})
export type RagAnswer = z.infer<typeof answer>
export async function askSources(
  auditId: string,
  question: string,
): Promise<RagAnswer> {
  return answer.parse(
    await apiFetch(`/audits/${encodeURIComponent(auditId)}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, top_k: 5 }),
    }),
  )
}
