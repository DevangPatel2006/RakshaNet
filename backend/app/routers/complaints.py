from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db import models
from app.schemas import complaint as complaint_schemas
from app.routers.auth import RoleChecker, get_current_user

from app.services.orchestrator import AIOrchestrator

router = APIRouter(prefix="/complaints", tags=["complaints"])

def fetch_complaint_by_id(db: Session, complaint_id: int):
    c = db.query(models.Complaint).filter(models.Complaint.id == complaint_id).first()
    if not c:
        return None
    
    # Expose case ID from many-to-many relationship
    c.case_id = c.cases[0].id if c.cases else None

    coords = db.execute(
        text("SELECT ST_X(location::geometry), ST_Y(location::geometry) FROM complaints WHERE id = :id"),
        {"id": complaint_id}
    ).first()
    if coords and coords[0] is not None and coords[1] is not None:
        c.location_lng = coords[0]
        c.location_lat = coords[1]
    else:
        c.location_lng = None
        c.location_lat = None
    return c

@router.post("", response_model=complaint_schemas.ComplaintResponse, status_code=status.HTTP_201_CREATED)
async def create_complaint(complaint_in: complaint_schemas.ComplaintCreate, db: Session = Depends(get_db)):
    complaint = await AIOrchestrator.process_complaint_signal(
        db=db,
        text_content=complaint_in.text_content,
        reporter_name=complaint_in.reporter_name,
        phone=complaint_in.phone,
        lat=complaint_in.location_lat,
        lng=complaint_in.location_lng
    )
    # Fetch coordinates representation correctly for serialization
    return fetch_complaint_by_id(db, complaint.id)

@router.get("", response_model=List[complaint_schemas.ComplaintResponse])
def read_complaints(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    complaints = db.query(models.Complaint).offset(skip).limit(limit).all()
    for c in complaints:
        c.case_id = c.cases[0].id if c.cases else None
        coords = db.execute(
            text("SELECT ST_X(location::geometry), ST_Y(location::geometry) FROM complaints WHERE id = :id"),
            {"id": c.id}
        ).first()
        if coords and coords[0] is not None and coords[1] is not None:
            c.location_lng = coords[0]
            c.location_lat = coords[1]
        else:
            c.location_lng = None
            c.location_lat = None
    return complaints

@router.get("/{id}", response_model=complaint_schemas.ComplaintResponse)
def read_complaint(id: int, db: Session = Depends(get_db)):
    c = fetch_complaint_by_id(db, id)
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    return c

@router.post("/{id}/risk-check", response_model=complaint_schemas.ComplaintRiskCheckResponse)
def check_complaint_risk(id: int, db: Session = Depends(get_db)):
    c = fetch_complaint_by_id(db, id)
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found"
        )
    # Return placeholder risk score/explanation for now - replaced by Risk Fusion / Orchestrator in Phase 7/11
    return {
        "risk_score": c.risk_score,
        "risk_explanation": c.risk_explanation or "Scam analysis pending orchestrator execution."
    }
