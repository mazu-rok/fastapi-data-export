import base64
from io import BytesIO
import json

import pytest
from core import Settings, Problem
from app import create_app

class Transport:
    def __init__(self): self.messages=[]
    def send(self,payload): self.messages.append(payload); return 'accepted'

@pytest.fixture
def fixture(tmp_path):
    transport=Transport()
    settings=Settings(database=str(tmp_path/'app.sqlite'),admin_password='test-password-long-enough',operator_email='operator@example.com')
    app=create_app(settings,transport)
    from fastapi.testclient import TestClient
    client=TestClient(app)
    return app,client,transport,settings

AUTH={'Authorization':'Basic '+base64.b64encode(b'admin:test-password-long-enough').decode()}

def test_export_requires_operator_and_contains_seeded_rows(fixture):
    import csv
    from io import StringIO
    app,client,mail,settings=fixture
    assert client.get('/').status_code==401
    assert client.get('/items').status_code==401
    assert client.post('/exports').status_code==401
    items=client.get('/items',headers=AUTH).json()
    assert len(items)==4 and items[0]['sku']=='P-001'
    response=client.post('/exports',headers=AUTH)
    assert response.status_code==201 and response.json()['row_count']==4
    message=mail.messages[0]
    assert message['to']=='operator@example.com'
    rows=list(csv.DictReader(StringIO(base64.b64decode(message['attachment']['data']).decode())))
    assert rows[0]['quantity']=='18' and len(rows)==4

def test_unconfigured_recipient_and_bad_origin_do_not_send(fixture):
    app,client,mail,settings=fixture
    settings.operator_email=''
    assert client.post('/exports',headers=AUTH).status_code==503
    assert client.post('/exports',headers={**AUTH,'Origin':'https://evil.example'}).status_code==403
    assert mail.messages==[] and app.state.store.records()==[]
