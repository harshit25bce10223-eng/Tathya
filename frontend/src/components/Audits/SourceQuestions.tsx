import { useMutation } from "@tanstack/react-query"
import { type FormEvent, useState } from "react"
import { askSources } from "@/api/rag"

export function SourceQuestions({ auditId }: { auditId: string }) {
  const [question, setQuestion] = useState("")
  const ask = useMutation({
    mutationFn: (text: string) => askSources(auditId, text),
  })
  function submit(event: FormEvent) {
    event.preventDefault()
    if (question.trim().length >= 3 && !ask.isPending)
      ask.mutate(question.trim())
  }
  return (
    <section className="product-panel" aria-labelledby="source-questions-title">
      <h2 id="source-questions-title">Ask your sources</h2>
      <p>
        Ask a question about this audit’s current source documents. Answers
        include the source excerpts they use.
      </p>
      <form onSubmit={submit} className="grid gap-3 mt-4">
        <label htmlFor="source-question">Your question</label>
        <textarea
          id="source-question"
          disabled={ask.isPending}
          value={question}
          maxLength={2000}
          rows={3}
          className="w-full rounded-md border border-input bg-background p-3 text-foreground"
          placeholder="What warranty period do the approved sources specify?"
          onChange={(event) => {
            setQuestion(event.target.value)
            if (!ask.isPending) ask.reset()
          }}
        />
        <button
          type="submit"
          className="primary-button"
          disabled={ask.isPending || question.trim().length < 3}
        >
          {ask.isPending ? "Checking sources…" : "Ask sources"}
        </button>
      </form>
      {ask.error && (
        <p className="form-error" role="alert">
          {ask.error.message}
        </p>
      )}
      {ask.data && (
        <div className="mt-4" role="status" aria-live="polite">
          <p className="whitespace-pre-wrap">{ask.data.answer}</p>
          {ask.data.citations.map((source) => (
            <details key={source.id} className="mt-3">
              <summary>
                [{source.id}] {source.filename} · Version {source.version_no}
              </summary>
              <blockquote className="mt-2 border-l-2 pl-3 whitespace-pre-wrap">
                {source.quote}
              </blockquote>
              <p className="text-sm text-muted-foreground">
                Characters {source.start_offset}–{source.end_offset}
              </p>
            </details>
          ))}
          <p className="text-sm text-muted-foreground mt-3">
            Check the source excerpts before relying on an answer.
          </p>
        </div>
      )}
    </section>
  )
}
