"""
TATHYA DEMO SEED
================
Creates a demo account + realistic Round-1 demo data to showcase every
major feature of Tathya to investors / evaluators.

Demo account  :  demo@tathya.ai  /  Demo@2024Tathya
Superuser can always log in as  admin@tathya.ai  /  changethis

Run from project root:
    python scripts/seed_demo.py

Safe to re-run — skips if demo account already exists.
"""

import hashlib
import json
import sys
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

# ── Add backend to sys.path ──────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from sqlmodel import Session, select  # noqa: E402

from app.core.db import engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models import (  # noqa: E402
    Audit,
    Claim,
    Document,
    Evidence,
    Fact,
    User,
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def now() -> datetime:
    return datetime.now(UTC)


def days_ago(n: int) -> datetime:
    return now() - timedelta(days=n)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# ── Demo data ─────────────────────────────────────────────────────────────────

DEMO_EMAIL = "demo@tathya.ai"
DEMO_PASSWORD = "Demo@2024Tathya"
DEMO_NAME = "Tathya Demo"

AUDITS = [
    # ── Audit 1: COMPLETED, high trust score (flagship demo) ───────────────
    {
        "title": "PM Modi's 'Viksit Bharat by 2047' Economic Claims",
        "status": "completed",
        "ai_score": 78.5,
        "reviewed_score": 81.0,
        "score_band": "mostly-trustworthy",
        "critical_risk": False,
        "review_status": "reviewed",
        "created_at": days_ago(3),
        "claims": [
            {
                "text": "India's GDP will reach $5 trillion by 2027.",
                "category": "economic",
                "status": "contradicted",
                "evidence": [
                    {
                        "quote": "IMF projects India GDP at $4.27 trillion by FY2027, not $5 trillion.",
                        "support_type": "refutes",
                        "score": 0.91,
                    }
                ],
            },
            {
                "text": "India is now the world's 5th largest economy.",
                "category": "economic",
                "status": "supported",
                "evidence": [
                    {
                        "quote": "World Bank data confirms India surpassed UK to become 5th largest in 2022.",
                        "support_type": "supports",
                        "score": 0.96,
                    }
                ],
            },
            {
                "text": "Manufacturing sector contributes 17% of GDP.",
                "category": "economic",
                "status": "uncertain",
                "evidence": [
                    {
                        "quote": "MoSPI data shows manufacturing at 15.6% of GVA in FY2023.",
                        "support_type": "refutes",
                        "score": 0.74,
                    }
                ],
            },
            {
                "text": "PM Gati Shakti has integrated 1,500+ infrastructure projects.",
                "category": "policy",
                "status": "supported",
                "evidence": [
                    {
                        "quote": "Ministry of Commerce confirms 1,521 projects mapped on PM Gati Shakti portal.",
                        "support_type": "supports",
                        "score": 0.88,
                    }
                ],
            },
        ],
        "facts": [
            ("India", "GDP rank", "5th globally (World Bank 2023)"),
            ("PM Gati Shakti", "project count", "1,521 mapped projects"),
            ("India GDP", "IMF projection 2027", "$4.27 trillion"),
            ("Manufacturing", "GDP share FY23", "15.6% of GVA"),
        ],
    },
    # ── Audit 2: COMPLETED, low trust score (critical risk) ───────────────
    {
        "title": "Viral WhatsApp: 'ISRO cancels Chandrayaan-4 due to funding crisis'",
        "status": "completed",
        "ai_score": 12.0,
        "reviewed_score": 9.5,
        "score_band": "misleading",
        "critical_risk": True,
        "review_status": "final",
        "created_at": days_ago(7),
        "claims": [
            {
                "text": "ISRO has cancelled Chandrayaan-4 mission due to funding cuts.",
                "category": "science",
                "status": "contradicted",
                "evidence": [
                    {
                        "quote": "ISRO Chairman confirmed Chandrayaan-4 is on schedule with full budget approved in Union Budget 2024.",
                        "support_type": "refutes",
                        "score": 0.98,
                    }
                ],
            },
            {
                "text": "ISRO's budget was cut by 40% this year.",
                "category": "economic",
                "status": "contradicted",
                "evidence": [
                    {
                        "quote": "Union Budget 2024-25 allocates Rs 13,042 crore to Department of Space, a 9.7% INCREASE over previous year.",
                        "support_type": "refutes",
                        "score": 0.99,
                    }
                ],
            },
            {
                "text": "Three senior ISRO scientists have resigned in protest.",
                "category": "personnel",
                "status": "contradicted",
                "evidence": [
                    {
                        "quote": "No resignation announcements from ISRO in 2024. This claim has no traceable source.",
                        "support_type": "refutes",
                        "score": 0.97,
                    }
                ],
            },
        ],
        "facts": [
            ("ISRO", "Space budget 2024-25", "Rs 13,042 crore (+9.7%)"),
            ("Chandrayaan-4", "Mission status", "Active — launch planned 2027"),
            ("Chandrayaan-4", "Funding status", "Approved in full"),
        ],
    },
    # ── Audit 3: PROCESSING (shows live pipeline in action) ───────────────
    {
        "title": "Health Ministry: 'Ayushman Bharat covers 55 crore beneficiaries'",
        "status": "processing",
        "ai_score": 100.0,
        "reviewed_score": 100.0,
        "score_band": "trustworthy",
        "critical_risk": False,
        "review_status": "pending",
        "created_at": days_ago(0),
        "claims": [],
        "facts": [],
    },
    # ── Audit 4: COMPLETED, medium trust (mixed signals) ──────────────────
    {
        "title": "Opposition Claim: 'Unemployment at 45-year high under current govt'",
        "status": "completed",
        "ai_score": 54.0,
        "reviewed_score": 58.5,
        "score_band": "contested",
        "critical_risk": False,
        "review_status": "reviewed",
        "created_at": days_ago(14),
        "claims": [
            {
                "text": "Unemployment rate in India is at a 45-year high.",
                "category": "economic",
                "status": "uncertain",
                "evidence": [
                    {
                        "quote": "CMIE data showed 7.8% unemployment in 2022, but PLFS data from MoSPI shows 3.2% for same period using different methodology.",
                        "support_type": "supports",
                        "score": 0.61,
                    }
                ],
            },
            {
                "text": "Over 2 crore jobs were promised but only 70 lakh were created.",
                "category": "economic",
                "status": "unsupported",
                "evidence": [
                    {
                        "quote": "No official government source confirms the '2 crore jobs per year' promise as a formal policy commitment.",
                        "support_type": "refutes",
                        "score": 0.52,
                    }
                ],
            },
            {
                "text": "Youth unemployment (15-29 age group) stands at 23%.",
                "category": "economic",
                "status": "supported",
                "evidence": [
                    {
                        "quote": "ILO India Employment Report 2024 confirms youth unemployment at 23.4% for 15-29 age bracket.",
                        "support_type": "supports",
                        "score": 0.89,
                    }
                ],
            },
        ],
        "facts": [
            ("CMIE unemployment", "2022 rate", "7.8%"),
            ("PLFS unemployment", "2022 rate", "3.2% (different methodology)"),
            ("Youth unemployment 15-29", "ILO 2024", "23.4%"),
        ],
    },
    # ── Audit 5: QUEUED (shows queue state) ──────────────────────────────
    {
        "title": "RBI Governor: 'Inflation contained within 4% target for 6 months'",
        "status": "queued",
        "ai_score": 100.0,
        "reviewed_score": 100.0,
        "score_band": "trustworthy",
        "critical_risk": False,
        "review_status": "pending",
        "created_at": days_ago(0),
        "claims": [],
        "facts": [],
    },
]


def seed_demo() -> None:
    print("[TATHYA DEMO SEED]")

    with Session(engine) as session:
        # ── 1. Create demo user ──────────────────────────────────────────────
        existing = session.exec(
            select(User).where(User.email == DEMO_EMAIL)
        ).first()

        if existing:
            print(f"[SKIP] Demo user {DEMO_EMAIL!r} already exists.")
            demo_user = existing
        else:
            demo_user = User(
                id=uuid.uuid4(),
                email=DEMO_EMAIL,
                full_name=DEMO_NAME,
                hashed_password=get_password_hash(DEMO_PASSWORD),
                is_active=True,
                is_superuser=False,
                role="reviewer",
                created_at=days_ago(30),
            )
            session.add(demo_user)
            session.commit()
            session.refresh(demo_user)
            print(f"[OK] Created demo user: {DEMO_EMAIL}")

        # ── 2. Check if demo data already seeded ─────────────────────────────
        existing_audits = session.exec(
            select(Audit).where(Audit.owner_id == demo_user.id)
        ).all()
        if len(existing_audits) >= 4:
            print(f"[SKIP] Demo audits already seeded ({len(existing_audits)} found).")
            return

        # ── 3. Seed audits ────────────────────────────────────────────────────
        for i, a in enumerate(AUDITS):
            audit_id = uuid.uuid4()
            doc_text = (
                f"[DEMO DOCUMENT]\n\nAudit: {a['title']}\n\n"
                f"This is a demo document seeded for the Tathya Round-1 demonstration.\n"
                f"Claim count: {len(a['claims'])}\n"
                f"Status: {a['status']}\n"
            )
            doc_hash = sha256(doc_text + str(audit_id))

            audit = Audit(
                id=audit_id,
                title=a["title"],
                status=a["status"],
                ai_score=a["ai_score"],
                reviewed_score=a["reviewed_score"],
                score_band=a["score_band"],
                critical_risk=a["critical_risk"],
                review_status=a["review_status"],
                owner_id=demo_user.id,
                created_at=a["created_at"],
                updated_at=a["created_at"],
                source_set_hash=doc_hash[:16],
                score_version="4.0",
                score_methodology="deterministic_penalty_v1",
            )
            session.add(audit)
            session.flush()

            # Document
            doc_id = uuid.uuid4()
            doc = Document(
                id=doc_id,
                audit_id=audit_id,
                kind="primary",
                filename=f"demo_source_{i+1}.txt",
                mime_type="text/plain",
                storage_path=f"demo/uploads/demo_source_{i+1}.txt",
                raw_text=doc_text,
                normalized_text=doc_text.lower(),
                offset_map_json="[]",
                blocks_json="[]",
                text_hash=doc_hash,
                version_no=1,
                is_current=True,
                metadata_json=json.dumps({"demo": True, "round": 1}),
                created_at=a["created_at"],
            )
            session.add(doc)
            session.flush()

            # Facts
            for subj, pred, obj in a.get("facts", []):
                session.add(
                    Fact(
                        id=uuid.uuid4(),
                        document_id=doc_id,
                        subject=subj,
                        predicate=pred,
                        object_value=obj,
                        status="active",
                        created_at=a["created_at"],
                    )
                )

            # Claims + Evidence
            for c in a.get("claims", []):
                claim_id = uuid.uuid4()
                claim = Claim(
                    id=claim_id,
                    audit_id=audit_id,
                    document_id=doc_id,
                    sentence_id=str(uuid.uuid4())[:8],
                    text=c["text"],
                    category=c["category"],
                    status=c["status"],
                    metadata_json=json.dumps({"demo": True}),
                    created_at=a["created_at"],
                )
                session.add(claim)
                session.flush()

                for ev in c.get("evidence", []):
                    session.add(
                        Evidence(
                            id=uuid.uuid4(),
                            claim_id=claim_id,
                            source_document_id=doc_id,
                            quote=ev["quote"],
                            support_type=ev["support_type"],
                            score=ev["score"],
                            location_json="{}",
                        )
                    )

            session.commit()
            status_icon = {"completed": "[OK]", "processing": "[~~]", "queued": "[..]", "failed": "[!!]"}.get(a["status"], "[OK]")
            print(f"  {status_icon} Audit {i+1}/5: {a['title'][:55]}...")

        print()
        print("=" * 60)
        print("DEMO SEED COMPLETE")
        print("=" * 60)
        print(f"  Email   : {DEMO_EMAIL}")
        print(f"  Password: {DEMO_PASSWORD}")
        print("  Role    : reviewer (can view all audits)")
        print()
        print("  Admin   : admin@tathya.ai / changethis")
        print()
        print("  Audits seeded:")
        for a in AUDITS:
            band = a["score_band"].upper()
            print(f"    [{a['status'].upper():<10}] [{band:<20}] {a['title'][:45]}")
        print()
        print("  Open: http://localhost:5174")


if __name__ == "__main__":
    seed_demo()
