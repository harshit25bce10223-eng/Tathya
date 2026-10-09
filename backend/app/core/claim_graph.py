"""A paginated graph of actual current claims and literal source evidence."""
import json
from uuid import UUID
from sqlmodel import Session, select, func
from app.models import Claim, Document
from app.core.current_evidence import current_evidence
from app.core.source_verification import compare_quote
from app.core.business_policies import recorded_policy_results


def build_claim_graph(session: Session, audit_id: UUID, offset: int = 0, limit: int = 50) -> dict:
    query = select(Claim).join(Document, Claim.document_id == Document.id).where(Claim.audit_id == audit_id, Document.audit_id == audit_id, Document.kind == "primary", Document.is_current.is_(True))
    total = session.exec(select(func.count()).select_from(query.subquery())).one()
    claims = session.exec(query.order_by(Claim.created_at, Claim.id).offset(offset).limit(limit)).all()
    evidence = current_evidence(session, audit_id, [c.id for c in claims])
    documents = session.exec(select(Document).where(Document.audit_id == audit_id, Document.is_current.is_(True))).all()
    document_by_id = {d.id: d for d in documents}
    nodes = [{"id": "document:" + str(d.id), "kind": "document", "label": d.filename, "document_id": str(d.id), "version": d.version_no, "role": d.kind} for d in documents]
    edges = []
    by_claim = {c.id: c for c in claims}
    from app.core.source_resolution import current_resolutions
    resolutions = current_resolutions(session, audit_id)
    assessment = recorded_policy_results(session, audit_id)
    stale = assessment["documents_changed"] or assessment["resolutions_changed"]
    for claim in claims:
        primary = document_by_id.get(claim.document_id)
        anchored = bool(primary and claim.text.strip() and claim.text in primary.normalized_text)
        nodes.append({"id": "claim:" + str(claim.id), "kind": "claim", "label": claim.text, "document_id": str(claim.document_id), "status": "not_anchored" if not anchored else "uncertain" if stale else claim.status})
        edges.append({"from": "document:" + str(claim.document_id), "to": "claim:" + str(claim.id), "relation": "contains" if anchored else "unanchored"})
    for item in evidence:
        claim = by_claim[item.claim_id]
        verdict = compare_quote(claim.text, item.quote)
        relation = {"supported": "supports", "contradicted": "contradicts"}.get(verdict, "candidate")
        if verdict is None and not stale:
            try:
                grounding = json.loads(claim.metadata_json or "{}").get("grounding", {})
                if str(item.id) == grounding.get("primary_evidence_id"):
                    relation = {"supported": "supports", "contradicted": "contradicts"}.get(grounding.get("status"), "candidate")
            except (TypeError, ValueError, AttributeError):
                pass
        from app.core.source_verification import field_hint
        field = {"delivery": "delivery_date", "payment": "payment_terms_days", "warranty": "warranty_months", "contract_value": "contract_value"}.get(field_hint(claim.text))
        selection = resolutions.get(field, {})
        nodes.append({"reviewer_selected": selection.get("document_id") == str(item.source_document_id), "id": "evidence:" + str(item.id), "kind": "evidence", "label": item.quote, "document_id": str(item.source_document_id), "location": item.location_json})
        edges.append({"from": "evidence:" + str(item.id), "to": "claim:" + str(claim.id), "relation": relation})
        edges.append({"from": "document:" + str(item.source_document_id), "to": "evidence:" + str(item.id), "relation": "quotes"})
    return {"nodes": nodes, "edges": edges, "offset": offset, "limit": limit, "total_claims": total, "has_more": offset + len(claims) < total, "assessment_stale": stale}
