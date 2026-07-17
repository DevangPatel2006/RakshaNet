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

from unittest.mock import patch

def test_create_and_read_complaint(client, auth_header):
    # Create complaint with location
    complaint_data = {
        "reporter_name": "Alice Smith",
        "phone": "9876543210",
        "text_content": "Received suspicious call claiming to be from the Cyber Crime cell requesting OTP.",
        "location_lat": 28.61,
        "location_lng": 77.23
    }
    
    response = client.post("/complaints", json=complaint_data, headers=auth_header)
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
    client.post("/complaints", json={"text_content": "Scam transcript 1"}, headers=auth_header)
    client.post("/complaints", json={"text_content": "Scam transcript 2"}, headers=auth_header)
    
    resp = client.get("/complaints", headers=auth_header)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert len(data) >= 2

def test_complaint_not_found(client):
    resp = client.get("/complaints/99999")
    assert resp.status_code == status.HTTP_404_NOT_FOUND

def test_complaint_risk_check(client, auth_header):
    # Create complaint
    resp_create = client.post("/complaints", json={"text_content": "Risk check scam message"}, headers=auth_header)
    comp_id = resp_create.json()["id"]
    
    resp = client.post(f"/complaints/{comp_id}/risk-check")
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "risk_score" in data
    assert "risk_explanation" in data

def test_citizen_complaint_alert_targeting(client, auth_header):
    with patch("app.services.event_bus.RedisEventBus.publish_alert") as mock_publish:
        complaint_data = {
            "reporter_name": "arbitrary_display_name",
            "phone": "9876543210",
            "text_content": "Suspicious digital arrest call from custom authorities.",
        }
        response = client.post("/complaints", json=complaint_data, headers=auth_header)
        assert response.status_code == status.HTTP_201_CREATED
        comp_id = response.json()["id"]

        resp = client.post(f"/complaints/{comp_id}/risk-check")
        assert resp.status_code == status.HTTP_200_OK

        assert mock_publish.call_count >= 1
        
        citizen_alert_calls = [
            call for call in mock_publish.call_args_list 
            if call[1].get("target_role") == "citizen"
        ]
        assert len(citizen_alert_calls) == 1
        citizen_args = citizen_alert_calls[0][1]
        assert citizen_args.get("target_username") == "test_user_crud"

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
