"""Living Trust: actual claim graph links, bounded watched sources and immutable versions."""
import json
import uuid
from pathlib import Path
import pytest
from sqlmodel import select
from app.models import Audit, AuditLogEntry, Claim, Document, Evidence, User
from app.core.pipeline import ingest_document, save_upload
from app.core.claims import extract_claims
from app.core.source_watch import check_watch, inbox, inspect_watch


@pytest.fixture
def living_audit(db):
    owner=db.exec(select(User).where(User.is_superuser.is_(True))).first()
    audit=Audit(title="Living trust "+uuid.uuid4().hex,owner_id=owner.id,status="completed")
    db.add(audit);db.commit()
    def doc(name,text):return ingest_document(db,audit,filename=name,path=save_upload(audit.id,name,text.encode()))
    primary=doc("generated.txt","Warranty is valid for 12 months.\nPayment is due within 30 days.")
    source=doc("approved.txt","Warranty is valid for 6 months.\nPayment is due within 30 days.")
    claims=extract_claims(db,primary)
    for claim in claims:
        quote=source.normalized_text.splitlines()[0 if "Warranty" in claim.text else 1]
        db.add(Evidence(claim_id=claim.id,source_document_id=source.id,quote=quote,support_type="supports"))
    db.commit()
    return audit,primary,source,claims


def enable(client,headers,audit,auto=False):
    result=client.post("/api/v1/sources/watch",headers=headers,json={"audit_id":str(audit.id),"enabled":True,"auto_reaudit":auto,"note":"Watch the synthetic regression inbox."})
    assert result.status_code==200,result.text
    return Path(result.json()["inbox_path"])


def test_graph_uses_real_quote_comparisons_and_paginated_claims(client,db,superuser_token_headers,living_audit):
    audit,primary,source,claims=living_audit
    response=client.get(f"/api/v1/audits/{audit.id}/claim-graph",headers=superuser_token_headers)
    assert response.status_code==200
    data=response.json()
    assert data["total_claims"]==2 and not data["has_more"]
    relations={e["relation"] for e in data["edges"]}
    assert "contradicts" in relations and "supports" in relations
    assert {n["label"] for n in data["nodes"] if n["kind"]=="evidence"}==set(source.normalized_text.splitlines())
    first=client.get(f"/api/v1/audits/{audit.id}/claim-graph?limit=1",headers=superuser_token_headers).json()
    second=client.get(f"/api/v1/audits/{audit.id}/claim-graph?limit=1&offset=1",headers=superuser_token_headers).json()
    assert first["has_more"] and not second["has_more"]
    assert {n["id"] for n in first["nodes"] if n["kind"]=="claim"}!={n["id"] for n in second["nodes"] if n["kind"]=="claim"}
    assert client.get(f"/api/v1/audits/{audit.id}/claim-graph?limit=101",headers=superuser_token_headers).status_code==422


def test_graph_excludes_obsolete_forged_and_cross_audit_evidence(client,db,superuser_token_headers,living_audit):
    audit,_,source,claims=living_audit
    db.add(Evidence(claim_id=claims[0].id,source_document_id=source.id,quote="Fabricated source statement."));db.commit()
    updated=ingest_document(db,audit,filename="approved.txt",path=save_upload(audit.id,"approved.txt",b"Warranty is valid for 24 months."))
    response=client.get(f"/api/v1/audits/{audit.id}/claim-graph",headers=superuser_token_headers).json()
    assert not [n for n in response["nodes"] if n["kind"]=="evidence"]
    assert str(source.id) not in json.dumps(response) and str(updated.id) in json.dumps(response)


def test_graph_and_watch_permissions(client,superuser_token_headers,normal_user_token_headers,living_audit):
    audit,_,_,_=living_audit
    assert client.get(f"/api/v1/audits/{audit.id}/claim-graph").status_code==401
    assert client.get(f"/api/v1/audits/{audit.id}/claim-graph",headers=normal_user_token_headers).status_code in (403,404)
    body={"audit_id":str(audit.id),"enabled":True,"note":"Test watcher access."}
    assert client.post("/api/v1/sources/watch",json=body,headers=normal_user_token_headers).status_code==403
    assert client.post(f"/api/v1/sources/{audit.id}/check",headers=normal_user_token_headers).status_code==403
    assert client.get(f"/api/v1/sources/{audit.id}/stale",headers=normal_user_token_headers).status_code in (403,404)
    assert client.post("/api/v1/sources/watch",json={**body,"path":"C:/"},headers=superuser_token_headers).status_code==422


