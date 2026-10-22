import json
from pathlib import Path
import pytest
from app.ml import TextClassifier
from test_api import client,packet,AUTH,UPLOAD


def test_preview_auth_and_validation(client):
    assert client.post('/api/v1/triage/preview',json={'text':'cần nước uống'}).status_code==401
    assert client.post('/api/v1/triage/preview',headers=AUTH,json={'text':'cần nước uống','needs':['invalid']}).status_code==422
    got=client.post('/api/v1/triage/preview',headers=AUTH,json={'text':'có người bất tỉnh','priority':3}).json()
    assert got['suggested_priority']==1 and got['requires_review']


def test_priority_separate_from_signature_and_audited(client):
    p=packet(priority=2)
    assert client.post('/api/v1/sos',headers=UPLOAD,json=p).status_code==201
    path=f"/api/v1/sos/{p['message_id']}/priority"
    r=client.patch(path,headers=AUTH,json={'version':1,'priority':1,'reason':'đã xác minh có thương tích'})
    assert r.status_code==200
    assert r.json()['effective_priority']==1 and r.json()['body']['priority']==2
    assert client.patch(path,headers=AUTH,json={'version':1,'priority':3,'reason':'version cũ'}).status_code==409
    events=client.get(f"/api/v1/sos/{p['message_id']}/events",headers=AUTH).json()
    assert events[-1]['event']=='PRIORITY_CHANGED'
    assert client.get('/api/v1/stats',headers=AUTH).json()['open_priorities']['1']==1
    # Duplicate retries never reset an operator's decision.
    assert client.post('/api/v1/sos',headers=UPLOAD,json=p).status_code==200
    assert client.get('/api/v1/sos',headers=AUTH).json()['items'][0]['effective_priority']==1


def test_csv_guard_and_auth(client):
    assert client.get('/api/v1/export.csv').status_code==401
    p=packet(text='=HYPERLINK("bad")',location_text='+formula')
    client.post('/api/v1/sos',headers=UPLOAD,json=p)
    response=client.get('/api/v1/export.csv',headers=AUTH)
    assert response.status_code==200 and response.headers['x-export-count']=='1'
    assert "'=HYPERLINK" in response.text and "'+formula" in response.text


def test_real_export_and_group_disjoint():
    root=Path(__file__).resolve().parents[2]
    report=json.loads((root/'ai/artifacts/evaluation.json').read_text())
    sets=[set(report['group_split'][k]) for k in ['train','validation','test']]
    assert not (sets[0]&sets[1] or sets[0]&sets[2] or sets[1]&sets[2])
    model=TextClassifier(root/'ai/artifacts/triage_model.json')
    p=model.predict('zzzz qqqq')
    assert not p['has_known_features']
    assert sum(p['scores'])==pytest.approx(1)
    assert 0<=p['confidence']<=1


def test_model_preview(client,monkeypatch):
    root=Path(__file__).resolve().parents[2]
    monkeypatch.setenv('TRIAGE_MODEL',str(root/'ai/artifacts/triage_model.json'))
    got=client.post('/api/v1/triage/preview',headers=AUTH,json={'text':'zzzz qqqq','priority':3}).json()
    assert got['model_version']=='tfidf-logreg-demo-v0.2'
    assert got['low_confidence'] and got['suggested_priority']==2


def test_quota_by_received_time_and_duplicate_exemption(client):
    from cryptography.hazmat.primitives.asymmetric import ec
    import time
    key=ec.generate_private_key(ec.SECP256R1())
    now=int(time.time()*1000)
    accepted=[]
    for _ in range(30):
        # Delayed offline reports still count within the reception window.
        p=packet(_key=key,created_at_ms=now-7200000,expires_at_ms=now+3600000,location_captured_at_ms=now-7200000)
        assert client.post('/api/v1/sos',headers=UPLOAD,json=p).status_code==201
        accepted.append(p)
    assert client.post('/api/v1/sos',headers=UPLOAD,json=packet(_key=key)).status_code==429
    assert client.post('/api/v1/sos',headers=UPLOAD,json=accepted[0]).status_code==200
