from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.user import UserRole

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: str
    full_name: str
    email: str

class PasswordResetRequest(BaseModel):
    new_password: str

class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: UserRole = UserRole.AGENT
    mobile: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    mobile: Optional[str] = None
    is_active: Optional[bool] = None
