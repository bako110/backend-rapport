from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from pydantic import BaseModel
from app.models.report import (
    ReportCreate, ReportResponse, ReportUpdate, ReportInDB, 
    ReportSummary, WeeklyStats
)
from app.middleware.auth import (
    require_employee, require_admin, get_current_user_from_db, 
    require_active_user
)
from app.core.database import get_database
from app.utils.datetime_utils import validate_iso_week_format, get_current_iso_week
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# Modèle pour une section de rapport
class ReportSection(BaseModel):
    title: str
    description: str


# Modèle simplifié pour la création depuis le mobile
class SimpleReportCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    category: str
    sections: Optional[List[ReportSection]] = []


class SimpleReportUpdate(BaseModel):
    title: str
    description: Optional[str] = ""
    category: str
    sections: Optional[List[ReportSection]] = []


@router.post("/simple", response_model=dict, summary="Créer un rapport simple")
async def create_simple_report(
    report_data: SimpleReportCreate,
    current_user: dict = Depends(require_active_user),
    db = Depends(get_database)
):
    """
    Créer un nouveau rapport avec un format simple (title, description, category).
    Accessible à tous les utilisateurs authentifiés.
    """
    try:
        # Validation: au moins une section requise
        if not report_data.sections or len(report_data.sections) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Au moins une section est requise"
            )
        
        # Créer le rapport avec les champs simples
        now = datetime.utcnow()
        report_doc = {
            "title": report_data.title,
            "description": report_data.description,
            "category": report_data.category,
            "sections": [section.dict() for section in report_data.sections] if report_data.sections else [],
            "status": "pending",
            "created_by": current_user["name"],
            "user_id": ObjectId(current_user["_id"]),
            "created_at": now,
            "updated_at": now
        }
        
        # Insérer en base
        result = await db.reports.insert_one(report_doc)
        
        logger.info(f"Rapport simple créé par {current_user['name']}: {report_data.title}")
        
        return {
            "id": str(result.inserted_id),
            "_id": str(result.inserted_id),
            "title": report_data.title,
            "description": report_data.description,
            "category": report_data.category,
            "sections": [section.dict() for section in report_data.sections] if report_data.sections else [],
            "status": "pending",
            "created_by": current_user["name"],
            "created_at": now.isoformat(),
            "updated_at": now.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la création du rapport simple: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la création du rapport: {str(e)}"
        )


@router.put("/simple/{report_id}", response_model=dict, summary="Mettre à jour un rapport simple")
async def update_simple_report(
    report_id: str,
    report_data: SimpleReportUpdate,
    current_user: dict = Depends(require_active_user),
    db = Depends(get_database)
):
    """
    Mettre à jour un rapport simple (title, description, category).
    Seul le créateur peut modifier son rapport et uniquement si le statut est 'pending'.
    """
    try:
        if not ObjectId.is_valid(report_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID rapport invalide"
            )
        
        # Vérifier que le rapport existe et appartient à l'utilisateur
        existing_report = await db.reports.find_one({
            "_id": ObjectId(report_id),
            "user_id": ObjectId(current_user["_id"])
        })
        
        if not existing_report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rapport non trouvé ou accès non autorisé"
            )
        
        # Vérifier que le rapport est en attente
        if existing_report.get("status") != "pending":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seuls les rapports en attente peuvent être modifiés"
            )
        
        # Validation: au moins une section requise
        if not report_data.sections or len(report_data.sections) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Au moins une section est requise"
            )
        
        # Mettre à jour le rapport
        now = datetime.utcnow()
        update_data = {
            "title": report_data.title,
            "description": report_data.description,
            "category": report_data.category,
            "sections": [section.dict() for section in report_data.sections] if report_data.sections else [],
            "updated_at": now
        }
        
        await db.reports.update_one(
            {"_id": ObjectId(report_id)},
            {"$set": update_data}
        )
        
        logger.info(f"Rapport simple modifié par {current_user['name']}: {report_id}")
        
        return {
            "id": report_id,
            "_id": report_id,
            "title": report_data.title,
            "description": report_data.description,
            "category": report_data.category,
            "sections": [section.dict() for section in report_data.sections] if report_data.sections else [],
            "status": existing_report.get("status", "pending"),
            "created_by": existing_report.get("created_by", current_user["name"]),
            "created_at": existing_report.get("created_at", now).isoformat(),
            "updated_at": now.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la modification du rapport simple: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur lors de la modification du rapport: {str(e)}"
        )


