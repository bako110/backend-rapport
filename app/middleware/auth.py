from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from app.utils.security import verify_token
from app.models.auth import TokenData
from app.core.database import get_database
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware d'authentification pour toutes les requêtes"""
    
    # Routes qui ne nécessitent pas d'authentification
    EXCLUDED_PATHS = [
        "/",
        "/docs",
        "/redoc", 
        "/openapi.json",
        "/api/v1/auth/login",
        "/api/v1/health"
    ]
    
    async def dispatch(self, request: Request, call_next):
        # Vérifier si la route est exclue
        if request.url.path in self.EXCLUDED_PATHS or request.url.path.startswith("/docs"):
            response = await call_next(request)
            return response
        
        # Vérifier la présence du token Authorization
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token d'authentification requis",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        try:
            # Extraire et vérifier le token
            token = auth_header.split(" ")[1]
            token_data = verify_token(token)
            
            # Ajouter les données du token à la requête
            request.state.current_user = token_data
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        response = await call_next(request)
        return response


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
    """Dependency pour obtenir l'utilisateur actuel à partir du token JWT"""
    return verify_token(credentials.credentials)


async def get_current_user_from_db(
    current_user: TokenData = Depends(get_current_user),
    db = Depends(get_database)
):
    """Dependency pour obtenir l'utilisateur actuel depuis la base de données"""
    user = await db.users.find_one({"_id": ObjectId(current_user.user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )
    return user


async def require_admin(
    current_user: dict = Depends(get_current_user_from_db)
):
    """Dependency pour vérifier que l'utilisateur est un admin"""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits administrateur requis"
        )
    return current_user


async def require_employee(
    current_user: dict = Depends(get_current_user_from_db)
):
    """Dependency pour vérifier que l'utilisateur est un employé"""
    if current_user.get("role") != "employee":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Droits employé requis"
        )
    return current_user


async def require_active_user(
    current_user: dict = Depends(get_current_user_from_db)
):
    """Dependency pour vérifier que l'utilisateur est actif"""
    # Vérifier is_active (booléen) ou status (string)
    is_active = current_user.get("is_active", current_user.get("status") == "active")
    
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Compte utilisateur inactif"
        )
    return current_user