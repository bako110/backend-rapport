from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from app.models.comment import CommentCreate, CommentResponse, CommentUpdate, CommentInDB
from app.middleware.auth import require_admin, get_current_user_from_db
from app.core.database import get_database
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=CommentResponse, summary="Créer un commentaire")
async def create_comment(
    comment_data: CommentCreate,
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Créer un nouveau commentaire sur un rapport (Admin seulement).
    
    - **report_id**: ID du rapport à commenter
    - **content**: Contenu du commentaire
    """
    try:
        # Vérifier que l'ID du rapport est valide
        if not ObjectId.is_valid(comment_data.report_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID rapport invalide"
            )
        
        # Vérifier que le rapport existe
        report = await db.reports.find_one({"_id": ObjectId(comment_data.report_id)})
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rapport non trouvé"
            )
        
        # Créer le commentaire
        comment_in_db = CommentInDB(
            report_id=ObjectId(comment_data.report_id),
            admin_id=ObjectId(current_user["_id"]),
            content=comment_data.content
        )
        
        # Insérer en base
        result = await db.comments.insert_one(comment_in_db.model_dump(by_alias=True))
        
        # Récupérer le commentaire créé
        created_comment = await db.comments.find_one({"_id": result.inserted_id})
        
        logger.info(f"Commentaire créé par {current_user['name']} sur rapport {comment_data.report_id}")
        
        return CommentResponse(
            _id=str(created_comment["_id"]),
            report_id=str(created_comment["report_id"]),
            admin_id=str(created_comment["admin_id"]),
            admin_name=current_user["name"],
            content=created_comment["content"],
            created_at=created_comment["created_at"],
            updated_at=created_comment["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la création du commentaire: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création du commentaire"
        )


@router.get("/report/{report_id}", response_model=List[CommentResponse], summary="Commentaires d'un rapport")
async def get_comments_by_report(
    report_id: str,
    current_user: dict = Depends(get_current_user_from_db),
    db = Depends(get_database)
):
    """
    Récupérer tous les commentaires d'un rapport spécifique.
    
    - **Admin**: Peut voir tous les commentaires
    - **Employé**: Peut voir les commentaires de ses rapports seulement
    """
    try:
        if not ObjectId.is_valid(report_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID rapport invalide"
            )
        
        # Vérifier que le rapport existe
        report = await db.reports.find_one({"_id": ObjectId(report_id)})
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Rapport non trouvé"
            )
        
        # Vérifier les permissions pour les employés
        if (current_user.get("role") == "employee" and 
            str(report["user_id"]) != str(current_user["_id"])):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé aux commentaires de ce rapport"
            )
        
        # Récupérer les commentaires avec les infos admin
        pipeline = [
            {"$match": {"report_id": ObjectId(report_id)}},
            {"$lookup": {
                "from": "users",
                "localField": "admin_id",
                "foreignField": "_id",
                "as": "admin_info"
            }},
            {"$sort": {"created_at": 1}}  # Du plus ancien au plus récent
        ]
        
        cursor = db.comments.aggregate(pipeline)
        comments = await cursor.to_list(length=None)
        
        # Convertir en CommentResponse
        comment_responses = []
        for comment in comments:
            admin_info = comment["admin_info"][0] if comment["admin_info"] else {}
            
            comment_responses.append(CommentResponse(
                _id=str(comment["_id"]),
                report_id=str(comment["report_id"]),
                admin_id=str(comment["admin_id"]),
                admin_name=admin_info.get("name", "Admin inconnu"),
                content=comment["content"],
                created_at=comment["created_at"],
                updated_at=comment["updated_at"]
            ))
        
        return comment_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des commentaires: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des commentaires"
        )


@router.get("/{comment_id}", response_model=CommentResponse, summary="Détails d'un commentaire")
async def get_comment(
    comment_id: str,
    current_user: dict = Depends(get_current_user_from_db),
    db = Depends(get_database)
):
    """
    Récupérer les détails d'un commentaire spécifique.
    """
    try:
        if not ObjectId.is_valid(comment_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID commentaire invalide"
            )
        
        # Récupérer le commentaire avec les infos admin et rapport
        pipeline = [
            {"$match": {"_id": ObjectId(comment_id)}},
            {"$lookup": {
                "from": "users",
                "localField": "admin_id",
                "foreignField": "_id",
                "as": "admin_info"
            }},
            {"$lookup": {
                "from": "reports",
                "localField": "report_id",
                "foreignField": "_id",
                "as": "report_info"
            }}
        ]
        
        cursor = db.comments.aggregate(pipeline)
        comments = await cursor.to_list(length=1)
        
        if not comments:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Commentaire non trouvé"
            )
        
        comment = comments[0]
        admin_info = comment["admin_info"][0] if comment["admin_info"] else {}
        report_info = comment["report_info"][0] if comment["report_info"] else {}
        
        # Vérifier les permissions pour les employés
        if (current_user.get("role") == "employee" and 
            str(report_info.get("user_id")) != str(current_user["_id"])):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à ce commentaire"
            )
        
        return CommentResponse(
            _id=str(comment["_id"]),
            report_id=str(comment["report_id"]),
            admin_id=str(comment["admin_id"]),
            admin_name=admin_info.get("name", "Admin inconnu"),
            content=comment["content"],
            created_at=comment["created_at"],
            updated_at=comment["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du commentaire: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du commentaire"
        )


@router.put("/{comment_id}", response_model=CommentResponse, summary="Mettre à jour un commentaire")
async def update_comment(
    comment_id: str,
    comment_update: CommentUpdate,
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Mettre à jour un commentaire existant (Admin propriétaire seulement).
    """
    try:
        if not ObjectId.is_valid(comment_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID commentaire invalide"
            )
        
        # Vérifier que le commentaire existe et appartient à l'admin
        existing_comment = await db.comments.find_one({
            "_id": ObjectId(comment_id),
            "admin_id": ObjectId(current_user["_id"])
        })
        
        if not existing_comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Commentaire non trouvé ou accès non autorisé"
            )
        
        # Mettre à jour le commentaire
        update_data = {
            "content": comment_update.content,
            "updated_at": datetime.utcnow()
        }
        
        await db.comments.update_one(
            {"_id": ObjectId(comment_id)},
            {"$set": update_data}
        )
        
        # Récupérer le commentaire mis à jour
        updated_comment = await db.comments.find_one({"_id": ObjectId(comment_id)})
        
        logger.info(f"Commentaire mis à jour: {comment_id} par {current_user['name']}")
        
        return CommentResponse(
            _id=str(updated_comment["_id"]),
            report_id=str(updated_comment["report_id"]),
            admin_id=str(updated_comment["admin_id"]),
            admin_name=current_user["name"],
            content=updated_comment["content"],
            created_at=updated_comment["created_at"],
            updated_at=updated_comment["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour du commentaire: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour du commentaire"
        )


@router.delete("/{comment_id}", summary="Supprimer un commentaire")
async def delete_comment(
    comment_id: str,
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Supprimer un commentaire (Admin propriétaire seulement).
    """
    try:
        if not ObjectId.is_valid(comment_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID commentaire invalide"
            )
        
        # Vérifier que le commentaire existe et appartient à l'admin
        existing_comment = await db.comments.find_one({
            "_id": ObjectId(comment_id),
            "admin_id": ObjectId(current_user["_id"])
        })
        
        if not existing_comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Commentaire non trouvé ou accès non autorisé"
            )
        
        # Supprimer le commentaire
        await db.comments.delete_one({"_id": ObjectId(comment_id)})
        
        logger.info(f"Commentaire supprimé: {comment_id} par {current_user['name']}")
        
        return {"message": "Commentaire supprimé avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du commentaire: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression du commentaire"
        )


@router.get("/", response_model=List[CommentResponse], summary="Liste de tous les commentaires")
async def get_all_comments(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    report_id: Optional[str] = Query(None, description="Filtrer par rapport"),
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Récupérer tous les commentaires avec pagination (Admin seulement).
    """
    try:
        # Construire les filtres
        filters = {}
        if report_id:
            if not ObjectId.is_valid(report_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ID rapport invalide"
                )
            filters["report_id"] = ObjectId(report_id)
        
        # Pipeline d'agrégation
        pipeline = [
            {"$match": filters},
            {"$lookup": {
                "from": "users",
                "localField": "admin_id",
                "foreignField": "_id",
                "as": "admin_info"
            }},
            {"$lookup": {
                "from": "reports",
                "localField": "report_id",
                "foreignField": "_id",
                "as": "report_info"
            }},
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        cursor = db.comments.aggregate(pipeline)
        comments = await cursor.to_list(length=limit)
        
        # Convertir en CommentResponse
        comment_responses = []
        for comment in comments:
            admin_info = comment["admin_info"][0] if comment["admin_info"] else {}
            
            comment_responses.append(CommentResponse(
                _id=str(comment["_id"]),
                report_id=str(comment["report_id"]),
                admin_id=str(comment["admin_id"]),
                admin_name=admin_info.get("name", "Admin inconnu"),
                content=comment["content"],
                created_at=comment["created_at"],
                updated_at=comment["updated_at"]
            ))
        
        return comment_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des commentaires: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des commentaires"
        )