@router.post("/", response_model=ReportResponse, summary="Créer un rapport hebdomadaire")
async def create_report(
    report_data: ReportCreate,
    current_user: dict = Depends(require_active_user),
    db = Depends(get_database)
):
    """
    Créer un nouveau rapport hebdomadaire.
    
    - **week_iso**: Semaine au format YYYY-Www
    - **tasks**: Liste des tâches avec heures
    - **difficulties**: Difficultés rencontrées (optionnel)
    - **remarks**: Remarques générales (optionnel)
    """
    try:
        # Vérifier que c'est un employé
        if current_user.get("role") != "employee":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Seuls les employés peuvent créer des rapports"
            )
        
        # Vérifier l'unicité (un rapport par employé par semaine)
        existing_report = await db.reports.find_one({
            "user_id": ObjectId(current_user["_id"]),
            "week_iso": report_data.week_iso
        })
        
        if existing_report:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Un rapport existe déjà pour la semaine {report_data.week_iso}"
            )
        
        # Créer le rapport
        report_in_db = ReportInDB(
            user_id=ObjectId(current_user["_id"]),
            week_iso=report_data.week_iso,
            tasks=report_data.tasks,
            difficulties=report_data.difficulties,
            remarks=report_data.remarks
        )
        
        # Calculer le total des heures
        report_in_db.calculate_total_hours()
        
        # Insérer en base
        result = await db.reports.insert_one(report_in_db.model_dump(by_alias=True))
        
        # Récupérer le rapport créé
        created_report = await db.reports.find_one({"_id": result.inserted_id})
        
        logger.info(f"Rapport créé pour {current_user['name']} - semaine {report_data.week_iso}")
        
        return ReportResponse(
            _id=str(created_report["_id"]),
            user_id=str(created_report["user_id"]),
            user_name=current_user["name"],
            week_iso=created_report["week_iso"],
            tasks=created_report["tasks"],
            difficulties=created_report["difficulties"],
            remarks=created_report["remarks"],
            total_hours=created_report["total_hours"],
            status=created_report["status"],
            created_at=created_report["created_at"],
            updated_at=created_report["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la création du rapport: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création du rapport"
        )


@router.get("/", response_model=List[dict], summary="Liste des rapports")
async def get_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    week_iso: Optional[str] = Query(None, description="Filtrer par semaine"),
    user_id: Optional[str] = Query(None, description="Filtrer par utilisateur"),
    current_user: dict = Depends(get_current_user_from_db),
    db = Depends(get_database)
):
    """
    Récupérer la liste des rapports.
    
    - **Tous les utilisateurs**: Peuvent voir tous les rapports
    """
    try:
        # Construire les filtres
        filters = {}
        
        # Filtrer par user_id si spécifié
        if user_id:
            if not ObjectId.is_valid(user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ID utilisateur invalide"
                )
            filters["user_id"] = ObjectId(user_id)
        
        # Filtrer par semaine si spécifié
        if week_iso:
            if not validate_iso_week_format(week_iso):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Format de semaine invalide"
                )
            filters["week_iso"] = week_iso
        
        # Récupérer les rapports avec les infos utilisateur
        pipeline = [
            {"$match": filters},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user_info"
            }},
            {"$lookup": {
                "from": "comments",
                "localField": "_id",
                "foreignField": "report_id",
                "as": "comments"
            }},
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        cursor = db.reports.aggregate(pipeline)
        reports = await cursor.to_list(length=limit)
        
        # Convertir en format compatible avec le frontend
        report_summaries = []
        for report in reports:
            user_info = report["user_info"][0] if report.get("user_info") else {}
            
            # Format simple (title, description, category)
            if "title" in report:
                report_summaries.append({
                    "id": str(report["_id"]),
                    "_id": str(report["_id"]),
                    "title": report.get("title", "Sans titre"),
                    "description": report.get("description", ""),
                    "category": report.get("category", ""),
                    "sections": report.get("sections", []),
                    "status": report.get("status", "pending"),
                    "created_by": report.get("created_by", user_info.get("name", "Inconnu")),
                    "created_at": report["created_at"].isoformat() if isinstance(report.get("created_at"), datetime) else report.get("created_at", ""),
                    "updated_at": report["updated_at"].isoformat() if isinstance(report.get("updated_at"), datetime) else report.get("updated_at", "")
                })
            # Format complexe (week_iso, tasks, etc.)
            else:
                report_summaries.append(ReportSummary(
                    id=str(report["_id"]),
                    week_iso=report.get("week_iso", ""),
                    user_name=user_info.get("name", "Utilisateur inconnu"),
                    total_hours=report.get("total_hours", 0),
                    tasks_count=len(report.get("tasks", [])),
                    created_at=report.get("created_at"),
                    has_comments=len(report.get("comments", [])) > 0
                ))
        
        return report_summaries
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des rapports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des rapports"
        )


