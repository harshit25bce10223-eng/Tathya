/**
 * Passport verification API client.
 * Public endpoints that don't require authentication.
 */

import { config } from "@/config"
import type { Passport, VerificationResult } from "./types"

const BASE = `${config.api.baseUrl}`

export async function getPassport(auditId: string): Promise<Passport> {
  const res = await fetch(`${BASE}/audits/${auditId}/passport`, {
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
  const res = await fetch(`${BASE}/verify/${token}`, {
    headers: { Accept: "application/json" },
  })
  if (!res.ok) {
    throw new Error(`Verification failed: ${res.status}`)
  }
  return res.json()
}
