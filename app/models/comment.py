from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from bson import ObjectId
from app.models.user import PyObjectId


class CommentBase(BaseModel):
    """Modèle de base pour un commentaire"""
    content: str = Field(..., min_length=1, max_length=2000, description="Contenu du commentaire")


class CommentCreate(CommentBase):
    """Modèle pour créer un nouveau commentaire"""
    report_id: str = Field(..., description="ID du rapport associé")


class CommentUpdate(BaseModel):
    """Modèle pour mettre à jour un commentaire"""
    content: str = Field(..., min_length=1, max_length=2000)


class CommentInDB(CommentBase):
    """Modèle commentaire stocké en base de données"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    report_id: PyObjectId
    admin_id: PyObjectId
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_encoders": {ObjectId: str},
        "populate_by_name": True
    }


class CommentResponse(CommentBase):
    """Modèle de réponse pour un commentaire"""
    id: str = Field(alias="_id")
    report_id: str
    admin_id: str
    admin_name: Optional[str] = None  # Sera ajouté lors de la récupération
    created_at: datetime
    updated_at: datetime

    model_config = {
        "json_encoders": {ObjectId: str},
        "populate_by_name": True
    }