def test_watched_changes_create_versions_once_and_preserve_sources(client,db,superuser_token_headers,living_audit):
    audit,_,source,_=living_audit
    folder=enable(client,superuser_token_headers,audit)
    path=folder/"approved.txt";path.write_text("Warranty is valid for 12 months.",encoding="utf-8")
    assert inspect_watch(db,audit.id)["changed_count"]==1
    first=check_watch(db,audit.id,audit.owner_id)
    assert len(first["imported"])==1 and not first["reaudit_queued"]
    db.refresh(source);assert not source.is_current
    assert check_watch(db,audit.id,audit.owner_id)["imported"]==[]
    path.write_text("Warranty is valid for 24 months.",encoding="utf-8")
    second=check_watch(db,audit.id,audit.owner_id)
    assert len(second["imported"])==1 and second["imported"][0]["version"]>first["imported"][0]["version"]
    documents=db.exec(select(Document).where(Document.audit_id==audit.id,Document.filename=="approved.txt")).all()
    assert len(documents)==3 and sum(d.is_current for d in documents)==1
    entries=db.exec(select(AuditLogEntry).where(AuditLogEntry.audit_id==audit.id,AuditLogEntry.action=="source.watch.imported")).all()
    assert len(entries)==2 and all(json.loads(e.payload_json)["raw_sha256"] for e in entries)
    assert path.exists()


def test_watcher_auto_reaudit_submits_only_after_import_commit(client,db,superuser_token_headers,living_audit,monkeypatch):
    from app.core import jobs
    audit,_,_,_=living_audit
    folder=enable(client,superuser_token_headers,audit,auto=True)
    (folder/"amendment.txt").write_text("Warranty is valid for 24 months.",encoding="utf-8")
    submitted=[]
    def submit(audit_id):
        db.refresh(audit)
        assert audit.status=="queued"
        assert db.exec(select(Document).where(Document.audit_id==audit_id,Document.filename=="amendment.txt")).first()
        submitted.append(audit_id)
    monkeypatch.setattr(jobs,"submit_audit_job",submit)
    result=check_watch(db,audit.id,audit.owner_id)
    assert result["reaudit_queued"] and submitted==[audit.id]
    assert check_watch(db,audit.id,audit.owner_id)["busy"]


def test_watcher_rejects_primary_overwrite_empty_unsupported_and_bad_parse(client,db,superuser_token_headers,living_audit):
    audit,primary,_,_=living_audit
    folder=enable(client,superuser_token_headers,audit)
    (folder/"generated.txt").write_text("Warranty is valid for 99 months.",encoding="utf-8")
    (folder/"empty.txt").write_bytes(b"")
    (folder/"unknown.exe").write_bytes(b"not a document")
    (folder/"broken.docx").write_bytes(b"not a zip")
    result=check_watch(db,audit.id,audit.owner_id)
    assert not result["imported"] and len(result["errors"])==4
    db.refresh(primary);assert primary.is_current
    assert len(db.exec(select(Document).where(Document.audit_id==audit.id)).all())==2
    assert not list((Path(folder).parent.parent/str(audit.id)).glob("*broken.docx"))


def test_disabled_watch_and_path_boundary(client,db,superuser_token_headers,living_audit,tmp_path):
    from app.core.source_watch import _read
    audit,_,_,_=living_audit
    with pytest.raises(ValueError,match="Enable"):
        check_watch(db,audit.id,audit.owner_id)
    folder=enable(client,superuser_token_headers,audit)
    outside=tmp_path/"outside.txt";outside.write_text("Outside evidence",encoding="utf-8")
    with pytest.raises(ValueError,match="inside"):
        _read(outside,folder)
    response=client.post("/api/v1/sources/watch",headers=superuser_token_headers,json={"audit_id":str(audit.id),"enabled":False,"note":"Disable the synthetic inbox."})
    assert response.status_code==200 and not response.json()["enabled"]


