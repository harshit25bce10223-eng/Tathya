/**
 * Tathya Passport API client.
 *
 * Deliberately kept as a NEW file alongside the concurrent session's audits.ts
 * to avoid overwriting that file.
 */
import { API_V1 } from "../config";

// ---------------------------------------------------------------------------
// Types (mirrors backend PassportPublic schema)
// ---------------------------------------------------------------------------

export interface Passport {
  id: string;
  audit_id: string;
  verify_token: string;
  document_hash: string;
  chain_head: string;
  signature: string;
  trust_score: number;
  status: string;
  issued_at: string | null;
  created_at: string | null;
}

export interface PassportVerifyResult {
  valid: boolean;
  passport: Passport | null;
  audit_id: string | null;
  message: string;
}

// ---------------------------------------------------------------------------
// API calls
// ---------------------------------------------------------------------------

/**
 * Fetch a passport by its audit_id (requires auth token).
 */
export async function getPassport(
  auditId: string,
  token: string
): Promise<Passport> {
  const res = await fetch(`${API_V1}/audits/${auditId}/passport`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail ?? `getPassport failed: ${res.status}`);
  }
  return res.json() as Promise<Passport>;
}

/**
 * Publicly verify a passport by its short verify_token.
 * No auth required — this is the public QR scan endpoint.
 */
export async function verifyPassport(
  verifyToken: string
): Promise<PassportVerifyResult> {
  const res = await fetch(`${API_V1}/verify/${verifyToken}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err?.detail ?? `verifyPassport failed: ${res.status}`);
  }
  return res.json() as Promise<PassportVerifyResult>;
}
