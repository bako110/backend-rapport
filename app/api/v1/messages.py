from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from app.models.message import (
    MessageCreate, MessageResponse, MessageBroadcast, MessageInDB,
    MessageSummary, MessageStats
)
from app.middleware.auth import require_admin, get_current_user_from_db, require_employee
from app.core.database import get_database
# WebSocket disabled
# from app.core.websocket import notify_new_message
from app.utils.datetime_utils import truncate_text
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/", response_model=MessageResponse, summary="Envoyer un message")
async def send_message(
    message_data: MessageCreate,
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Envoyer un message à un employé (Admin seulement).
    
    - **receiver_id**: ID de l'employé destinataire
    - **subject**: Sujet du message (optionnel)
    - **content**: Contenu du message
    """
    try:
        # Vérifier que l'ID du destinataire est valide
        if not ObjectId.is_valid(message_data.receiver_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID destinataire invalide"
            )
        
        # Vérifier que le destinataire existe et est un employé
        receiver = await db.users.find_one({
            "_id": ObjectId(message_data.receiver_id),
            "role": "employee",
            "status": "active"
        })
        
        if not receiver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employé destinataire non trouvé ou inactif"
            )
        
        # Créer le message
        message_in_db = MessageInDB(
            sender_id=ObjectId(current_user["_id"]),
            receiver_id=ObjectId(message_data.receiver_id),
            subject=message_data.subject,
            content=message_data.content
        )
        
        # Insérer en base
        result = await db.messages.insert_one(message_in_db.model_dump(by_alias=True))
        
        # Récupérer le message créé
        created_message = await db.messages.find_one({"_id": result.inserted_id})
        
        logger.info(f"Message envoyé de {current_user['name']} à {receiver['name']}")
        
        response = MessageResponse(
            _id=str(created_message["_id"]),
            sender_id=str(created_message["sender_id"]),
            sender_name=current_user["name"],
            receiver_id=str(created_message["receiver_id"]),
            receiver_name=receiver["name"],
            subject=created_message["subject"],
            content=created_message["content"],
            read_status=created_message["read_status"],
            read_at=created_message.get("read_at"),
            created_at=created_message["created_at"]
        )
        
        # WebSocket notification disabled
        # await notify_new_message(...)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'envoi du message"
        )


@router.post("/broadcast", response_model=List[MessageResponse], summary="Envoyer un message groupé")
async def broadcast_message(
    message_data: MessageBroadcast,
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Envoyer un message à plusieurs employés (Admin seulement).
    
    - **receiver_ids**: Liste des IDs des employés destinataires
    - **subject**: Sujet du message (optionnel)
    - **content**: Contenu du message
    """
    try:
        # Vérifier que tous les IDs sont valides
        receiver_object_ids = []
        for receiver_id in message_data.receiver_ids:
            if not ObjectId.is_valid(receiver_id):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"ID destinataire invalide: {receiver_id}"
                )
            receiver_object_ids.append(ObjectId(receiver_id))
        
        # Récupérer tous les employés destinataires
        cursor = db.users.find({
            "_id": {"$in": receiver_object_ids},
            "role": "employee",
            "status": "active"
        })
        receivers = await cursor.to_list(length=None)
        
        if len(receivers) != len(message_data.receiver_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Certains destinataires sont invalides ou inactifs"
            )
        
        # Créer et insérer tous les messages
        messages_to_insert = []
        for receiver in receivers:
            message_in_db = MessageInDB(
                sender_id=ObjectId(current_user["_id"]),
                receiver_id=receiver["_id"],
                subject=message_data.subject,
                content=message_data.content
            )
            messages_to_insert.append(message_in_db.model_dump(by_alias=True))
        
        # Insertion groupée
        result = await db.messages.insert_many(messages_to_insert)
        
        # Récupérer les messages créés
        created_messages = await db.messages.find({
            "_id": {"$in": result.inserted_ids}
        }).to_list(length=None)
        
        # Créer les réponses
        message_responses = []
        receivers_dict = {str(r["_id"]): r for r in receivers}
        
        for message in created_messages:
            receiver = receivers_dict[str(message["receiver_id"])]
            
            message_responses.append(MessageResponse(
                _id=str(message["_id"]),
                sender_id=str(message["sender_id"]),
                sender_name=current_user["name"],
                receiver_id=str(message["receiver_id"]),
                receiver_name=receiver["name"],
                subject=message["subject"],
                content=message["content"],
                read_status=message["read_status"],
                read_at=message.get("read_at"),
                created_at=message["created_at"]
            ))
        
        logger.info(f"Message groupé envoyé de {current_user['name']} à {len(receivers)} employés")
        
        return message_responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'envoi du message groupé: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'envoi du message groupé"
        )


