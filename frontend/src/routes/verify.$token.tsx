import { apiFetch } from "@/api/transport"
import { useQuery } from "@tanstack/react-query"
import { createFileRoute, Link } from "@tanstack/react-router"
import { z } from "zod"
import { QueryState, StatusPill } from "@/components/Audits/shared"
import { Logo } from "@/components/Common/Logo"

const schema = z.object({
  found: z.boolean(),
  status: z.string(),
  trust_score: z.number().min(0).max(100),
  score_status: z.string().default("insufficient_verification"),
  document_count: z.number().int().nonnegative(),
  document_hash: z.string(),
  issued_at: z.string().nullable(),
  signature_valid: z.boolean().nullable(),
  chain: z
    .object({
      ok: z.boolean(),
      reason: z.string(),
      entry_count: z.number().int().nonnegative(),
    })
    .nullable(),
  detail: z.string().nullable().optional(),
})
export const Route = createFileRoute("/verify/$token")({
  component: VerifyPage,
  head: () => ({ meta: [{ title: "Verify passport - Tathya" }] }),
})
function VerifyPage() {
  const { token } = Route.useParams()
  const result = useQuery({
    queryKey: ["verify", token],
    retry: 1,
    queryFn: async () => {
      const response = await apiFetch(`/verify/${encodeURIComponent(token)}`, {}, false)
      if (!response.ok)
        throw new Error(
          response.status === 404
            ? "This passport was not found. Check the verification link."
            : "Verification is unavailable. Please try again.",
        )
      const parsed = schema.safeParse(await response.json())
      if (!parsed.success)
        throw new Error("The verification service returned incomplete data.")
      return parsed.data
    },
  })
  const data = result.data
  return (
    <main className="public-verifier">
      <header>
        <Logo />
        <Link to="/login" className="back-link">
          Sign in
        </Link>
      </header>
      <div className="product-page">
        <div className="product-heading">
          <div>
            <span className="eyebrow">PUBLIC PASSPORT VERIFICATION</span>
            <h1>Trust, with a paper trail.</h1>
            <p>
              Check the issued score, document fingerprint and integrity proof.
            </p>
          </div>
        </div>
        <QueryState
          loading={result.isPending}
          error={result.error}
          retry={() => result.refetch()}
        />
        {data &&
          (data.found ? (
            <>
              <section className="product-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Document passport</h2>
                    <p>
                      {data.issued_at
                        ? `${new Intl.DateTimeFormat("en-IN", {
                            dateStyle: "medium",
                            timeStyle: "short",
                            timeZone: "Asia/Kolkata",
                          }).format(new Date(data.issued_at))}`
                        : "Issue time unavailable"}
                    </p>
                  </div>
                  <StatusPill status={data.status} />
                </div>
                <div className="verification-score">
                  <strong>{data.score_status === "insufficient_verification" ? "Not assessed" : data.trust_score}</strong>
                  <span>/ 100 · Published trust score</span>
                </div>
                <div className="policy-grid">
                  <article>
                    <h3>Signature</h3>
                    <StatusPill
                      status={
                        data.signature_valid === null
                          ? "not available"
                          : data.signature_valid
                            ? "verified"
                            : "failed"
                      }
                    />
                  </article>
                  <article>
                    <h3>Audit chain</h3>
                    <StatusPill
                      status={
                        !data.chain
                          ? "not available"
                          : data.chain.ok
                            ? "verified"
                            : "failed"
                      }
                    />
                    <p>
                      {data.chain?.reason}{" "}
                      {data.chain
                        ? `${data.chain.entry_count} entries checked.`
                        : ""}
                    </p>
                  </article>
                </div>
                <article className="source-record">
                  <div>
                    <h3>{data.document_count} documents covered</h3>
                    <p>Combined document fingerprint</p>
                  </div>
                  <dl>
                    <dt>Hash</dt>
                    <dd>{data.document_hash || "Not available"}</dd>
                  </dl>
                </article>
              </section>
              <aside className="control-note">
                <p>
                  Integrity checks confirm whether this issued record validates.
                  Read its score and status together; a valid signature does not
                  guarantee every underlying claim is correct.
                </p>
              </aside>
            </>
          ) : (
            <section className="product-panel panel-state">
              <h2>Passport not found</h2>
              <p>
                {data.detail ||
                  "Ask the document owner for the correct verification link."}
              </p>
            </section>
          ))}
      </div>
    </main>
  )
}
