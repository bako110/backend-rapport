from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, Literal
from datetime import datetime
from bson import ObjectId


class PyObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")
        return field_schema


class UserBase(BaseModel):
    """Modèle de base pour un utilisateur"""
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    role: Literal["employee", "admin"] = "employee"
    status: Literal["active", "inactive"] = "active"


class UserCreate(UserBase):
    """Modèle pour créer un nouvel utilisateur"""
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    """Modèle pour mettre à jour un utilisateur"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    role: Optional[Literal["employee", "admin"]] = None
    status: Optional[Literal["active", "inactive"]] = None


class UserInDB(UserBase):
    """Modèle utilisateur stocké en base de données"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_encoders": {ObjectId: str},
        "populate_by_name": True
    }


class UserResponse(UserBase):
    """Modèle de réponse utilisateur (sans mot de passe)"""
    id: str = Field(alias="_id")
    created_at: datetime
    updated_at: datetime

    model_config = {
        "json_encoders": {ObjectId: str},
        "populate_by_name": True
    }


class UserProfile(BaseModel):
    """Modèle pour le profil utilisateur"""
    id: str
    email: EmailStr
    name: str
    role: str
    status: str
    created_at: datetime

    model_config = {
        "json_encoders": {ObjectId: str}
    }