def test_source_only_upload_cannot_replace_primary(client,db,superuser_token_headers,living_audit):
    audit,primary,_,_=living_audit
    response=client.post(f"/api/v1/audits/{audit.id}/documents",headers=superuser_token_headers,data={"source_only":"true"},files=[("files",("generated.txt",b"Replacement primary document.","text/plain"))])
    assert response.status_code==409
    db.refresh(primary);assert primary.is_current


def test_unanchored_claim_cannot_create_verified_graph_edges(client,db,superuser_token_headers,living_audit,monkeypatch):
    from app.core import grounding
    from app.core.current_evidence import current_evidence
    audit,primary,source,_=living_audit
    claim=Claim(audit_id=audit.id,document_id=primary.id,text="Warranty is valid for 6 months.",status="supported")
    db.add(claim);db.commit();db.refresh(claim)
    db.add(Evidence(claim_id=claim.id,source_document_id=source.id,quote=claim.text));db.commit()
    assert current_evidence(db,audit.id,[claim.id])==[]
    calls=[]
    monkeypatch.setattr(grounding,"retrieve_for_claim",lambda *args:calls.append("retrieval"))
    result=grounding._ground_single_claim(db,claim)
    assert result.status.value=="unsupported" and calls==[]
    graph=client.get(f"/api/v1/audits/{audit.id}/claim-graph",headers=superuser_token_headers).json()
    node=next(n for n in graph["nodes"] if n["id"]=="claim:"+str(claim.id))
    assert node["status"]=="not_anchored"
    assert not [e for e in graph["edges"] if e["to"]==node["id"] and e["relation"] in ("supports","contradicts")]


def test_failed_files_do_not_block_automatic_import_of_other_sources(client,db,superuser_token_headers,living_audit):
    audit,_,_,_=living_audit
    folder=enable(client,superuser_token_headers,audit)
    for index in range(5):(folder/f"a{index}.docx").write_bytes(b"broken office file")
    (folder/"z-valid.txt").write_text("Warranty is valid for 24 months.",encoding="utf-8")
    first=check_watch(db,audit.id,audit.owner_id,automatic=True)
    assert not first["imported"] and len(first["errors"])==5
    second=check_watch(db,audit.id,audit.owner_id,automatic=True)
    assert len(second["imported"])==1 and second["imported"][0]["filename"]=="z-valid.txt"
    assert sum(f["state"]=="failed" for f in inspect_watch(db,audit.id)["files"])==5


def resolution_fixture(db,living_audit):
    from app.core.facts import extract_facts
    from app.core.grounding import ground_claims,emit_grounding_flags
    from app.core.business_policies import evaluate_audit_policies
    audit,_,source,claims=living_audit
    selected=ingest_document(db,audit,filename="amendment.txt",path=save_upload(audit.id,"amendment.txt",b"Warranty is valid for 12 months."))
    for doc in (source,selected):extract_facts(db,doc)
    warranty=next(c for c in claims if "Warranty" in c.text)
    db.add(Evidence(claim_id=warranty.id,source_document_id=selected.id,quote=selected.normalized_text));db.commit()
    ground_claims(db,audit.id);emit_grounding_flags(db,audit.id);evaluate_audit_policies(db,audit.id)
    return audit,selected


def choose(client,headers,audit,document,revision=None):
    return client.post(f"/api/v1/sources/{audit.id}/resolve",headers=headers,json={"field":"warranty_months","document_id":str(document.id) if document else None,"expected_revision":revision,"note":"Reviewer confirms this specific source version applies to the warranty."})


def test_explicit_source_selection_resolves_actual_conflict_after_reaudit(client,db,superuser_token_headers,living_audit):
    from app.core.trust_score import compute_score_breakdown
    from app.core.grounding import ground_claims,emit_grounding_flags
    from app.core.business_policies import evaluate_audit_policies
    audit,selected=resolution_fixture(db,living_audit)
    assert compute_score_breakdown(db,str(audit.id)).coverage["uncertain"]==1
    result=choose(client,superuser_token_headers,audit,selected)
    assert result.status_code==200,result.text
    data=result.json()
    assert data["canonical"]["warranty_months"]["value"]==12
    assert data["canonical"]["warranty_months"]["reviewer_selected"] is True
    assert data["resolutions"][0]["state"]=="selected"
    assert compute_score_breakdown(db,str(audit.id)).score_status=="insufficient_verification"
    assert all(r.status.value=="supported" for r in ground_claims(db,audit.id))
    emit_grounding_flags(db,audit.id);evaluate_audit_policies(db,audit.id)
    score=compute_score_breakdown(db,str(audit.id))
    assert score.reviewed_score==100 and score.coverage["supported"]==2
    graph=client.get(f"/api/v1/audits/{audit.id}/claim-graph",headers=superuser_token_headers).json()
    assert any(n.get("reviewer_selected") for n in graph["nodes"] if n["kind"]=="evidence")


