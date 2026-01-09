from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from typing import Optional, List
from app.middleware.auth import require_admin, get_current_user_from_db
from app.core.database import get_database
from app.services.csv_export import CSVExportService
from app.services.pdf_export import PDFExportService
from app.utils.datetime_utils import validate_iso_week_format, format_datetime_for_display
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

csv_service = CSVExportService()
pdf_service = PDFExportService()


@router.get("/reports/csv", summary="Export rapports en CSV")
async def export_reports_csv(
    start_week: Optional[str] = Query(None, description="Semaine de début (YYYY-Www)"),
    end_week: Optional[str] = Query(None, description="Semaine de fin (YYYY-Www)"),
    user_id: Optional[str] = Query(None, description="Filtrer par employé"),
    include_tasks_detail: bool = Query(True, description="Inclure le détail des tâches"),
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Exporter les rapports en format CSV (Admin seulement).
    
    - **start_week**: Semaine de début pour filtrer
    - **end_week**: Semaine de fin pour filtrer  
    - **user_id**: ID employé pour filtrer
    - **include_tasks_detail**: Inclure détail des tâches ou résumé seulement
    """
    try:
        # Construire les filtres
        filters = {}
        
        # Filtrage par période
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
        elif end_week:
            if not validate_iso_week_format(end_week):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Format de semaine invalide"
                )
            filters["week_iso"] = {"$lte": end_week}
        
        # Filtrage par employé
        if user_id:
            if not ObjectId.is_valid(user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ID utilisateur invalide"
                )
            filters["user_id"] = ObjectId(user_id)
        
        # Récupérer les rapports avec infos utilisateur
        pipeline = [
            {"$match": filters},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user_info"
            }},
            {"$sort": {"week_iso": -1, "created_at": -1}}
        ]
        
        cursor = db.reports.aggregate(pipeline)
        reports = await cursor.to_list(length=None)
        
        # Enrichir les données
        enriched_reports = []
        for report in reports:
            user_info = report["user_info"][0] if report["user_info"] else {}
            
            enriched_report = {
                **report,
                "user_name": user_info.get("name", "Utilisateur inconnu"),
                "user_email": user_info.get("email", "")
            }
            enriched_reports.append(enriched_report)
        
        # Générer le CSV
        csv_content = csv_service.export_reports_to_csv(enriched_reports, include_tasks_detail)
        
        # Préparer le nom du fichier
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rapports_sahelys_{timestamp}.csv"
        
        # Retourner le fichier CSV
        return Response(
            content=csv_content.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'export CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'export CSV"
        )


@router.get("/reports/pdf", summary="Export rapports en PDF")
async def export_reports_pdf(
    start_week: Optional[str] = Query(None, description="Semaine de début (YYYY-Www)"),
    end_week: Optional[str] = Query(None, description="Semaine de fin (YYYY-Www)"),
    user_id: Optional[str] = Query(None, description="Filtrer par employé"),
    title: Optional[str] = Query("Rapports Hebdomadaires Sahelys", description="Titre du document"),
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Exporter les rapports en format PDF (Admin seulement).
    """
    try:
        # Mêmes filtres que pour le CSV
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
        elif end_week:
            if not validate_iso_week_format(end_week):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Format de semaine invalide"
                )
            filters["week_iso"] = {"$lte": end_week}
        
        if user_id:
            if not ObjectId.is_valid(user_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ID utilisateur invalide"
                )
            filters["user_id"] = ObjectId(user_id)
        
        # Récupérer les rapports
        pipeline = [
            {"$match": filters},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user_info"
            }},
            {"$sort": {"week_iso": -1, "created_at": -1}}
        ]
        
        cursor = db.reports.aggregate(pipeline)
        reports = await cursor.to_list(length=None)
        
        # Enrichir les données
        enriched_reports = []
        for report in reports:
            user_info = report["user_info"][0] if report["user_info"] else {}
            
            enriched_report = {
                **report,
                "user_name": user_info.get("name", "Utilisateur inconnu"),
                "user_email": user_info.get("email", "")
            }
            enriched_reports.append(enriched_report)
        
        # Générer le PDF
        pdf_content = pdf_service.export_reports_to_pdf(enriched_reports, title)
        
        # Préparer le nom du fichier
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rapports_sahelys_{timestamp}.pdf"
        
        # Retourner le fichier PDF
        return Response(
            content=pdf_content.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'export PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'export PDF"
        )


