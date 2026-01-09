from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from app.models.user import UserCreate, UserResponse, UserUpdate, UserInDB
from app.middleware.auth import require_admin, get_current_user_from_db
from app.core.database import get_database
from app.utils.security import get_password_hash
from bson import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=List[UserResponse], summary="Liste des utilisateurs")
async def get_users(
    skip: int = Query(0, ge=0, description="Nombre d'utilisateurs à ignorer"),
    limit: int = Query(100, ge=1, le=100, description="Limite d'utilisateurs à retourner"),
    role: Optional[str] = Query(None, description="Filtrer par rôle"),
    status: Optional[str] = Query(None, description="Filtrer par statut"),
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Récupérer la liste de tous les utilisateurs (Admin seulement).
    
    - **skip**: Pagination - nombre à ignorer
    - **limit**: Pagination - limite par page
    - **role**: Filtrer par rôle (employee, admin)
    - **status**: Filtrer par statut (active, inactive)
    """
    try:
        # Construire les filtres
        filters = {}
        if role:
            filters["role"] = role
        if status:
            filters["status"] = status
        
        # Récupérer les utilisateurs
        cursor = db.users.find(filters).skip(skip).limit(limit).sort("created_at", -1)
        users = await cursor.to_list(length=limit)
        
        # Convertir en UserResponse
        user_responses = []
        for user in users:
            user_responses.append(UserResponse(
                _id=str(user["_id"]),
                email=user["email"],
                name=user["name"],
                role=user["role"],
                status=user["status"],
                created_at=user["created_at"],
                updated_at=user["updated_at"]
            ))
        
        return user_responses
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des utilisateurs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des utilisateurs"
        )


@router.get("/{user_id}", response_model=UserResponse, summary="Détails d'un utilisateur")
async def get_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Récupérer les détails d'un utilisateur spécifique (Admin seulement).
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID utilisateur invalide"
            )
        
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        return UserResponse(
            _id=str(user["_id"]),
            email=user["email"],
            name=user["name"],
            role=user["role"],
            status=user["status"],
            created_at=user["created_at"],
            updated_at=user["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'utilisateur: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération de l'utilisateur"
        )


@router.post("/", response_model=UserResponse, summary="Créer un nouvel utilisateur")
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Créer un nouvel utilisateur (Admin seulement).
    
    - **email**: Email unique de l'utilisateur
    - **name**: Nom complet de l'utilisateur
    - **password**: Mot de passe (minimum 6 caractères)
    - **role**: Rôle (employee ou admin)
    - **status**: Statut (active ou inactive)
    """
    try:
        # Vérifier si l'email existe déjà
        existing_user = await db.users.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un utilisateur avec cet email existe déjà"
            )
        
        # Créer le nouvel utilisateur
        user_in_db = UserInDB(
            email=user_data.email,
            name=user_data.name,
            role=user_data.role,
            status=user_data.status,
            hashed_password=get_password_hash(user_data.password)
        )
        
        # Insérer en base
        result = await db.users.insert_one(user_in_db.model_dump(by_alias=True))
        
        # Récupérer l'utilisateur créé
        created_user = await db.users.find_one({"_id": result.inserted_id})
        
        logger.info(f"Nouvel utilisateur créé: {user_data.email} par {current_user['email']}")
        
        return UserResponse(
            _id=str(created_user["_id"]),
            email=created_user["email"],
            name=created_user["name"],
            role=created_user["role"],
            status=created_user["status"],
            created_at=created_user["created_at"],
            updated_at=created_user["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la création de l'utilisateur: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création de l'utilisateur"
        )


@router.put("/{user_id}", response_model=UserResponse, summary="Mettre à jour un utilisateur")
async def update_user(
    user_id: str,
    user_update: UserUpdate,
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Mettre à jour un utilisateur existant (Admin seulement).
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID utilisateur invalide"
            )
        
        # Vérifier que l'utilisateur existe
        existing_user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not existing_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        # Préparer les données de mise à jour
        update_data = {}
        if user_update.name is not None:
            update_data["name"] = user_update.name
        if user_update.role is not None:
            update_data["role"] = user_update.role
        if user_update.status is not None:
            update_data["status"] = user_update.status
        
        update_data["updated_at"] = datetime.utcnow()
        
        # Mettre à jour en base
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": update_data}
        )
        
        # Récupérer l'utilisateur mis à jour
        updated_user = await db.users.find_one({"_id": ObjectId(user_id)})
        
        logger.info(f"Utilisateur mis à jour: {updated_user['email']} par {current_user['email']}")
        
        return UserResponse(
            _id=str(updated_user["_id"]),
            email=updated_user["email"],
            name=updated_user["name"],
            role=updated_user["role"],
            status=updated_user["status"],
            created_at=updated_user["created_at"],
            updated_at=updated_user["updated_at"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la mise à jour de l'utilisateur: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la mise à jour de l'utilisateur"
        )


@router.delete("/{user_id}", summary="Supprimer un utilisateur")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Supprimer un utilisateur (Admin seulement).
    
    Note: Supprime également tous les rapports, commentaires et messages associés.
    """
    try:
        if not ObjectId.is_valid(user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID utilisateur invalide"
            )
        
        # Vérifier que l'utilisateur existe
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Utilisateur non trouvé"
            )
        
        # Empêcher la suppression de son propre compte
        if str(user["_id"]) == str(current_user["_id"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Impossible de supprimer votre propre compte"
            )
        
        # Supprimer les données associées
        await db.reports.delete_many({"user_id": ObjectId(user_id)})
        await db.comments.delete_many({"admin_id": ObjectId(user_id)})
        await db.messages.delete_many({"$or": [
            {"sender_id": ObjectId(user_id)},
            {"receiver_id": ObjectId(user_id)}
        ]})
        
        # Supprimer l'utilisateur
        await db.users.delete_one({"_id": ObjectId(user_id)})
        
        logger.info(f"Utilisateur supprimé: {user['email']} par {current_user['email']}")
        
        return {"message": "Utilisateur supprimé avec succès"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de l'utilisateur: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la suppression de l'utilisateur"
        )


@router.get("/employees/list", response_model=List[UserResponse], summary="Liste des employés")
async def get_employees(
    current_user: dict = Depends(require_admin),
    db = Depends(get_database)
):
    """
    Récupérer la liste de tous les employés actifs (Admin seulement).
    """
    try:
        cursor = db.users.find({
            "role": "employee",
            "status": "active"
        }).sort("name", 1)
        
        employees = await cursor.to_list(length=None)
        
        employee_responses = []
        for emp in employees:
            employee_responses.append(UserResponse(
                _id=str(emp["_id"]),
                email=emp["email"],
                name=emp["name"],
                role=emp["role"],
                status=emp["status"],
                created_at=emp["created_at"],
                updated_at=emp["updated_at"]
            ))
        
        return employee_responses
        
    except Exception as e:
        logger.error(f"Erreur lors de la récupération des employés: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la récupération des employés"
        )