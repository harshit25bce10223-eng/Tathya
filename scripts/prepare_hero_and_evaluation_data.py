import os
import json
from pathlib import Path

# Paths
hero_dir = Path("storage/hero_pack")
hero_dir.mkdir(parents=True, exist_ok=True)

eval_dir = Path("storage/eval_data")
eval_dir.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# HERO PACK CREATION
# -----------------------------------------------------------------------------

# 1. AI-Generated Hero Business Document (with planted hallucinations/conflicts)
hero_doc_content = """# COMMERCIAL SUPPLY & SERVICES AGREEMENT (AI DRAFT SUMMARY)

## 1. PARTIES & RECITALS
This Master Supply Agreement is entered into between Zenith Enterprises Ltd ("Buyer") and Orion Solutions Pvt Ltd ("Vendor").

## 2. COMMERCIAL TERMS & CONTRACT VALUE
- Total Approved Contract Value: ₹50,00,000 (Fifty Lakhs Indian Rupees) payable across four quarterly disbursements.
- Payment Terms: Invoices payable within 30 days of receipt.
- Delivery Date: All deliverable hardware units must be handed over by 15 December 2026.

## 3. WARRANTY & SLA COMMITMENTS
- Warranty Coverage: Full manufacturer warranty for a period of 5 years from acceptance.
- System Availability SLA: 99.9% uptime guaranteed across all production endpoints.

## 4. LIABILITY & INDEMNIFICATION
- Liability: Vendor accepts unlimited liability for direct and indirect operational damages resulting from performance failures.

## 5. ESCALATION & CONTACTS
- Lead Finance Officer: Rahul Verma, Mobile: +91 98201 12345, Aadhaar: 4321 8765 1290, Email: rahul.verma@orion-solutions.internal.
"""
(hero_dir / "hero_contract_ai_draft.md").write_text(hero_doc_content, encoding="utf-8")

# 2. Source Document 1: Approved Purchase Order & Commercial Bid (₹41.6L vs ₹50L)
src1_content = """# APPROVED PURCHASE ORDER (PO-2026-8812)
Buyer: Zenith Enterprises Ltd
Vendor: Orion Solutions Pvt Ltd
Approved Base Commercial Value: ₹41,60,000 (Forty-One Lakh Sixty Thousand Indian Rupees) inclusive of GST.
Billing Terms: Net 45 days upon satisfactory inspection of milestones.
"""
(hero_dir / "src_purchase_order_approved.md").write_text(src1_content, encoding="utf-8")

# 3. Source Document 2: Technical Project Schedule (22 Dec vs 15 Dec)
src2_content = """# TECHNICAL SCHEDULE & DELIVERY MILESTONE SIGN-OFF
Project Milestone 4: Final hardware delivery and deployment.
Agreed Schedule Date: 22 December 2026.
Note: 15 December is the internal QA code freeze only; customer delivery is explicitly scheduled for 22 December 2026.
"""
(hero_dir / "src_project_schedule_signoff.md").write_text(src2_content, encoding="utf-8")

# 4. Source Document 3: Master Service Agreement Baseline (Warranty 12 mos vs 5 yrs, Liability cap)
src3_content = """# MASTER SERVICE LEVEL AGREEMENT (TERMS OF SERVICE)
Clause 7.1 (Warranty): Standard warranty period is twelve (12) months from formal commissioning. Extensions require formal change order.
Clause 9.3 (Limitation of Liability): Vendor liability is capped at 100% of aggregate fees paid in the preceding six (6) months. Unlimited liability is expressly disclaimed.
Clause 11.2 (SLA Target): Best-effort target is 99.5% uptime; 99.9% is not supported under standard tier.
"""
(hero_dir / "src_msa_terms_baseline.md").write_text(src3_content, encoding="utf-8")

# 5. Source Document 4: Vendor Contact & Privacy Policy (PII Handling)
src4_content = """# VENDOR DIRECTORY & DATA PRIVACY SPECIFICATION
Public contact point: support@orion-solutions.com.
Confidentiality Note: Individual government identifiers (such as Aadhaar or PAN) and private personal mobile numbers of key personnel must never be published in external commercial agreements.
"""
(hero_dir / "src_vendor_privacy_guidelines.md").write_text(src4_content, encoding="utf-8")

# Hero manifest with planted issues documented
hero_manifest = {
    "pack_name": "Hero Commercial Contract Pack",
    "hero_document": "hero_contract_ai_draft.md",
    "source_documents": [
        "src_purchase_order_approved.md",
        "src_project_schedule_signoff.md",
        "src_msa_terms_baseline.md",
        "src_vendor_privacy_guidelines.md"
    ],
    "planted_issues": [
        {"id": "ISSUE-1", "type": "financial_mismatch", "claim": "₹50,00,000", "source_fact": "₹41,60,000 in PO"},
        {"id": "ISSUE-2", "type": "date_mismatch", "claim": "15 December 2026", "source_fact": "22 December 2026 in Schedule"},
        {"id": "ISSUE-3", "type": "payment_terms_mismatch", "claim": "30 days", "source_fact": "Net 45 days in PO"},
        {"id": "ISSUE-4", "type": "sla_unsupported", "claim": "99.9% uptime", "source_fact": "99.5% standard tier in MSA"},
        {"id": "ISSUE-5", "type": "warranty_mismatch", "claim": "5 years", "source_fact": "12 months in MSA"},
        {"id": "ISSUE-6", "type": "pii_leak", "claim": "Aadhaar: 4321 8765 1290", "source_fact": "Aadhaar exposure violates privacy policy"},
        {"id": "ISSUE-7", "type": "unlimited_liability", "claim": "unlimited liability", "source_fact": "MSA Clause 9.3 caps liability"}
    ]
}
(hero_dir / "hero_manifest.json").write_text(json.dumps(hero_manifest, indent=2), encoding="utf-8")
print(f"[PASS] Hero Pack created with 1 hero doc + 4 source docs + 7 planted issues.")

# -----------------------------------------------------------------------------
# EVALUATION & SYNTHETIC DATASETS SKELETON
# -----------------------------------------------------------------------------
packs = ["Contract", "GST_Invoice", "Financial_Summary", "Project_Status", "Hinglish_Summary"]
splits = ["tuning", "test", "injector"]

for split in splits:
    split_dir = eval_dir / split
    split_dir.mkdir(parents=True, exist_ok=True)
    for pack in packs:
        pack_dir = split_dir / pack
        pack_dir.mkdir(parents=True, exist_ok=True)
        # Create 1 clean and 2 flawed variants
        (pack_dir / "clean_v1.json").write_text(json.dumps({"variant": "clean", "type": pack, "issues": []}, indent=2), encoding="utf-8")
        (pack_dir / "flawed_v1.json").write_text(json.dumps({"variant": "flawed", "type": pack, "issues": ["planted_numeric_diff"]}, indent=2), encoding="utf-8")
        (pack_dir / "flawed_v2.json").write_text(json.dumps({"variant": "flawed", "type": pack, "issues": ["planted_date_diff", "planted_pii"]}, indent=2), encoding="utf-8")

print(f"[PASS] Synthetic Evaluation Packs initialized: 5 domains across tuning/test/injector splits.")
