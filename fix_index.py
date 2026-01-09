"""
Script pour supprimer l'ancien index unique et recréer les indexes corrects
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, IndexModel

async def fix_indexes():
    # Connexion à MongoDB
    client = AsyncIOMotorClient('mongodb://localhost:27017')
    db = client.sahelys
    
    print("Suppression de l'ancien index unique...")
    try:
        # Supprimer l'ancien index unique
        await db.reports.drop_index("user_id_1_week_iso_1")
        print("✓ Index unique supprimé")
    except Exception as e:
        print(f"Note: {e}")
    
    print("\nCréation du nouvel index partiel...")
    try:
        # Créer le nouvel index partiel
        await db.reports.create_index(
            [("user_id", ASCENDING), ("week_iso", ASCENDING)],
            unique=True,
            partialFilterExpression={"week_iso": {"$exists": True}},
            name="user_id_1_week_iso_1_partial"
        )
        print("✓ Nouvel index partiel créé")
    except Exception as e:
        print(f"Erreur: {e}")
    
    # Lister tous les indexes
    print("\nIndexes actuels sur la collection reports:")
    indexes = await db.reports.list_indexes().to_list(length=None)
    for idx in indexes:
        print(f"  - {idx['name']}: {idx.get('key', {})}")
        if 'partialFilterExpression' in idx:
            print(f"    Filtre partiel: {idx['partialFilterExpression']}")
    
    client.close()
    print("\n✅ Terminé!")

if __name__ == "__main__":
    asyncio.run(fix_indexes())
