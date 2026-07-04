import pytest
from fastapi import status
from app.db import models
from app.core.security import get_password_hash

@pytest.fixture
def auth_header(client, db_session):
    hashed_pw = get_password_hash("pass123")
    user = models.User(username="test_user_crud", hashed_password=hashed_pw, role="officer")
    db_session.add(user)
    db_session.commit()
    
    login_resp = client.post("/auth/login", data={"username": "test_user_crud", "password": "pass123"})
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_create_and_read_complaint(client, auth_header):
    # Create complaint with location
    complaint_data = {
        "reporter_name": "Alice Smith",
        "phone": "9876543210",
        "text_content": "Received suspicious call claiming to be from the Cyber Crime cell requesting OTP.",
        "location_lat": 28.61,
        "location_lng": 77.23
    }
    
    response = client.post("/complaints", json=complaint_data)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["reporter_name"] == "Alice Smith"
    assert data["phone"] == "9876543210"
    assert data["location_lat"] == pytest.approx(28.61, abs=1e-4)
    assert data["location_lng"] == pytest.approx(77.23, abs=1e-4)
    assert "id" in data
    
    comp_id = data["id"]
    
    # Read complaint back
    resp = client.get(f"/complaints/{comp_id}")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["reporter_name"] == "Alice Smith"
    assert data["location_lat"] == pytest.approx(28.61, abs=1e-4)
    assert data["location_lng"] == pytest.approx(77.23, abs=1e-4)

def test_read_complaints_list(client, auth_header):
    # Add two complaints
    client.post("/complaints", json={"text_content": "Scam transcript 1"})
    client.post("/complaints", json={"text_content": "Scam transcript 2"})
    
    resp = client.get("/complaints", headers=auth_header)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data) >= 2

def test_complaint_not_found(client):
    resp = client.get("/complaints/99999")
    assert resp.status_code == status.HTTP_404_NOT_FOUND

def test_complaint_risk_check(client):
    # Create complaint
    resp_create = client.post("/complaints", json={"text_content": "Risk check scam message"})
    comp_id = resp_create.json()["id"]
    
    resp = client.post(f"/complaints/{comp_id}/risk-check")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "risk_score" in data
    assert "risk_explanation" in data

def test_create_and_update_case(client, db_session, auth_header):
    # Create complaints first
    c1 = models.Complaint(text_content="Linked transcript 1")
    c2 = models.Complaint(text_content="Linked transcript 2")
    db_session.add(c1)
    db_session.add(c2)
    db_session.commit()
    
    case_payload = {
        "title": "Digital Arrest Fraud Network",
        "severity": "Critical",
        "complaint_ids": [c1.id, c2.id]
    }
    
    # Create case
    resp = client.post("/cases", json=case_payload, headers=auth_header)
    assert resp.status_code == status.HTTP_201_CREATED
    case_data = resp.json()
    assert case_data["title"] == "Digital Arrest Fraud Network"
    assert case_data["severity"] == "Critical"
    assert case_data["status"] == "Open"
    assert len(case_data["complaints"]) == 2
    
    case_id = case_data["id"]
    
    # Update case status
    update_payload = {"status": "Under Investigation", "severity": "High"}
    resp = client.put(f"/cases/{case_id}", json=update_payload, headers=auth_header)
    assert resp.status_code == status.HTTP_200_OK
    updated_data = resp.json()
    assert updated_data["status"] == "Under Investigation"
    assert updated_data["severity"] == "High"
