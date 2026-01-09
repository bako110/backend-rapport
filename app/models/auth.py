from pydantic import BaseModel, EmailStr
from typing import Optional


class Token(BaseModel):
    """Modèle pour le token JWT"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Données contenues dans le token JWT"""
    user_id: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    """Modèle pour la requête de connexion"""
    email: str
    password: str


class RegisterRequest(BaseModel):
    """Modèle pour la requête d'inscription"""
    email: str
    name: str
    password: str


class LoginResponse(BaseModel):
    """Modèle pour la réponse de connexion"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict