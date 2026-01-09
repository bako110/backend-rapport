from fastapi import APIRouter
from app.api.v1 import auth, users, reports, comments, messages, exports, dashboard

api_router = APIRouter()

# Inclure tous les routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(comments.router, prefix="/comments", tags=["Comments"])
api_router.include_router(messages.router, prefix="/messages", tags=["Messages"])
api_router.include_router(exports.router, prefix="/exports", tags=["Exports"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])