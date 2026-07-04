from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ComplaintBase(BaseModel):
    reporter_name: Optional[str] = None
    phone: Optional[Optional[str]] = None
    text_content: str = Field(..., min_length=5, description="The transcript or text detail of the scam")
    location_lat: Optional[float] = Field(None, ge=-90, le=90)
    location_lng: Optional[float] = Field(None, ge=-180, le=180)

class ComplaintCreate(ComplaintBase):
    pass

class ComplaintRiskCheckRequest(BaseModel):
    text_content: str

class ComplaintRiskCheckResponse(BaseModel):
    risk_score: float
    risk_explanation: str

class ComplaintResponse(BaseModel):
    id: int
    reporter_name: Optional[str]
    phone: Optional[str]
    text_content: str
    risk_score: float
    risk_explanation: Optional[str]
    created_at: datetime
    location_lat: Optional[float] = None
    location_lng: Optional[float] = None
    case_id: Optional[int] = None

    class Config:
        from_attributes = True