@router.get("/weekly-summary/{week_iso}/pdf", summary="Export résumé hebdomadaire PDF")
async def export_weekly_summary_pdf(
    week_iso: str,
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Exporter un résumé hebdomadaire en PDF (Admin seulement).
    """
    try:
        # Valider le format de la semaine
        if not validate_iso_week_format(week_iso):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format de semaine invalide"
            )
        
        # Récupérer les statistiques de la semaine
        stats_pipeline = [
            {"$match": {"week_iso": week_iso}},
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
            }}
        ]
        
        cursor = db.reports.aggregate(stats_pipeline)
        stats = await cursor.to_list(length=1)
        
        if not stats:
            week_stats = {
                "week_iso": week_iso,
                "total_reports": 0,
                "total_hours": 0,
                "employees_reported": 0,
                "average_hours_per_employee": 0
            }
        else:
            week_stats = stats[0]
        
        # Récupérer les rapports de la semaine
        reports_pipeline = [
            {"$match": {"week_iso": week_iso}},
            {"$lookup": {
                "from": "users",
                "localField": "user_id",
                "foreignField": "_id",
                "as": "user_info"
            }},
            {"$sort": {"user_id": 1}}
        ]
        
        cursor = db.reports.aggregate(reports_pipeline)
        reports = await cursor.to_list(length=None)
        
        # Enrichir les données
        enriched_reports = []
        for report in reports:
            user_info = report["user_info"][0] if report["user_info"] else {}
            
            enriched_report = {
                **report,
                "user_name": user_info.get("name", "Utilisateur inconnu"),
                "user_email": user_info.get("email", "")
            }
            enriched_reports.append(enriched_report)
        
        # Générer le PDF du résumé
        pdf_content = pdf_service.export_weekly_summary_to_pdf(week_stats, enriched_reports)
        
        # Préparer le nom du fichier
        filename = f"resume_hebdomadaire_{week_iso}.pdf"
        
        # Retourner le fichier PDF
        return Response(
            content=pdf_content.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'export du résumé hebdomadaire: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'export du résumé hebdomadaire"
        )


@router.get("/users/csv", summary="Export utilisateurs en CSV")
async def export_users_csv(
    role: Optional[str] = Query(None, description="Filtrer par rôle"),
    status: Optional[str] = Query(None, description="Filtrer par statut"),
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Exporter les utilisateurs en format CSV (Admin seulement).
    """
    try:
        # Construire les filtres
        filters = {}
        if role:
            filters["role"] = role
        if status:
            filters["status"] = status
        
        # Récupérer les utilisateurs
        cursor = db.users.find(filters).sort("name", 1)
        users = await cursor.to_list(length=None)
        
        # Générer le CSV
        csv_content = csv_service.export_users_to_csv(users)
        
        # Préparer le nom du fichier
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"utilisateurs_sahelys_{timestamp}.csv"
        
        # Retourner le fichier CSV
        return Response(
            content=csv_content.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de l'export des utilisateurs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'export des utilisateurs"
        )


@router.get("/messages/csv", summary="Export messages en CSV")
async def export_messages_csv(
    start_date: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)"),
    sender_id: Optional[str] = Query(None, description="ID expéditeur"),
    receiver_id: Optional[str] = Query(None, description="ID destinataire"),
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Exporter les messages en format CSV (Admin seulement).
    """
    try:
        # Construire les filtres
        filters = {}
        
        # Filtrage par dates
        if start_date or end_date:
            date_filter = {}
            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    date_filter["$gte"] = start_dt
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Format de date invalide pour start_date"
                    )
            
            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    end_dt = end_dt.replace(hour=23, minute=59, second=59)
                    date_filter["$lte"] = end_dt
                except ValueError:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Format de date invalide pour end_date"
                    )
            
            filters["created_at"] = date_filter
        
        # Filtrage par expéditeur/destinataire
        if sender_id:
            if not ObjectId.is_valid(sender_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ID expéditeur invalide"
                )
            filters["sender_id"] = ObjectId(sender_id)
        
        if receiver_id:
            if not ObjectId.is_valid(receiver_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ID destinataire invalide"
                )
            filters["receiver_id"] = ObjectId(receiver_id)
        
        # Récupérer les messages avec infos utilisateurs
        pipeline = [
            {"$match": filters},
            {"$lookup": {
                "from": "users",
                "localField": "sender_id",
                "foreignField": "_id",
                "as": "sender_info"
            }},
            {"$lookup": {
                "from": "users",
                "localField": "receiver_id",
                "foreignField": "_id",
                "as": "receiver_info"
            }},
            {"$sort": {"created_at": -1}}
        ]
        
        cursor = db.messages.aggregate(pipeline)
        messages = await cursor.to_list(length=None)
        
        # Enrichir les données
        enriched_messages = []
        for message in messages:
            sender_info = message["sender_info"][0] if message["sender_info"] else {}
            receiver_info = message["receiver_info"][0] if message["receiver_info"] else {}
            
            enriched_message = {
                **message,
                "sender_name": sender_info.get("name", "Utilisateur inconnu"),
                "receiver_name": receiver_info.get("name", "Utilisateur inconnu")
            }
            enriched_messages.append(enriched_message)
        
        # Générer le CSV
        csv_content = csv_service.export_messages_to_csv(enriched_messages)
        
        # Préparer le nom du fichier
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"messages_sahelys_{timestamp}.csv"
        
        # Retourner le fichier CSV
        return Response(
            content=csv_content.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'export des messages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'export des messages"
        )