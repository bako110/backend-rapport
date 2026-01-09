from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.models.auth import LoginRequest, LoginResponse, Token, RegisterRequest
from app.models.user import UserResponse, UserInDB
from app.utils.security import verify_password, create_access_token, get_token_expires_in, get_password_hash
from app.core.database import get_database
from app.middleware.auth import get_current_user_from_db
from datetime import timedelta, datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=LoginResponse, summary="Créer un nouveau compte")
async def register(register_data: RegisterRequest, db=Depends(get_database)):
    """
    Public endpoint pour créer un nouveau compte utilisateur
    """
    try:
        logger.info(f"Tentative d'inscription: {register_data.email}, nom: {register_data.name}")
        
        # Valider l'email
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, register_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format d'email invalide"
            )
        
        # Vérifier si l'email existe déjà
        existing_user = await db.users.find_one({"email": register_data.email.lower()})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Un utilisateur avec cette adresse email existe déjà"
            )
        
        # Valider les données
        if not register_data.name or len(register_data.name.strip()) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le nom doit contenir au moins 2 caractères"
            )
        
        if len(register_data.password) < 6:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Le mot de passe doit contenir au moins 6 caractères"
            )
        
        # Créer l'utilisateur
        hashed_password = get_password_hash(register_data.password)
        user_data = {
            "email": register_data.email.lower(),
            "name": register_data.name.strip(),
            "hashed_password": hashed_password,
            "is_active": True,
            "role": "user",  # Rôle par défaut
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insérer l'utilisateur dans la base de données
        result = await db.users.insert_one(user_data)
        user_id = str(result.inserted_id)
        
        logger.info(f"Nouvel utilisateur créé: {user_data['email']} (ID: {user_id})")
        
        # Créer un token pour l'utilisateur qui vient de s'inscrire
        access_token_expires = timedelta(hours=24)
        access_token = create_access_token(
            data={"sub": user_data["email"], "user_id": user_id}, 
            expires_delta=access_token_expires
        )
        
        # Créer les données utilisateur pour la réponse
        user_dict = {
            "id": user_id,
            "email": user_data["email"],
            "name": user_data["name"],
            "is_active": user_data["is_active"],
            "role": user_data["role"]
        }
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_dict,
            expires_in=get_token_expires_in()
        )
        
    except HTTPException:
        # Re-lever les HTTPException sans les modifier
        raise
    except Exception as e:
        logger.error(f"Erreur lors de l'inscription: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erreur interne du serveur: {str(e)}"
        )


@router.post("/login", response_model=LoginResponse, summary="Connexion utilisateur")
async def login(
    login_data: LoginRequest,
    db = Depends(get_database)
):
    """
    Authentifier un utilisateur et retourner un token JWT.
    
    - **email**: Email de l'utilisateur
    - **password**: Mot de passe de l'utilisateur
    """
    try:
        # Chercher l'utilisateur par email
        user = await db.users.find_one({"email": login_data.email})
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Vérifier le mot de passe
        if not verify_password(login_data.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Vérifier que l'utilisateur est actif
        is_active = user.get("is_active", user.get("status") == "active")
        if not is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Compte utilisateur désactivé"
            )
        
        # Créer le token JWT
        access_token_expires = timedelta(hours=24)  # Ou depuis les settings
        access_token = create_access_token(
            data={
                "sub": str(user["_id"]),
                "email": user["email"],
                "role": user["role"]
            },
            expires_delta=access_token_expires
        )
        
        # Préparer les données utilisateur (sans le mot de passe)
        user_data = {
            "id": str(user["_id"]),
            "email": user["email"],
            "name": user["name"],
            "role": user.get("role", "user"),
            "is_active": is_active
        }
        
        logger.info(f"Connexion réussie pour l'utilisateur: {user['email']}")
        
        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=get_token_expires_in(),
            user=user_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la connexion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )


@router.post("/token", response_model=Token, summary="Connexion OAuth2 (compatible)")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db = Depends(get_database)
):
    """
    Point de connexion OAuth2 compatible avec les clients standards.
    """
    # Utiliser la même logique que /login
    login_data = LoginRequest(email=form_data.username, password=form_data.password)
    response = await login(login_data, db)
    
    return Token(
        access_token=response.access_token,
        token_type=response.token_type,
        expires_in=response.expires_in
    )


@router.get("/me", response_model=UserResponse, summary="Profil utilisateur")
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user_from_db)
):
    """
    Obtenir le profil de l'utilisateur connecté.
    """
    return UserResponse(
        _id=str(current_user["_id"]),
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"],
        status=current_user["status"],
        created_at=current_user["created_at"],
        updated_at=current_user["updated_at"]
    )


@router.post("/refresh", response_model=Token, summary="Rafraîchir le token")
async def refresh_token(
    current_user: dict = Depends(get_current_user_from_db)
):
    """
    Rafraîchir le token JWT de l'utilisateur connecté.
    """
    try:
        # Créer un nouveau token
        access_token_expires = timedelta(hours=24)
        access_token = create_access_token(
            data={
                "sub": str(current_user["_id"]),
                "email": current_user["email"],
                "role": current_user["role"]
            },
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=get_token_expires_in()
        )
        
    except Exception as e:
        logger.error(f"Erreur lors du rafraîchissement du token: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors du rafraîchissement du token"
        )