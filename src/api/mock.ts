import { Audit, Passport } from './types';

export const mockAudits: Audit[] = [
  {
    id: 'AUD-1042',
    title: 'Enterprise Cloud Procurement & Master Services Agreement',
    documentName: 'AI_Procurement_Summary_v3.pdf',
    documentType: 'Procurement Contract',
    language: 'English (US / IN)',
    uploadedAt: '2026-10-08T17:42:00Z',
    updatedAt: '2026-10-08T19:15:00Z',
    status: 'REVIEW REQUIRED',
    priority: 'CRITICAL',
    trustScore: 42,
    initialScore: 100,
    riskBand: 'High Risk',
    findingsCount: 4,
    aiDocument: {
      name: 'AI_Procurement_Summary_v3.pdf',
      size: '2.4 MB',
      hash: 'sha256:7b91c84f39ae62463e271917f8a3d5b74100cde19ef652a9f4c391219b188c0a',
      pageCount: 14,
      rawText: `MASTER SERVICES AGREEMENT SUMMARY (AI SYNTHESIS)

1. COMMERCIAL TERMS & FEES
The total consideration payable under this Statement of Work is ₹24,800,000 (INR Twenty-Four Million Eight Hundred Thousand) net of applicable GST, disbursed across 24 equal monthly milestone tranches of ₹1,033,333. The initial mobilization fee shall be transferred within 15 calendar days of signature.

2. TIMELINE & MILESTONES
The vendor commits to commence work on 01 November 2026. The primary Stage 1 core architecture delivery date is firmly committed for 22 Dec 2026. Subsequent deployment sprints will execute bi-weekly through Q4 2027.

3. SERVICE LEVEL AGREEMENT (SLA) & AVAILABILITY
The vendor explicitly guarantees 99.99% monthly system uptime across all production cloud availability zones. In the event of downtime exceeding 4.3 minutes per calendar month, customer receives a 15% billing credit.

4. DATA SECURITY & PRIVACY CONTROLS
To facilitate rapid onboarding and staging environment verification, customer user directory records and preliminary payment identifiers will be replicated to an internal unencrypted staging bucket for 30 business days before tokenization.

5. TERMINATION & INDEMNIFICATION
Either party may terminate for convenience with 30 days written notice. Indemnification liability for intellectual property infringement is capped at 1.5x total contract value.`
    },
    sourceDocuments: [
      {
        id: 'SRC-001',
        name: 'Approved_Purchase_Order_PO_v2_Final.pdf',
        type: 'Purchase Order',
        sizeBytes: 1840000,
        uploadedAt: '2026-10-08T17:45:00Z',
        authority: 'LATEST_APPROVED',
        authorityLabel: 'Latest Approved PO v2',
        freshnessDate: '22 Sep 2026',
        version: 'v2.4',
        hash: 'sha256:4a123f8b91c0e3a45c789d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a'
      },
      {
        id: 'SRC-002',
        name: 'Master_Execution_Schedule_Rev4.xlsx',
        type: 'Project Plan',
        sizeBytes: 945000,
        uploadedAt: '2026-10-08T17:45:00Z',
        authority: 'SIGNED_EXECUTED',
        authorityLabel: 'Signed Master Schedule',
        freshnessDate: '18 Sep 2026',
        version: 'v4.0',
        hash: 'sha256:b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8'
      },
      {
        id: 'SRC-003',
        name: 'Enterprise_Cloud_SLA_Terms_v1.2.pdf',
        type: 'Legal Terms',
        sizeBytes: 1200000,
        uploadedAt: '2026-10-08T17:46:00Z',
        authority: 'LATEST_APPROVED',
        authorityLabel: 'Approved SLA Schedule',
        freshnessDate: '10 Aug 2026',
        version: 'v1.2',
        hash: 'sha256:9f8e7d6c5b4a3a2b1c0d9e8f7a6b5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b'
      },
      {
        id: 'SRC-004',
        name: 'Superseded_Procurement_Draft_v1.docx',
        type: 'Draft Document',
        sizeBytes: 650000,
        uploadedAt: '2026-10-08T17:46:00Z',
        authority: 'SUPERSEDED',
        authorityLabel: 'Superseded Draft v1 (Deprecated)',
        freshnessDate: '15 Jul 2026',
        version: 'v1.0',
        hash: 'sha256:112233445566778899aabbccddeeff00112233445566778899aabbccddeeff00'
      }
    ],
    claims: [
      {
        id: 'CLM-01',
        claimNumber: 1,
        text: 'Total consideration payable is ₹24,800,000 across 24 equal monthly milestones.',
        category: 'COMMERCIAL_VALUE',
        status: 'CONTRADICTED',
        expectedTruth: '₹20,640,000 (Commercial Cap in Approved PO v2)',
        variance: '+₹4,160,000 (+₹41.6L unauthorized excess)',
        documentOffset: { page: 1, paragraph: 1, startChar: 40, endChar: 110 }
      },
      {
        id: 'CLM-02',
        claimNumber: 2,
        text: 'The primary Stage 1 core architecture delivery date is firmly committed for 22 Dec 2026.',
        category: 'DELIVERY_DATE',
        status: 'CONTRADICTED',
        expectedTruth: '15 Nov 2026 (Stage 1 Strict Milestone)',
        variance: '+37 days unapproved delivery slippage',
        documentOffset: { page: 1, paragraph: 2, startChar: 70, endChar: 160 }
      },
      {
        id: 'CLM-03',
        claimNumber: 3,
        text: 'The vendor explicitly guarantees 99.99% monthly system uptime across all production cloud availability zones.',
        category: 'SLA_GUARANTEE',
        status: 'UNSUPPORTED',
        expectedTruth: '99.5% uptime commitment in approved SLA schedule',
        variance: 'AI hallucinated 4-nines availability (not agreed)',
        documentOffset: { page: 2, paragraph: 1, startChar: 30, endChar: 140 }
      },
      {
        id: 'CLM-04',
        claimNumber: 4,
        text: 'Customer user directory records and preliminary payment identifiers will be replicated to an internal unencrypted staging bucket.',
        category: 'PII_SECURITY',
        status: 'CONTRADICTED',
        expectedTruth: 'Clause 14.1 mandates 100% encryption-at-rest and tokenization before replication',
        variance: 'Severe regulatory breach (GDPR / DPDP Act 2023 violation)',
        documentOffset: { page: 2, paragraph: 2, startChar: 60, endChar: 190 }
      }
    ],
    flags: [
      {
        id: 'FLG-101',
        auditId: 'AUD-1042',
        claimId: 'CLM-01',
        type: 'Commercial Value Conflict',
        severity: 'CRITICAL',
        materiality: 'MATERIAL',
        claim: 'Total consideration payable is ₹24,800,000 across 24 equal monthly milestones.',
        reason: 'AI summary inflated commercial contract value by ₹41.6L (+20.15%). Approved PO v2 strictly caps liability at ₹20,640,000.',
        evidence: {
          sourceId: 'SRC-001',
          sourceName: 'Approved_Purchase_Order_PO_v2_Final.pdf',
          authority: '✓ Latest Approved (PO v2 · Finance Executed)',
          freshnessDate: '22 Sep 2026',
          quote: '"Clause 3.1: The total contract liability and maximum consideration shall not exceed ₹20,640,000 INR inclusive of mobilization."',
          location: 'Item 4 · Page 2'
        },
        counterEvidence: {
          sourceName: 'Superseded_Procurement_Draft_v1.docx',
          quote: '"Initial vendor proposal estimated optional add-on scope up to ₹24.8M before scope deselect."',
          location: 'Appendix B (Superseded Draft)'
        },
        suggestedFix: 'Replace ₹24,800,000 with the binding approved amount: ₹20,640,000.',
        whatToCheck: 'Verify latest approved commercial value against Finance PO v2',
        status: 'PENDING',
        impactScore: -28
      },
      {
        id: 'FLG-102',
        auditId: 'AUD-1042',
        claimId: 'CLM-02',
        type: 'Milestone Delivery Conflict',
        severity: 'HIGH',
        materiality: 'HIGH',
        claim: 'The primary Stage 1 core architecture delivery date is firmly committed for 22 Dec 2026.',
        reason: 'AI summary permits delivery on 22 Dec 2026, whereas signed Master Schedule demands completion by 15 Nov 2026 (a 37-day discrepancy).',
        evidence: {
          sourceId: 'SRC-002',
          sourceName: 'Master_Execution_Schedule_Rev4.xlsx',
          authority: '✓ Signed Master Schedule (Operations Approved)',
          freshnessDate: '18 Sep 2026',
          quote: '"Milestone M1 Deliverable: Core Cloud VPC Architecture signoff required no later than 15 Nov 2026."',
          location: 'Tab 1 · Row 24'
        },
        suggestedFix: 'Change Stage 1 completion date to 15 Nov 2026 as legally required in Schedule Rev4.',
        whatToCheck: 'Confirm contractual delivery date with Lead Architect schedule',
        status: 'PENDING',
        impactScore: -14
      },
      {
        id: 'FLG-103',
        auditId: 'AUD-1042',
        claimId: 'CLM-03',
        type: 'Unsupported SLA Commitment',
        severity: 'HIGH',
        materiality: 'MODERATE',
        claim: 'Vendor explicitly guarantees 99.99% monthly system uptime across all production zones.',
        reason: 'AI synthesized a 99.99% (Four Nines) availability tier. The vendor contract only warrants 99.5% (Two and a half Nines). Promising 99.99% creates unfulfillable client exposure.',
        evidence: {
          sourceId: 'SRC-003',
          sourceName: 'Enterprise_Cloud_SLA_Terms_v1.2.pdf',
          authority: '✓ Approved SLA Schedule v1.2',
          freshnessDate: '10 Aug 2026',
          quote: '"Section 2.2: Standard production service availability commitment is 99.5% uptime per billing cycle."',
          location: 'Section 2.2 · Page 4'
        },
        suggestedFix: 'Align SLA guarantee with standard contract tier: 99.5% monthly availability.',
        whatToCheck: 'Review unsupported uptime guarantee against SLA Terms v1.2',
        status: 'PENDING',
        impactScore: -10
      },
      {
        id: 'FLG-104',
        auditId: 'AUD-1042',
        claimId: 'CLM-04',
        type: 'Data Privacy & Security Contradiction',
        severity: 'CRITICAL',
        materiality: 'MATERIAL',
        claim: 'Replication of payment identifiers to an unencrypted staging bucket for 30 business days.',
        reason: 'Direct contradiction of corporate security policy and statutory data protection laws. PII must be encrypted-at-rest and tokenized before staging transit.',
        evidence: {
          sourceId: 'SRC-001',
          sourceName: 'Approved_Purchase_Order_PO_v2_Final.pdf',
          authority: '✓ Mandatory Security Addendum',
          freshnessDate: '22 Sep 2026',
          quote: '"Section 14.1: Customer PII or financial credentials shall NEVER be retained in unencrypted or non-tokenized data stores."',
          location: 'Security Addendum · Page 12'
        },
        suggestedFix: 'Remove unencrypted staging replication clause; replace with AES-256 tokenized pipeline requirement.',
        whatToCheck: 'Audit PII staging protocol and eliminate non-compliant staging storage',
        status: 'PENDING',
        impactScore: -6
      }
    ],
    whatToCheck: [
      {
        id: 'WTC-01',
        order: 1,
        title: 'Verify latest approved commercial value (PO v2 cap: ₹20,640,000)',
        severity: 'CRITICAL',
        materiality: 'MATERIAL',
        flagId: 'FLG-101',
        summary: 'Commercial conflict of ₹41.6L (+20.15% variance). AI text states ₹24.8M.',
        actionRequired: 'Inspect Purchase Order v2 Item 4 and verify Finance CFO signature.'
      },
      {
        id: 'WTC-02',
        order: 2,
        title: 'Confirm contractual delivery date (Target: 15 Nov 2026 vs AI: 22 Dec 2026)',
        severity: 'HIGH',
        materiality: 'HIGH',
        flagId: 'FLG-102',
        summary: '37-day milestone delay introduced by AI synthesis without change order.',
        actionRequired: 'Check Master Execution Schedule Rev4 Row 24.'
      },
      {
        id: 'WTC-03',
        order: 3,
        title: 'Review unsupported 99.99% uptime guarantee (Vendor cap: 99.5%)',
        severity: 'HIGH',
        materiality: 'MODERATE',
        flagId: 'FLG-103',
        summary: 'Risk of legal breach due to unwarranted four-nines SLA representation.',
        actionRequired: 'Validate Section 2.2 in SLA Terms v1.2.'
      },
      {
        id: 'WTC-04',
        order: 4,
        title: 'Remediate unencrypted PII staging exposure before legal sign-off',
        severity: 'CRITICAL',
        materiality: 'MATERIAL',
        flagId: 'FLG-104',
        summary: 'Security policy breach regarding unencrypted staging storage of user records.',
        actionRequired: 'Enforce Section 14.1 encryption and tokenization standards.'
      }
    ],
    waterfall: [
      {
        name: 'Initial Trust Baseline',
        deduction: 0,
        scoreAfter: 100,
        description: 'Unchecked document baseline state',
        severity: 'NEUTRAL'
      },
      {
        name: 'Commercial Value Conflict (₹41.6L)',
        deduction: -28,
        scoreAfter: 72,
        description: 'Critical materiality conflict with latest PO v2',
        severity: 'CRITICAL'
      },
      {
        name: 'Milestone Delivery Contradiction',
        deduction: -14,
        scoreAfter: 58,
        description: '37-day unauthorized milestone slippage',
        severity: 'HIGH'
      },
      {
        name: 'Unsupported SLA Commitment',
        deduction: -10,
        scoreAfter: 48,
        description: 'Unverified 99.99% availability hallucination',
        severity: 'HIGH'
      },
      {
        name: 'Data Privacy Violation',
        deduction: -6,
        scoreAfter: 42,
        description: 'Breach of Section 14.1 PII security standards',
        severity: 'CRITICAL'
      }
    ],
    passportToken: 'PASSPORT-88219-AUD1042-CRIT'
  },

  {
    id: 'AUD-1088',
    title: 'Cross-Border Supply Chain Vendor Indemnity Agreement',
    documentName: 'Vendor_Indemnity_Summary_v1.pdf',
    documentType: 'Master Services Agreement',
    language: 'English (UK)',
    uploadedAt: '2026-10-08T15:10:00Z',
    updatedAt: '2026-10-08T18:30:00Z',
    status: 'REVIEW REQUIRED',
    priority: 'HIGH',
    trustScore: 58,
    initialScore: 100,
    riskBand: 'Review Needed',
    findingsCount: 3,
    aiDocument: {
      name: 'Vendor_Indemnity_Summary_v1.pdf',
      size: '1.8 MB',
      hash: 'sha256:8899aabbccddeeff00112233445566778899aabbccddeeff0011223344556677',
      pageCount: 8,
      rawText: `SUPPLY CHAIN VENDOR AGREEMENT\n\n1. Indemnification liability is capped at £250,000 for all cargo losses.\n2. Governing law shall be Singapore International Arbitration Centre.\n3. Turnaround time for customs clearance disputes is 72 hours.`
    },
    sourceDocuments: [
      {
        id: 'SRC-010',
        name: 'Global_Logistics_Master_Executed_2026.pdf',
        type: 'Master Agreement',
        sizeBytes: 3100000,
        uploadedAt: '2026-10-08T15:12:00Z',
        authority: 'SIGNED_EXECUTED',
        authorityLabel: 'Signed Master Agreement',
        freshnessDate: '01 Aug 2026',
        version: 'v3.1',
        hash: 'sha256:1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
      }
    ],
    claims: [],
    flags: [
      {
        id: 'FLG-201',
        auditId: 'AUD-1088',
        claimId: 'CLM-201',
        type: 'Liability Cap Variance',
        severity: 'HIGH',
        materiality: 'HIGH',
        claim: 'Indemnification liability is capped at £250,000 for all cargo losses.',
        reason: 'Master Agreement stipulates unlimited liability for gross negligence cargo loss.',
        evidence: {
          sourceId: 'SRC-010',
          sourceName: 'Global_Logistics_Master_Executed_2026.pdf',
          authority: 'Signed Master Agreement',
          freshnessDate: '01 Aug 2026',
          quote: '"Section 12.4: Neither party shall cap indemnity for gross negligence or willful cargo damage."',
          location: 'Clause 12.4 · Page 19'
        },
        suggestedFix: 'Update summary to reflect uncapped liability for gross negligence.',
        whatToCheck: 'Verify Clause 12.4 with Chief Legal Counsel',
        status: 'PENDING',
        impactScore: -24
      }
    ],
    whatToCheck: [
      {
        id: 'WTC-201',
        order: 1,
        title: 'Verify Clause 12.4 uncapped liability for cargo loss',
        severity: 'HIGH',
        materiality: 'HIGH',
        flagId: 'FLG-201',
        summary: 'AI introduced £250k liability cap contrary to signed master agreement.',
        actionRequired: 'Verify Section 12.4 in Logistics Master Agreement.'
      }
    ],
    waterfall: [
      { name: 'Initial Trust Baseline', deduction: 0, scoreAfter: 100, description: 'Baseline', severity: 'NEUTRAL' },
      { name: 'Liability Cap Discrepancy', deduction: -24, scoreAfter: 76, description: 'Clause 12.4 conflict', severity: 'HIGH' },
      { name: 'Arbitration Jurisdiction Mismatch', deduction: -18, scoreAfter: 58, description: 'Seat of arbitration variance', severity: 'MEDIUM' }
    ]
  },

  {
    id: 'AUD-1104',
    title: 'Q3 Statutory Financial Health & Disclosure Filing',
    documentName: 'Q3_Financial_Audit_Report_Certified.pdf',
    documentType: 'Financial Report',
    language: 'English',
    uploadedAt: '2026-10-08T12:00:00Z',
    updatedAt: '2026-10-08T16:45:00Z',
    status: 'VERIFIED',
    priority: 'LOW',
    trustScore: 94,
    initialScore: 100,
    riskBand: 'Trustworthy',
    findingsCount: 0,
    aiDocument: {
      name: 'Q3_Financial_Audit_Report_Certified.pdf',
      size: '5.1 MB',
      hash: 'sha256:c0ffee123456789abcdef0123456789abcdef0123456789abcdef0123456789a',
      pageCount: 32,
      rawText: `Q3 STATUTORY FINANCIAL DISCLOSURE\n\nAll disclosures reconciled 100% against ERP ledgers and external bank statements.`
    },
    sourceDocuments: [
      {
        id: 'SRC-030',
        name: 'SAP_ERP_Ledger_Extract_Q3_Audited.xlsx',
        type: 'General Ledger',
        sizeBytes: 8200000,
        uploadedAt: '2026-10-08T12:05:00Z',
        authority: 'LATEST_APPROVED',
        authorityLabel: 'Audited General Ledger',
        freshnessDate: '05 Oct 2026',
        version: 'v1.0',
        hash: 'sha256:778899aabbccddeeff00112233445566778899aabbccddeeff00112233445566'
      }
    ],
    claims: [],
    flags: [],
    whatToCheck: [],
    waterfall: [
      { name: 'Initial Trust Baseline', deduction: 0, scoreAfter: 100, description: 'Baseline', severity: 'NEUTRAL' },
      { name: 'Minor Terminology Variance (Informational)', deduction: -6, scoreAfter: 94, description: 'GAAP/IFRS label alignment', severity: 'LOW' }
    ],
    passportToken: 'PASSPORT-94102-AUD1104-VERIFIED'
  },

  {
    id: 'AUD-1115',
    title: 'Healthcare System FHIR API Security Specification',
    documentName: 'HealthTech_FHIR_Compliance_v2.pdf',
    documentType: 'Technical Spec',
    language: 'English',
    uploadedAt: '2026-10-08T18:00:00Z',
    updatedAt: '2026-10-08T18:40:00Z',
    status: 'REVIEW REQUIRED',
    priority: 'HIGH',
    trustScore: 71,
    initialScore: 100,
    riskBand: 'Review Needed',
    findingsCount: 2,
    aiDocument: {
      name: 'HealthTech_FHIR_Compliance_v2.pdf',
      size: '3.4 MB',
      hash: 'sha256:deadbeef123456789abcdef0123456789abcdef0123456789abcdef012345678',
      pageCount: 22,
      rawText: `FHIR SECURITY SPECIFICATION\n\n1. OAuth2 token expiration configured for 720 hours.\n2. Audit logs retained for 90 days.`
    },
    sourceDocuments: [
      {
        id: 'SRC-040',
        name: 'HIPAA_Security_Rule_Standard_Ops.pdf',
        type: 'Compliance Standard',
        sizeBytes: 2400000,
        uploadedAt: '2026-10-08T18:02:00Z',
        authority: 'LATEST_APPROVED',
        authorityLabel: 'HIPAA Security SOP',
        freshnessDate: '15 Sep 2026',
        version: 'v2.0',
        hash: 'sha256:abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789'
      }
    ],
    claims: [],
    flags: [],
    whatToCheck: [
      {
        id: 'WTC-301',
        order: 1,
        title: 'Verify OAuth2 token TTL (HIPAA max 1 hour vs AI spec 720 hours)',
        severity: 'HIGH',
        materiality: 'HIGH',
        flagId: 'FLG-301',
        summary: 'Excessive token lifespan poses unauthorized access risk.',
        actionRequired: 'Update configuration to 3600 seconds max.'
      }
    ],
    waterfall: [
      { name: 'Initial Trust Baseline', deduction: 0, scoreAfter: 100, description: 'Baseline', severity: 'NEUTRAL' },
      { name: 'OAuth2 Expiration Discrepancy', deduction: -19, scoreAfter: 81, description: 'Token TTL exceeds maximum', severity: 'HIGH' },
      { name: 'Audit Log Retention Gap', deduction: -10, scoreAfter: 71, description: '6-year statutory retention violated', severity: 'MEDIUM' }
    ]
  },

  {
    id: 'AUD-1120',
    title: 'Sovereign Cloud Data Sovereignty & Border Protocol',
    documentName: 'Sovereign_Cloud_Compliance_Draft.docx',
    documentType: 'Compliance Filing',
    language: 'English / Hindi',
    uploadedAt: '2026-10-08T20:10:00Z',
    updatedAt: '2026-10-08T20:10:00Z',
    status: 'PROCESSING',
    priority: 'HIGH',
    trustScore: 0,
    initialScore: 100,
    riskBand: 'Review Needed',
    findingsCount: 0,
    aiDocument: {
      name: 'Sovereign_Cloud_Compliance_Draft.docx',
      size: '1.2 MB',
      hash: 'sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef',
      pageCount: 6,
      rawText: `Processing document ingestion...`
    },
    sourceDocuments: [],
    claims: [],
    flags: [],
    whatToCheck: [],
    waterfall: []
  }
];

