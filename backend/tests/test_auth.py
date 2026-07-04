import pytest
from fastapi import status
from app.db import models
from app.core.security import get_password_hash

def test_register_user(client):
    response = client.post(
        "/auth/register",
        json={"username": "test_citizen", "password": "password123", "role": "citizen"}
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["username"] == "test_citizen"
    assert data["role"] == "citizen"
    assert "id" in data
    assert "password" not in data

def test_register_duplicate_username(client):
    # Register once
    client.post(
        "/auth/register",
        json={"username": "duplicate_user", "password": "password123", "role": "citizen"}
    )
    # Register again
    response = client.post(
        "/auth/register",
        json={"username": "duplicate_user", "password": "password123", "role": "citizen"}
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Username already registered"

def test_login_success(client, db_session):
    # Seed user directly
    hashed_pw = get_password_hash("secretpass")
    user = models.User(username="login_test", hashed_password=hashed_pw, role="officer")
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/auth/login",
        data={"username": "login_test", "password": "secretpass"}
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "officer"
    assert data["username"] == "login_test"

def test_login_failure(client):
    response = client.post(
        "/auth/login",
        data={"username": "non_existent", "password": "wrong_password"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_rbac_protection(client, db_session):
    # Register officer
    hashed_pw = get_password_hash("pass123")
    officer = models.User(username="test_off", hashed_password=hashed_pw, role="officer")
    db_session.add(officer)
    
    # Register citizen
    citizen = models.User(username="test_cit", hashed_password=hashed_pw, role="citizen")
    db_session.add(citizen)
    db_session.commit()

    # Login officer
    login_off = client.post("/auth/login", data={"username": "test_off", "password": "pass123"})
    off_token = login_off.json()["access_token"]

    # Login citizen
    login_cit = client.post("/auth/login", data={"username": "test_cit", "password": "pass123"})
    cit_token = login_cit.json()["access_token"]

    # Access cases list route (requires standard auth)
    # Without token
    resp = client.get("/cases")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    # With citizen token (should accept since any auth user can read cases)
    resp = client.get("/cases", headers={"Authorization": f"Bearer {cit_token}"})
    assert resp.status_code == status.HTTP_200_OK

    # Create case route (requires officer/admin role)
    case_payload = {"title": "Scam Case 1", "severity": "High", "complaint_ids": []}
    
    # With citizen token (should be forbidden)
    resp = client.post(
        "/cases",
        json=case_payload,
        headers={"Authorization": f"Bearer {cit_token}"}
    )
    assert resp.status_code == status.HTTP_403_FORBIDDEN

    # With officer token (should succeed)
    resp = client.post(
        "/cases",
        json=case_payload,
        headers={"Authorization": f"Bearer {off_token}"}
    )
    assert resp.status_code == status.HTTP_201_CREATED
