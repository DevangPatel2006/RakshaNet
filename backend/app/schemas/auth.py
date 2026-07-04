from typing import Optional
from pydantic import BaseModel, Field

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    role: str = Field(..., description="citizen, officer, bank_analyst, telecom_analyst, admin")
    jurisdiction_id: Optional[int] = None

class UserResponse(UserBase):
    id: int
    role: str
    jurisdiction_id: Optional[int] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    role: Optional[str] = None