export const mockPassports: Record<string, Passport> = {
  'PASSPORT-88219-AUD1042-CRIT': {
    token: 'PASSPORT-88219-AUD1042-CRIT',
    auditId: 'AUD-1042',
    documentName: 'AI_Procurement_Summary_v3.pdf',
    documentHash: 'sha256:7b91c84f39ae62463e271917f8a3d5b74100cde19ef652a9f4c391219b188c0a',
    merkleRoot: 'merkle:9e8a7c6b5d4e3f2a1b0c9d8e7f6a5b4c3d2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a',
    signature: '3045022100e4c8f9021a88b5d32c918a24ef9876543210fedcba9876543210abcdef01234502207b6a5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6b',
    signedBy: 'TATHYA-CORE-VALIDATOR-NODE-01 (ECDSA-SECP256K1)',
    signedAt: '2026-10-08T19:15:22Z',
    trustScore: 42,
    status: 'VERIFIED',
    totalClaimsChecked: 14,
    verifiedClaimsCount: 10,
    unresolvedFlagsCount: 4
  },
  'PASSPORT-94102-AUD1104-VERIFIED': {
    token: 'PASSPORT-94102-AUD1104-VERIFIED',
    auditId: 'AUD-1104',
    documentName: 'Q3_Financial_Audit_Report_Certified.pdf',
    documentHash: 'sha256:c0ffee123456789abcdef0123456789abcdef0123456789abcdef0123456789a',
    merkleRoot: 'merkle:11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff',
    signature: '3046022100abc8f9021a88b5d32c918a24ef9876543210fedcba9876543210abcdef0123450221008b6a5c4d3e2f1a0b9c8d7e6f5a4b3c2d1e0f9a8b7c6d5e4f3a2b1c0d9e8f7a6c',
    signedBy: 'TATHYA-ENTERPRISE-TRUST-SEAL (ECDSA-SECP256K1)',
    signedAt: '2026-10-08T16:45:10Z',
    trustScore: 94,
    status: 'VERIFIED',
    totalClaimsChecked: 28,
    verifiedClaimsCount: 28,
    unresolvedFlagsCount: 0
  }
};
