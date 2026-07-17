import pytest
from fastapi import status
from sqlalchemy import text
from unittest.mock import patch, MagicMock
import hashlib

from app.db import models
from app.services.orchestrator import AIOrchestrator
from app.services.nlp_classifier import get_nlp_classifier
from app.services.graph_service import get_graph_service

@pytest.mark.asyncio
@patch("app.services.event_bus.RedisEventBus.publish_alert")
@patch("app.services.graph_service.GraphService.add_entity")
async def test_orchestrator_pipeline(mock_add_entity, mock_publish_alert, db_session):
    # Mock Neo4j and Redis alert publish to avoid external calls failing local test suite
    mock_add_entity.return_value = "dummy_hash"
    mock_publish_alert.return_value = None

    # Seed delhi jurisdiction if not exists
    jur = db_session.query(models.Jurisdiction).filter(models.Jurisdiction.name == "Delhi Police").first()
    if not jur:
        jur = models.Jurisdiction(name="Delhi Police")
        db_session.add(jur)
        db_session.commit()
        db_session.refresh(jur)
    
    # Update Delhi polygon
    db_session.execute(text(
        f"UPDATE jurisdictions SET polygon_geom = ST_GeogFromText("
        f"'POLYGON((77.10 28.50, 77.30 28.50, 77.30 28.70, 77.10 28.70, 77.10 28.50))') "
        f"WHERE id = {jur.id};"
    ))
    db_session.commit()

    # Seed an officer in Delhi Police if not exists
    officer = db_session.query(models.User).filter(models.User.username == "delhi_cop").first()
    if not officer:
        officer = models.User(username="delhi_cop", hashed_password="hashed_password", role="officer", jurisdiction_id=jur.id)
        db_session.add(officer)
        db_session.commit()
    
    # Seed pre-existing entity with high risk score to test graph-risk inheritance if not exists
    value_hash = hashlib.sha256("9998887776".encode()).hexdigest()
    entity = db_session.query(models.Entity).filter(models.Entity.value_hash == value_hash).first()
    if not entity:
        entity = models.Entity(type="phone", value="9998887776", value_hash=value_hash, risk_score=80.0)
        db_session.add(entity)
        db_session.commit()

    # Define a high-risk scam transcript containing legal coercion vocabulary
    transcript = "This is CBI officer. You are under digital arrest for money laundering. Go to Skype immediately."

    # Process signal
    complaint = await AIOrchestrator.process_complaint_signal(
        db=db_session,
        text_content=transcript,
        reporter_name="Bob Jones",
        phone="9998887776",
        lat=28.60, # Inside Delhi bounds
        lng=77.20
    )

    # 1. Verify PostgreSQL Ingestion
    assert complaint is not None
    assert complaint.reporter_name == "Bob Jones"
    assert complaint.phone == "9998887776"
    assert complaint.risk_score >= 60.0 # High risk due to CBI/digital arrest keywords + graph inheritance

    # 2. Verify PostGIS location coordinates
    coords = db_session.execute(
        text("SELECT ST_X(location::geometry), ST_Y(location::geometry) FROM complaints WHERE id = :id"),
        {"id": complaint.id}
    ).first()
    assert coords[0] == pytest.approx(77.20)
    assert coords[1] == pytest.approx(28.60)

    # 3. Verify Evidence Chain Hash Entry
    evidence_item = db_session.query(models.EvidenceItem).filter(models.EvidenceItem.complaint_id == complaint.id).first()
    assert evidence_item is not None
    assert evidence_item.type == "transcript"
    assert len(evidence_item.sha256_hash) == 64
    assert evidence_item.previous_hash is not None

    # 4. Verify Case Auto-creation & Assignment
    # Check if a case was automatically created and linked to this complaint
    linked_cases = complaint.cases
    assert len(linked_cases) == 1
    case = linked_cases[0]
    assert case.status == "Open"
    # Verify the assigned officer has the correct role and jurisdiction
    assert case.assigned_officer_id is not None
    assigned_officer = db_session.query(models.User).filter(models.User.id == case.assigned_officer_id).first()
    assert assigned_officer.role == "officer"
    assert assigned_officer.jurisdiction_id == jur.id

    # 5. Verify Neo4j & Redis publishes were triggered
    mock_add_entity.assert_called_once()
    assert mock_publish_alert.call_count == 2
    
    # First call: officer alert
    first_call_args = mock_publish_alert.call_args_list[0][1]
    assert first_call_args["target_role"] == "officer"
    assert "Suspicious Scam Call Ingested" in first_call_args["title"]
    
    # Second call: citizen alert
    second_call_args = mock_publish_alert.call_args_list[1][1]
    assert second_call_args["target_role"] == "citizen"
    assert "Your report has been analyzed" in second_call_args["title"]
    assert second_call_args.get("target_username") == "Bob Jones"
