import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr

from app.models import UserRole, VideoStatus


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.learner


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    role: UserRole
    is_active: str
    created_at: datetime

    class Config:
        from_attributes = True


class VideoOut(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    category: str
    file_url: str
    status: VideoStatus
    uploaded_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class TranscriptSegmentOut(BaseModel):
    id: uuid.UUID
    video_id: uuid.UUID
    start_time: float
    end_time: float
    text: str

    class Config:
        from_attributes = True