@router.get("/{report_id}", response_model=ReportResponse, summary="Détails d'un rapport")
async def get_report(
    report_id: str,
    current_user: dict = Depends(get_current_user_from_db),
    db = Depends(get_database)
):
    """
    Récupérer les détails d'un rapport spécifique.
    """
    try:
        if not ObjectId.is_valid(report_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID rapport invalide"
            )
        
        # Récupérer le rapport avec les infos utilisateur
        pipeline = [
            {"$match": {"_id": ObjectId(report_id)}},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user_info"
            }}
        ]
        
        cursor = db.reports.aggregate(pipeline)
        reports = await cursor.to_list(length=1)
        
        if not reports:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rapport non trouvé"
            )
        
        report = reports[0]
        user_info = report["user_info"][0] if report["user_info"] else {}
        
        # Vérifier les permissions
        if (current_user.get("role") == "employee" and 
            str(report["user_id"]) != str(current_user["_id"])):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à ce rapport"
            )
        
        return ReportResponse(
            _id=str(report["_id"]),
            user_id=str(report["user_id"]),
            user_name=user_info.get("name", "Utilisateur inconnu"),
            week_iso=report["week_iso"],
            tasks=report["tasks"],
            difficulties=report["difficulties"],
            remarks=report["remarks"],
            total_hours=report["total_hours"],
            status=report["status"],
            created_at=report["created_at"],
            updated_at=report["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du rapport: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du rapport"
        )


@router.put("/{report_id}", response_model=ReportResponse, summary="Mettre à jour un rapport")
async def update_report(
    report_id: str,
    report_update: ReportUpdate,
    current_user: dict = Depends(require_employee),
    db = Depends(get_database)
):
    """
    Mettre à jour un rapport existant (Employé propriétaire seulement).
    """
    try:
        if not ObjectId.is_valid(report_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID rapport invalide"
            )
        
        # Vérifier que le rapport existe et appartient à l'utilisateur
        existing_report = await db.reports.find_one({
            "_id": ObjectId(report_id),
            "user_id": ObjectId(current_user["_id"])
        })
        
        if not existing_report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rapport non trouvé ou accès non autorisé"
            )
        
        # Préparer les données de mise à jour
        update_data = {}
        if report_update.tasks is not None:
            update_data["tasks"] = [task.model_dump() for task in report_update.tasks]
            # Recalculer le total des heures
            update_data["total_hours"] = sum(task.hours for task in report_update.tasks)
        
        if report_update.difficulties is not None:
            update_data["difficulties"] = report_update.difficulties
        
        if report_update.remarks is not None:
            update_data["remarks"] = report_update.remarks
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Mettre à jour en base
        await db.reports.update_one(
            {"_id": ObjectId(report_id)},
            {"$set": update_data}
        )
        
        # Récupérer le rapport mis à jour
        updated_report = await db.reports.find_one({"_id": ObjectId(report_id)})
        
        logger.info(f"Rapport mis à jour: {report_id} par {current_user['name']}")
        
        return ReportResponse(
            _id=str(updated_report["_id"]),
            user_id=str(updated_report["user_id"]),
            user_name=current_user["name"],
            week_iso=updated_report["week_iso"],
            tasks=updated_report["tasks"],
            difficulties=updated_report["difficulties"],
            remarks=updated_report["remarks"],
            total_hours=updated_report["total_hours"],
            status=updated_report["status"],
            created_at=updated_report["created_at"],
            updated_at=updated_report["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du rapport: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour du rapport"
        )


@router.delete("/{report_id}", summary="Supprimer un rapport")
async def delete_report(
    report_id: str,
    current_user: dict = Depends(require_employee),
    db = Depends(get_database)
):
    """
    Supprimer un rapport (Employé propriétaire seulement).
    """
    try:
        if not ObjectId.is_valid(report_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID rapport invalide"
            )
        
        # Vérifier que le rapport existe et appartient à l'utilisateur
        existing_report = await db.reports.find_one({
            "_id": ObjectId(report_id),
            "user_id": ObjectId(current_user["_id"])
        })
        
        if not existing_report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rapport non trouvé ou accès non autorisé"
            )
        
        # Supprimer les commentaires associés
        await db.comments.delete_many({"report_id": ObjectId(report_id)})
        
        # Supprimer le rapport
        await db.reports.delete_one({"_id": ObjectId(report_id)})
        
        logger.info(f"Rapport supprimé: {report_id} par {current_user['name']}")
        
        return {"message": "Rapport supprimé avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du rapport: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression du rapport"
        )