@router.get("/inbox", response_model=List[MessageSummary], summary="Boîte de réception")
async def get_inbox(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    unread_only: bool = Query(False, description="Afficher seulement les messages non lus"),
    current_user: dict = Depends(get_current_user_from_db),
    db = Depends(get_database)
):
    """
    Récupérer la boîte de réception de l'utilisateur connecté.
    
    - **Admin**: Peut voir tous les messages envoyés
    - **Employé**: Peut voir tous les messages reçus
    """
    try:
        # Construire les filtres selon le rôle
        if current_user.get("role") == "admin":
            filters = {"sender_id": ObjectId(current_user["_id"])}
        else:
            filters = {"receiver_id": ObjectId(current_user["_id"])}
        
        # Filtre pour les messages non lus
        if unread_only and current_user.get("role") == "employee":
            filters["read_status"] = False
        
        # Pipeline d'agrégation
        pipeline = [
            {"$match": filters},
            {"$lookup": {
                "from": "users",
                "localField": "sender_id" if current_user.get("role") == "employee" else "receiver_id",
                "foreignField": "_id",
                "as": "other_user_info"
            }},
            {"$sort": {"created_at": -1}},
            {"$skip": skip},
            {"$limit": limit}
        ]
        
        cursor = db.messages.aggregate(pipeline)
        messages = await cursor.to_list(length=limit)
        
        # Convertir en MessageSummary
        message_summaries = []
        for message in messages:
            other_user_info = message["other_user_info"][0] if message["other_user_info"] else {}
            
            # Tronquer le contenu pour l'aperçu
            content_preview = truncate_text(message["content"], 100)
            
            message_summaries.append(MessageSummary(
                id=str(message["_id"]),
                subject=message["subject"],
                content_preview=content_preview,
                sender_name=other_user_info.get("name", "Utilisateur inconnu") if current_user.get("role") == "employee" else current_user["name"],
                read_status=message["read_status"],
                created_at=message["created_at"]
            ))
        
        return message_summaries
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de la boîte de réception: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de la boîte de réception"
        )


