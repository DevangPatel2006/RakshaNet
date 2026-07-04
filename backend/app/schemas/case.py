from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.schemas.complaint import ComplaintResponse

class CaseBase(BaseModel):
    title: str
    status: Optional[str] = "Open"
    severity: Optional[str] = "Medium"
    assigned_officer_id: Optional[int] = None

class CaseCreate(CaseBase):
    complaint_ids: List[int] = []

class CaseUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    severity: Optional[str] = None
    assigned_officer_id: Optional[int] = None

class CaseResponse(CaseBase):
    id: int
    created_at: datetime
    complaints: List[ComplaintResponse] = []

    class Config:
        from_attributes = True