@router.get("/stats/weekly", response_model=List[WeeklyStats], summary="Statistiques hebdomadaires")
async def get_weekly_stats(
    start_week: Optional[str] = Query(None, description="Semaine de début"),
    end_week: Optional[str] = Query(None, description="Semaine de fin"),
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Obtenir les statistiques hebdomadaires (Admin seulement).
    """
    try:
        # Construire les filtres
        filters = {}
        if start_week and end_week:
            if not validate_iso_week_format(start_week) or not validate_iso_week_format(end_week):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Format de semaine invalide"
                )
            filters["week_iso"] = {"$gte": start_week, "$lte": end_week}
        elif start_week:
            if not validate_iso_week_format(start_week):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Format de semaine invalide"
                )
            filters["week_iso"] = {"$gte": start_week}
        
        # Pipeline d'agrégation
        pipeline = [
            {"$match": filters},
            {"$group": {
                "_id": "$week_iso",
                "total_reports": {"$sum": 1},
                "total_hours": {"$sum": "$total_hours"},
                "employees": {"$addToSet": "$user_id"}
            }},
            {"$project": {
                "week_iso": "$_id",
                "total_reports": 1,
                "total_hours": 1,
                "employees_reported": {"$size": "$employees"},
                "average_hours_per_employee": {
                    "$cond": {
                        "if": {"$gt": [{"$size": "$employees"}, 0]},
                        "then": {"$divide": ["$total_hours", {"$size": "$employees"}]},
                        "else": 0
                    }
                }
            }},
            {"$sort": {"week_iso": -1}}
        ]
        
        cursor = db.reports.aggregate(pipeline)
        stats = await cursor.to_list(length=None)
        
        # Convertir en WeeklyStats
        weekly_stats = []
        for stat in stats:
            weekly_stats.append(WeeklyStats(
                week_iso=stat["week_iso"],
                total_reports=stat["total_reports"],
                total_hours=stat["total_hours"],
                employees_reported=stat["employees_reported"],
                average_hours_per_employee=round(stat["average_hours_per_employee"], 2)
            ))
        
        return weekly_stats
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des statistiques"
        )