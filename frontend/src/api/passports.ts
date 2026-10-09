import { apiFetch } from "./transport"
/**
 * Passport verification API client.
 * Public endpoints that don't require authentication.
 */

import type { Passport, VerificationResult } from "./types"


export async function getPassport(auditId: string): Promise<Passport> {
  const res = await apiFetch(`/audits/${encodeURIComponent(auditId)}/passport`, {
    headers: { Accept: "application/json" },
  })
  if (!res.ok) {
    throw new Error(`Failed to fetch passport: ${res.status}`)
  }
  return res.json()
}

export async function verifyPassport(
  token: string,
): Promise<VerificationResult> {
  const res = await apiFetch(`/verify/${encodeURIComponent(token)}`, {
    headers: { Accept: "application/json" },
  })
  if (!res.ok) {
    throw new Error(`Verification failed: ${res.status}`)
  }
  return res.json()
}
