from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app.models.user import PyObjectId
import re


class TaskItem(BaseModel):
    """Modèle pour une tâche dans un rapport"""
    title: str = Field(..., min_length=1, max_length=200)
    hours: float = Field(..., ge=0, description="Nombre d'heures passées sur cette tâche")
    notes: Optional[str] = Field(None, max_length=500, description="Notes optionnelles")
    project: Optional[str] = Field(None, max_length=100, description="Projet associé (optionnel)")


class ReportBase(BaseModel):
    """Modèle de base pour un rapport hebdomadaire"""
    week_iso: str = Field(..., description="Semaine au format ISO (YYYY-Www)")
    tasks: List[TaskItem] = Field(..., min_length=1, description="Liste des tâches")
    difficulties: Optional[str] = Field(None, max_length=1000, description="Difficultés rencontrées")
    remarks: Optional[str] = Field(None, max_length=1000, description="Remarques générales")
    
    @field_validator('week_iso')
    @classmethod
    def validate_week_iso(cls, v):
        # Format: YYYY-Www (ex: 2024-W01)
        pattern = r'^\d{4}-W\d{2}$'
        if not re.match(pattern, v):
            raise ValueError('Format de semaine invalide. Utilisez YYYY-Www (ex: 2024-W01)')
        return v
    
    @field_validator('tasks')
    @classmethod
    def validate_tasks(cls, v):
        if not v:
            raise ValueError('Au moins une tâche est requise')
        return v


class ReportCreate(ReportBase):
    """Modèle pour créer un nouveau rapport"""
    pass


class ReportUpdate(BaseModel):
    """Modèle pour mettre à jour un rapport"""
    tasks: Optional[List[TaskItem]] = Field(None, min_length=1)
    difficulties: Optional[str] = Field(None, max_length=1000)
    remarks: Optional[str] = Field(None, max_length=1000)


class ReportInDB(ReportBase):
    """Modèle rapport stocké en base de données"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    total_hours: float = Field(default=0.0, description="Total des heures calculé automatiquement")
    status: str = Field(default="submitted", description="Statut du rapport")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {
        "json_encoders": {ObjectId: str},
        "populate_by_name": True
    }

    def calculate_total_hours(self):
        """Calcule le total des heures"""
        self.total_hours = sum(task.hours for task in self.tasks)


class ReportResponse(ReportBase):
    """Modèle de réponse pour un rapport"""
    id: str = Field(alias="_id")
    user_id: str
    user_name: Optional[str] = None  # Sera ajouté lors de la récupération
    total_hours: float
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {
        "json_encoders": {ObjectId: str},
        "populate_by_name": True
    }


class ReportSummary(BaseModel):
    """Modèle pour le résumé d'un rapport"""
    id: str
    week_iso: str
    user_name: str
    total_hours: float
    tasks_count: int
    created_at: datetime
    has_comments: bool = False

    model_config = {
        "json_encoders": {ObjectId: str}
    }


class WeeklyStats(BaseModel):
    """Modèle pour les statistiques hebdomadaires"""
    week_iso: str
    total_reports: int
    total_hours: float
    employees_reported: int
    average_hours_per_employee: float