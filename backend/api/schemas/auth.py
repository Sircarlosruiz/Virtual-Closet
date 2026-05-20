from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters")
    nombre_negocio: str = Field(..., min_length=1, max_length=255)


class RegisterResponse(BaseModel):
    id: UUID
    email: str
    nombre_negocio: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    pass


class MeResponse(BaseModel):
    id: UUID
    email: str
    nombre_negocio: str
    plan: str
    trial_activo: bool
    trial_expira_en: datetime
    prendas_count: int = 0
