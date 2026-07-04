from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.db import models
from app.schemas import case as case_schemas
from app.routers.auth import RoleChecker, get_current_user
from app.routers.complaints import fetch_complaint_by_id

router = APIRouter(prefix="/cases", tags=["cases"])

def fetch_case_by_id(db: Session, case_id: int):
    case = db.query(models.Case).filter(models.Case.id == case_id).first()
    if not case:
        return None
    # Enrich complaints with coordinates
    for c in case.complaints:
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
    return case

@router.post("", response_model=case_schemas.CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(case_in: case_schemas.CaseCreate, db: Session = Depends(get_db), current_user: models.User = Depends(RoleChecker(["officer", "admin"]))):
    case = models.Case(
        title=case_in.title,
        status=case_in.status,
        severity=case_in.severity,
        assigned_officer_id=case_in.assigned_officer_id
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # Link complaints
    if case_in.complaint_ids:
        complaints = db.query(models.Complaint).filter(models.Complaint.id.in_(case_in.complaint_ids)).all()
        for comp in complaints:
            case.complaints.append(comp)
        db.commit()

    return fetch_case_by_id(db, case.id)

@router.get("", response_model=List[case_schemas.CaseResponse])
def read_cases(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    cases = db.query(models.Case).offset(skip).limit(limit).all()
    for case in cases:
        for c in case.complaints:
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
    return cases

@router.get("/{id}", response_model=case_schemas.CaseResponse)
def read_case(id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    case = fetch_case_by_id(db, id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    return case

@router.put("/{id}", response_model=case_schemas.CaseResponse)
def update_case(id: int, case_update: case_schemas.CaseUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(RoleChecker(["officer", "admin"]))):
    case = db.query(models.Case).filter(models.Case.id == id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    update_data = case_update.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(case, key, val)
    
    db.commit()
    return fetch_case_by_id(db, id)
