import uuid
import asyncio
from httpx import ASGITransport, AsyncClient
from app.main import app
from app.core.security import get_password_hash
from app.models import User, Audit, Document, Fact, Claim, Evidence, Flag
from sqlmodel import Session, select
from app.core.db import engine

async def test():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url='http://test') as ac:
        # Health
        r = await ac.get('/health')
        print('health:', r.status_code, r.json())
        
        # Create user and login
        unique_email = f'smoke_{uuid.uuid4().hex[:8]}@test.com'
        with Session(engine) as db:
            user = User(email=unique_email, hashed_password=get_password_hash('Str0ngPass!'), role='user')
            db.add(user)
            db.commit()
            db.refresh(user)
        
        r = await ac.post('/api/v1/login/access-token', data={'username': unique_email, 'password': 'Str0ngPass!'})
        token = r.json()['access_token']
        print('login:', r.status_code, 'token:', token[:20] + '...')
        
        headers = {'Authorization': f'Bearer {token}'}
        
        # Create audit
        r = await ac.post('/api/v1/audits', data={'title': 'Phase 3 smoke test'}, headers=headers)
        print('create audit:', r.status_code)
        audit = r.json()
        audit_id = audit['id']
        print('  audit_id:', audit_id)
        
        # Upload document with PII and risky commitments
        test_content = """
        Contract between ABC Corp and XYZ Ltd.
        
        The total contract value is ₹50 lakh.
        Delivery will be completed within 30 days.
        We guarantee 100% uptime and zero downtime.
        Unlimited liability for all damages.
        Contact: john.doe@company.com
        Phone: 9876543210
        Aadhaar: 1234 5678 9012
        API Key: sk-abcdefghijklmnopqrstuvwxyz123456
        Visit our portal at http://suspicious-site.xyz/login
        """
        
        files = {'files': ('contract.txt', test_content.encode(), 'text/plain')}
        r = await ac.post(f'/api/v1/audits/{audit_id}/documents', files=files, headers=headers)
        print('upload:', r.status_code, r.json())
        
        # Run audit
        r = await ac.post(f'/api/v1/audits/{audit_id}/run', headers=headers)
        print('run:', r.status_code, r.json())
        
        # Poll status
        for i in range(30):
            await asyncio.sleep(1)
            r = await ac.get(f'/api/v1/audits/{audit_id}/status', headers=headers)
            status = r.json()['status']
            print(f'  status check {i}: {status}')
            if status in ('completed', 'failed'):
                break
        
        # Get facts
        r = await ac.get(f'/api/v1/audits/{audit_id}/facts', headers=headers)
        print('facts:', r.status_code, r.json())
        
        # Get claims with grounding
        r = await ac.get(f'/api/v1/audits/{audit_id}/claims', headers=headers)
        print('claims:', r.status_code, r.json())
        
        # Get evidence
        r = await ac.get(f'/api/v1/audits/{audit_id}/evidence', headers=headers)
        print('evidence:', r.status_code, r.json())
        
        # Get flags with evidence
        r = await ac.get(f'/api/v1/audits/{audit_id}/flags', headers=headers)
        print('flags:', r.status_code, r.json())
        
        # Summary
        r = await ac.get(f'/api/v1/audits/{audit_id}', headers=headers)
        print('summary:', r.status_code)
        summary = r.json()
        print('  fact_count:', summary.get('fact_count'))
        print('  flag_count:', summary.get('flag_count'))
        print('  verify_token:', summary.get('verify_token'))
        
        # Verify DB state
        with Session(engine) as db:
            facts = db.exec(select(Fact).where(Fact.document_id.in_(
                select(Document.id).where(Document.audit_id == uuid.UUID(audit_id))
            ))).all()
            print(f'\nDB Facts count: {len(facts)}')
            for f in facts:
                print(f'  Fact: {f.subject} {f.predicate} = {f.object_value} (type: {f.status})')
            
            flags = db.exec(select(Flag).where(Flag.audit_id == uuid.UUID(audit_id))).all()
            print(f'\nDB Flags count: {len(flags)}')
            for f in flags:
                print(f'  Flag: {f.type} | {f.severity} | {f.reason[:80]}...')
        
        print('\nSMOKE TEST PASSED')

asyncio.run(test())