@router.get("/{message_id}", response_model=MessageResponse, summary="Détails d'un message")
async def get_message(
    message_id: str,
    current_user: dict = Depends(get_current_user_from_db),
    db = Depends(get_database)
):
    """
    Récupérer les détails d'un message spécifique.
    
    Note: Marque automatiquement le message comme lu pour l'employé destinataire.
    """
    try:
        if not ObjectId.is_valid(message_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID message invalide"
            )
        
        # Récupérer le message avec les infos utilisateur
        pipeline = [
            {"$match": {"_id": ObjectId(message_id)}},
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
            }}
        ]
        
        cursor = db.messages.aggregate(pipeline)
        messages = await cursor.to_list(length=1)
        
        if not messages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message non trouvé"
            )
        
        message = messages[0]
        sender_info = message["sender_info"][0] if message["sender_info"] else {}
        receiver_info = message["receiver_info"][0] if message["receiver_info"] else {}
        
        # Vérifier les permissions
        user_is_sender = str(message["sender_id"]) == str(current_user["_id"])
        user_is_receiver = str(message["receiver_id"]) == str(current_user["_id"])
        
        if not user_is_sender and not user_is_receiver:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Accès non autorisé à ce message"
            )
        
        # Marquer comme lu si c'est l'employé destinataire qui lit
        if user_is_receiver and not message["read_status"]:
            await db.messages.update_one(
                {"_id": ObjectId(message_id)},
                {
                    "$set": {
                        "read_status": True,
                        "read_at": datetime.utcnow()
                    }
                }
            )
            message["read_status"] = True
            message["read_at"] = datetime.utcnow()
            
            logger.info(f"Message {message_id} marqué comme lu par {current_user['name']}")
        
        return MessageResponse(
            _id=str(message["_id"]),
            sender_id=str(message["sender_id"]),
            sender_name=sender_info.get("name", "Utilisateur inconnu"),
            receiver_id=str(message["receiver_id"]),
            receiver_name=receiver_info.get("name", "Utilisateur inconnu"),
            subject=message["subject"],
            content=message["content"],
            read_status=message["read_status"],
            read_at=message.get("read_at"),
            created_at=message["created_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération du message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération du message"
        )


@router.patch("/{message_id}/mark-read", summary="Marquer comme lu")
async def mark_message_as_read(
    message_id: str,
    current_user: dict = Depends(require_employee),
    db = Depends(get_database)
):
    """
    Marquer un message comme lu (Employé destinataire seulement).
    """
    try:
        if not ObjectId.is_valid(message_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID message invalide"
            )
        
        # Vérifier que le message existe et appartient à l'employé
        existing_message = await db.messages.find_one({
            "_id": ObjectId(message_id),
            "receiver_id": ObjectId(current_user["_id"])
        })
        
        if not existing_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message non trouvé ou accès non autorisé"
            )
        
        # Marquer comme lu
        await db.messages.update_one(
            {"_id": ObjectId(message_id)},
            {
                "$set": {
                    "read_status": True,
                    "read_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"Message {message_id} marqué comme lu par {current_user['name']}")
        
        return {"message": "Message marqué comme lu"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors du marquage du message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du marquage du message"
        )


@router.delete("/{message_id}", summary="Supprimer un message")
async def delete_message(
    message_id: str,
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Supprimer un message (Admin expéditeur seulement).
    """
    try:
        if not ObjectId.is_valid(message_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID message invalide"
            )
        
        # Vérifier que le message existe et appartient à l'admin
        existing_message = await db.messages.find_one({
            "_id": ObjectId(message_id),
            "sender_id": ObjectId(current_user["_id"])
        })
        
        if not existing_message:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message non trouvé ou accès non autorisé"
            )
        
        # Supprimer le message
        await db.messages.delete_one({"_id": ObjectId(message_id)})
        
        logger.info(f"Message supprimé: {message_id} par {current_user['name']}")
        
        return {"message": "Message supprimé avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression du message: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression du message"
        )


@router.get("/stats/summary", response_model=MessageStats, summary="Statistiques des messages")
async def get_message_stats(
    current_user: dict = Depends(get_current_user_from_db),
    db = Depends(get_database)
):
    """
    Obtenir les statistiques des messages pour l'utilisateur connecté.
    
    - **Admin**: Statistiques des messages envoyés
    - **Employé**: Statistiques des messages reçus
    """
    try:
        # Filtres selon le rôle
        if current_user.get("role") == "admin":
            base_filter = {"sender_id": ObjectId(current_user["_id"])}
        else:
            base_filter = {"receiver_id": ObjectId(current_user["_id"])}
        
        # Compter les messages totaux
        total_messages = await db.messages.count_documents(base_filter)
        
        # Compter les messages non lus (seulement pour les employés)
        unread_messages = 0
        if current_user.get("role") == "employee":
            unread_filter = {**base_filter, "read_status": False}
            unread_messages = await db.messages.count_documents(unread_filter)
        
        # Compter les messages de cette semaine
        from app.utils.datetime_utils import get_current_time_ouagadougou
        from datetime import timedelta
        
        now = get_current_time_ouagadougou()
        week_start = now - timedelta(days=7)
        
        week_filter = {
            **base_filter,
            "created_at": {"$gte": week_start.replace(tzinfo=None)}
        }
        messages_this_week = await db.messages.count_documents(week_filter)
        
        return MessageStats(
            total_messages=total_messages,
            unread_messages=unread_messages,
            messages_this_week=messages_this_week
        )
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des statistiques: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des statistiques"
        )