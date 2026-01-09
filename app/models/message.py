from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from app.models.user import PyObjectId


class MessageBase(BaseModel):
    """Modèle de base pour un message"""
    content: str = Field(..., min_length=1, max_length=2000, description="Contenu du message")
    subject: Optional[str] = Field(None, max_length=200, description="Sujet du message")


class MessageCreate(MessageBase):
    """Modèle pour créer un nouveau message"""
    receiver_id: str = Field(..., description="ID du destinataire")


class MessageBroadcast(MessageBase):
    """Modèle pour envoyer un message à plusieurs destinataires"""
    receiver_ids: List[str] = Field(..., min_items=1, description="Liste des IDs des destinataires")


class MessageInDB(MessageBase):
    """Modèle message stocké en base de données"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    sender_id: PyObjectId  # Toujours un admin
    receiver_id: PyObjectId  # Toujours un employé
    read_status: bool = Field(default=False, description="Statut de lecture")
    read_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_encoders": {ObjectId: str},
        "populate_by_name": True
    }


class MessageResponse(MessageBase):
    """Modèle de réponse pour un message"""
    id: str = Field(alias="_id")
    sender_id: str
    sender_name: Optional[str] = None  # Sera ajouté lors de la récupération
    receiver_id: str
    receiver_name: Optional[str] = None  # Sera ajouté lors de la récupération
    read_status: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    model_config = {
        "json_encoders": {ObjectId: str},
        "populate_by_name": True
    }


class MessageSummary(BaseModel):
    """Modèle pour le résumé d'un message (liste)"""
    id: str
    subject: Optional[str]
    content_preview: str  # Premiers caractères du contenu
    sender_name: str
    read_status: bool
    created_at: datetime

    model_config = {
        "json_encoders": {ObjectId: str}
    }


class MessageStats(BaseModel):
    """Modèle pour les statistiques des messages"""
    total_messages: int
    unread_messages: int
    messages_this_week: int