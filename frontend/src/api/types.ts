/**
 * TATHYA (तथ्य) API & DOMAIN CONTRACT TYPES
 * Centralized strictly typed definitions for all frontend models.
 */

export type SeverityLevel =
  | "CRITICAL"
  | "HIGH"
  | "MEDIUM"
  | "LOW"
  | "INFORMATIONAL"
export type MaterialityLevel = "MATERIAL" | "HIGH" | "MODERATE" | "LOW"
export type ClaimVerificationStatus =
  | "SUPPORTED"
  | "CONTRADICTED"
  | "UNSUPPORTED"
  | "UNCERTAIN"
export type AuditStatus =
  | "QUEUED"
  | "PROCESSING"
  | "COMPLETED"
  | "FAILED"
  | "REVIEW REQUIRED"
  | "VERIFIED"
  | "TAMPER DETECTED"

export type FlagStatus = "PENDING" | "ACCEPTED" | "DISMISSED" | "FIXED"

export interface SourceDocument {
  id: string
  name: string
  type: string
  sizeBytes: number
  uploadedAt: string
  authority: "LATEST_APPROVED" | "SIGNED_EXECUTED" | "SUPERSEDED" | "DRAFT"
  authorityLabel: string
  freshnessDate: string
  version: string
  hash: string
}

export interface GroundTruthEvidence {
  sourceId: string
  sourceName: string
  authority: string
  freshnessDate: string
  quote: string
  location: string // e.g. "Section 4.2 · Page 18"
}

export interface CounterEvidence {
  sourceName: string
  quote: string
  location: string
}

export interface Claim {
  id: string
  claimNumber: number
  text: string
  category:
    | "COMMERCIAL_VALUE"
    | "DELIVERY_DATE"
    | "SLA_GUARANTEE"
    | "INDEMNITY"
    | "PII_SECURITY"
    | "COMPLIANCE"
  status: ClaimVerificationStatus
  documentOffset?: {
    page: number
    paragraph: number
    startChar: number
    endChar: number
  }
  expectedTruth?: string
  variance?: string
}

export interface Flag {
  id: string
  auditId: string
  claimId: string
  type: string
  severity: SeverityLevel
  materiality: MaterialityLevel
  claim: string
  reason: string
  evidence: GroundTruthEvidence
  counterEvidence?: CounterEvidence
  suggestedFix: string
  whatToCheck: string
  status: FlagStatus
  reviewerNote?: string
  impactScore: number // point deduction e.g. -28
}

export interface WhatToCheckItem {
  id: string
  order: number
  title: string
  severity: SeverityLevel
  materiality: MaterialityLevel
  flagId: string
  summary: string
  actionRequired: string
}

export interface TrustWaterfallStep {
  name: string
  deduction: number
  scoreAfter: number
  description: string
  severity: SeverityLevel | "NEUTRAL"
}

export interface Audit {
  id: string
  title: string
  documentName: string
  documentType:
    | "Procurement Contract"
    | "Master Services Agreement"
    | "Financial Report"
    | "Technical Spec"
    | "Compliance Filing"
  language: string
  uploadedAt: string
  updatedAt: string
  status: AuditStatus
  priority: SeverityLevel
  trustScore: number
  initialScore: number
  riskBand: "High Risk" | "Review Needed" | "Trustworthy"
  findingsCount: number
  aiDocument: {
    name: string
    size: string
    hash: string
    pageCount: number
    rawText: string
  }
  sourceDocuments: SourceDocument[]
  flags: Flag[]
  claims: Claim[]
  whatToCheck: WhatToCheckItem[]
  waterfall: TrustWaterfallStep[]
  passportToken?: string
}

export interface Decision {
  flagId: string
  action: "ACCEPT" | "DISMISS" | "FIX"
  note?: string
  reviewedBy: string
  timestamp: string
}

export interface Passport {
  token: string
  auditId: string
  documentName: string
  documentHash: string
  chainHead: string
  signature: string
  signedBy: string
  signedAt: string
  trustScore: number
  status: "VERIFIED" | "REVOKED" | "TAMPER_DETECTED"
  totalClaimsChecked: number
  verifiedClaimsCount: number
  unresolvedFlagsCount: number
}

export interface VerificationResult {
  valid: boolean
  passport: Passport
  verifiedAt: string
  verifierNode: string
  auditTrail: {
    step: string
    status: "PASS" | "WARN" | "FAIL"
    detail: string
  }[]
}
