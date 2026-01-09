"""
Script pour créer un utilisateur de test dans la base de données
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from app.utils.security import get_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "sahelys_db")


async def create_test_user():
    """Créer un utilisateur de test"""
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]
    
    try:
        # Vérifier si l'utilisateur existe déjà
        existing_user = await db.users.find_one({"email": "test@sahelys.bf"})
        
        if existing_user:
            print("✅ L'utilisateur test@sahelys.bf existe déjà")
            return
        
        # Créer l'utilisateur
        user_data = {
            "email": "test@sahelys.bf",
            "name": "Utilisateur Test",
            "hashed_password": get_password_hash("test123"),
            "is_active": True,
            "role": "user",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = await db.users.insert_one(user_data)
        print(f"✅ Utilisateur créé avec succès!")
        print(f"   Email: test@sahelys.bf")
        print(f"   Mot de passe: test123")
        print(f"   ID: {result.inserted_id}")
        
    except Exception as e:
        print(f"❌ Erreur: {str(e)}")
    finally:
        client.close()


if __name__ == "__main__":
    print("🚀 Création d'un utilisateur de test...")
    asyncio.run(create_test_user())
