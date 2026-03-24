from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class UserRegister(BaseModel):
    email: EmailStr
    password: str
    username: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: str

class UserInfo(BaseModel):
    user_id: str
    email: str
    username: Optional[str] = None

class FileUploadResponse(BaseModel):
    filename: str
    stored_as: str
    size: int
    path: str
    public_url: str
    uploaded_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "filename": "spectrum.fits",
                "stored_as": "20260324_151500_spectrum.fits",
                "size": 1024000,
                "path": "/tmp/astrosense_uploads/user_id/20260324_151500_spectrum.fits",
                "public_url": "/api/files/download/20260324_151500_spectrum.fits",
                "uploaded_at": "2026-03-24T15:15:00.000000"
            }
        }

class UserFile(BaseModel):
    name: str
    size: int
    created: Optional[str] = None
    public_url: Optional[str] = None