def test_source_selection_version_conflict_clear_and_expiry(client,db,superuser_token_headers,living_audit):
    audit,selected=resolution_fixture(db,living_audit)
    first=choose(client,superuser_token_headers,audit,selected).json()
    revision=first["resolutions"][0]["revision"]
    assert choose(client,superuser_token_headers,audit,selected).status_code==409
    updated=ingest_document(db,audit,filename="amendment.txt",path=save_upload(audit.id,"amendment.txt",b"Warranty is valid for 18 months."))
    from app.core.facts import extract_facts
    from app.core.source_fact_sheet import build_source_fact_sheet
    extract_facts(db,updated)
    data=build_source_fact_sheet(db,audit.id)
    assert data["resolutions"][0]["state"]=="expired"
    assert "warranty_months" not in data["canonical"]
    assert choose(client,superuser_token_headers,audit,selected,revision).status_code==422
    cleared=choose(client,superuser_token_headers,audit,None,revision)
    assert cleared.status_code==200 and cleared.json()["resolutions"][0]["state"]=="cleared"
    assert len(db.exec(select(AuditLogEntry).where(AuditLogEntry.audit_id==audit.id,AuditLogEntry.action=="source.resolution.recorded")).all())==2


def test_source_selection_permissions_and_ambiguous_field(client,db,superuser_token_headers,normal_user_token_headers,living_audit):
    audit,selected=resolution_fixture(db,living_audit)
    assert choose(client,normal_user_token_headers,audit,selected).status_code==403
    assert choose(client,superuser_token_headers,audit,living_audit[1]).status_code==422
    ambiguous=ingest_document(db,audit,filename="ambiguous.txt",path=save_upload(audit.id,"ambiguous.txt",b"Warranty is valid for 12 months. Warranty is valid for 24 months."))
    from app.core.facts import extract_facts
    extract_facts(db,ambiguous)
    assert choose(client,superuser_token_headers,audit,ambiguous).status_code==422
    audit.status="processing";db.add(audit);db.commit()
    assert choose(client,superuser_token_headers,audit,selected).status_code==409


def test_source_target_policy_uses_explicit_selected_source(client,db,superuser_token_headers,living_audit):
    from app.core.business_policies import BusinessRules,preview_rules
    audit,selected=resolution_fixture(db,living_audit)
    rule=BusinessRules.model_validate({"target":"source","conditions":[{"variable":"warranty_months","operator":"gte","value":12}]})
    assert preview_rules(db,audit.id,rule)["state"]=="uncertain"
    assert choose(client,superuser_token_headers,audit,selected).status_code==200
    result=preview_rules(db,audit.id,rule)
    assert result["state"]=="satisfied"
    assert all(e["document_id"]==str(selected.id) for e in result["conditions"][0]["evidence"])


def test_concurrent_chain_appends_preserve_one_verified_history(db,living_audit):
    from concurrent.futures import ThreadPoolExecutor
    from sqlmodel import Session
    from app.core.pipeline import append_chain_entry
    from app.core.security import verify_chain
    audit,_,_,_=living_audit
    audit_id,owner_id=audit.id,audit.owner_id
    engine=db.get_bind()
    def append(index):
        with Session(engine) as session:
            append_chain_entry(session,audit_id=audit_id,actor_id=owner_id,action="regression.concurrent",payload_json=json.dumps({"index":index}))
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(append,range(8)))
    entries=db.exec(select(AuditLogEntry).where(AuditLogEntry.audit_id==audit_id).order_by(AuditLogEntry.created_at)).all()
    assert len(entries)==8
    assert verify_chain([e.model_dump(mode="json") for e in entries])[0] is True
