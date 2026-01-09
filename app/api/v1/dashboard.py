from fastapi import APIRouter, Depends
from app.middleware.auth import get_current_user_from_db
from app.models.user import UserInDB
from app.core.database import get_database
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    current_user: UserInDB = Depends(get_current_user_from_db),
    db = Depends(get_database)
):
    """
    Récupérer les statistiques du tableau de bord
    """
    try:
        # Compter les messages
        total_messages = await db.messages.count_documents({})
        unread_messages = await db.messages.count_documents({"read": False})
        
        # Compter les rapports  
        total_reports = await db.reports.count_documents({})
        pending_reports = await db.reports.count_documents({"status": "pending"})
        
        # Activité récente (derniers messages et rapports)
        recent_activity = []
        
        # Derniers messages
        recent_messages = await db.messages.find({}).sort("created_at", -1).limit(3).to_list(3)
        for msg in recent_messages:
            recent_activity.append({
                "id": str(msg["_id"]),
                "type": "message",
                "description": f"Message: {msg.get('title', 'Sans titre')}",
                "timestamp": msg.get("created_at", datetime.utcnow()).isoformat()
            })
            
        # Derniers rapports
        recent_reports = await db.reports.find({}).sort("created_at", -1).limit(2).to_list(2)
        for report in recent_reports:
            recent_activity.append({
                "id": str(report["_id"]),
                "type": "report", 
                "description": f"Rapport: {report.get('title', 'Sans titre')}",
                "timestamp": report.get("created_at", datetime.utcnow()).isoformat()
            })
        
        # Trier par date
        recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "total_messages": total_messages,
            "unread_messages": unread_messages,
            "total_reports": total_reports,
            "pending_reports": pending_reports,
            "recent_activity": recent_activity[:5]  # Top 5
        }
        
    except Exception as e:
        logger.error(f"Erreur dashboard stats: {str(e)}")
        # Fallback avec données par défaut
        return {
            "total_messages": 0,
            "unread_messages": 0,
            "total_reports": 0,
            "pending_reports": 0,
            "recent_activity": []
        }