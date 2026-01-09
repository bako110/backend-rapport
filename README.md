# Sahelys Backend - Système de Compte Rendu Hebdomadaire

API REST complète pour le système de compte rendu hebdomadaire de Sahelys Burkina, développée avec FastAPI, MongoDB et authentification JWT.

## 🚀 Fonctionnalités

### 🔐 Authentification & Autorisation
- **JWT Authentication** avec tokens sécurisés
- **Gestion des rôles** : Admin & Employé
- **Middleware de sécurité** pour toutes les routes
- **Gestion des sessions** avec expiration configurable

### 👥 Gestion des Utilisateurs
- **CRUD complet** pour les utilisateurs
- **Filtrage et pagination** des utilisateurs
- **Création d'employés** par les admins
- **Gestion du statut** (actif/inactif)

### 📋 Rapports Hebdomadaires
- **Création de rapports** par semaine ISO (YYYY-Www)
- **Gestion des tâches** avec heures, notes et projets
- **Unicité** : un rapport par employé par semaine
- **Validation automatique** des données
- **Statistiques hebdomadaires** pour les admins

### 💬 Système de Commentaires
- **Commentaires admin** sur les rapports
- **Gestion CRUD** des commentaires
- **Visibilité** pour les employés concernés

### 📨 Messagerie Interne
- **Messages admin → employé**
- **Messages groupés** (broadcast)
- **Statut de lecture** automatique
- **Boîte de réception** avec pagination

### 📊 Exports de Données
- **Export CSV** : rapports, utilisateurs, messages
- **Export PDF** : rapports avec mise en forme
- **Résumés hebdomadaires** en PDF
- **Filtrage avancé** par période, employé, etc.

## 🛠️ Technologies

- **FastAPI** 0.104.1 - Framework web moderne
- **MongoDB** avec Motor - Base de données NoSQL
- **Pydantic** - Validation et sérialisation des données
- **JWT** - Authentification sécurisée
- **ReportLab** - Génération de PDF
- **Python 3.8+** - Langage de développement

## 📦 Installation

### Prérequis
- Python 3.8 ou supérieur
- MongoDB 4.4 ou supérieur
- pip (gestionnaire de packages Python)

### Installation des dépendances

```bash
# Cloner le projet
cd backend

# Installer les dépendances
pip install -r requirements.txt
```

### Configuration

1. **Copier le fichier d'environnement** :
```bash
cp .env.example .env
```

2. **Configurer les variables d'environnement** dans `.env` :
```env
# Database
MONGO_URI=mongodb://localhost:27017/sahelys
DATABASE_NAME=sahelys

# JWT
JWT_SECRET=your-super-secret-jwt-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# CORS
CORS_ORIGINS=["http://localhost:3000", "http://localhost:19006"]

# Admin par défaut
ADMIN_EMAIL=admin@sahelys.bf
ADMIN_PASSWORD=admin123
ADMIN_NAME=Administrateur

# Fuseau horaire
TIMEZONE=Africa/Ouagadougou
```

## 🚀 Démarrage

### Développement

```bash
# Démarrer le serveur de développement
python main.py

# Ou avec uvicorn directement
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Production

```bash
# Démarrer le serveur de production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker (optionnel)

```bash
# Construire l'image
docker build -t sahelys-api .

# Démarrer le conteneur
docker run -d -p 8000:8000 --env-file .env sahelys-api
```

## 📚 Documentation API

### Swagger UI
Une fois l'API démarrée, accédez à la documentation interactive :
- **Swagger UI** : http://localhost:8000/docs
- **ReDoc** : http://localhost:8000/redoc

### Authentification

Pour utiliser l'API, vous devez d'abord vous authentifier :

```bash
# Connexion
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@sahelys.bf",
    "password": "admin123"
  }'
```

Utilisez le token retourné dans l'en-tête `Authorization: Bearer <token>` pour les requêtes suivantes.

## 🗃️ Structure de la Base de Données

### Collections MongoDB

#### `users`
```javascript
{
  "_id": ObjectId,
  "email": "string (unique)",
  "name": "string",
  "hashed_password": "string",
  "role": "employee|admin",
  "status": "active|inactive",
  "created_at": ISODate,
  "updated_at": ISODate
}
```

#### `reports`
```javascript
{
  "_id": ObjectId,
  "user_id": ObjectId,
  "week_iso": "string (YYYY-Www)",
  "tasks": [{
    "title": "string",
    "hours": Number,
    "notes": "string",
    "project": "string"
  }],
  "difficulties": "string",
  "remarks": "string",
  "total_hours": Number,
  "status": "string",
  "created_at": ISODate,
  "updated_at": ISODate
}
```

#### `comments`
```javascript
{
  "_id": ObjectId,
  "report_id": ObjectId,
  "admin_id": ObjectId,
  "content": "string",
  "created_at": ISODate,
  "updated_at": ISODate
}
```

#### `messages`
```javascript
{
  "_id": ObjectId,
  "sender_id": ObjectId,
  "receiver_id": ObjectId,
  "subject": "string",
  "content": "string",
  "read_status": Boolean,
  "read_at": ISODate,
  "created_at": ISODate
}
```

## 🔧 Endpoints Principaux

### Authentification
- `POST /api/v1/auth/login` - Connexion
- `POST /api/v1/auth/refresh` - Rafraîchir le token
- `GET /api/v1/auth/me` - Profil utilisateur

### Utilisateurs (Admin)
- `GET /api/v1/users/` - Liste des utilisateurs
- `POST /api/v1/users/` - Créer un utilisateur
- `PUT /api/v1/users/{id}` - Mettre à jour un utilisateur
- `DELETE /api/v1/users/{id}` - Supprimer un utilisateur

### Rapports
- `POST /api/v1/reports/` - Créer un rapport (Employé)
- `GET /api/v1/reports/` - Liste des rapports
- `GET /api/v1/reports/{id}` - Détails d'un rapport
- `PUT /api/v1/reports/{id}` - Mettre à jour un rapport (Employé)

### Commentaires (Admin)
- `POST /api/v1/comments/` - Ajouter un commentaire
- `GET /api/v1/comments/report/{id}` - Commentaires d'un rapport
- `PUT /api/v1/comments/{id}` - Modifier un commentaire

### Messages
- `POST /api/v1/messages/` - Envoyer un message (Admin)
- `POST /api/v1/messages/broadcast` - Message groupé (Admin)
- `GET /api/v1/messages/inbox` - Boîte de réception
- `PATCH /api/v1/messages/{id}/mark-read` - Marquer comme lu

### Exports (Admin)
- `GET /api/v1/exports/reports/csv` - Export CSV des rapports
- `GET /api/v1/exports/reports/pdf` - Export PDF des rapports
- `GET /api/v1/exports/users/csv` - Export CSV des utilisateurs

## 🔒 Sécurité

- **Mots de passe hachés** avec bcrypt
- **Tokens JWT** avec expiration
- **Validation stricte** des entrées avec Pydantic
- **Contrôle d'accès** basé sur les rôles
- **CORS configuré** pour les domaines autorisés
- **Middleware d'authentification** sur toutes les routes protégées

## 📈 Performance

- **Index MongoDB** optimisés pour les requêtes fréquentes
- **Pagination** automatique sur les listes
- **Agrégation pipeline** pour les statistiques
- **Connexion asynchrone** à la base de données

## 🧪 Tests

```bash
# Installer les dépendances de test
pip install pytest pytest-asyncio httpx

# Lancer les tests
pytest tests/

# Tests avec couverture
pytest tests/ --cov=app --cov-report=html
```

## 🐛 Logging

Les logs sont configurés pour différents niveaux :
- **INFO** : Actions utilisateur importantes
- **ERROR** : Erreurs applicatives
- **DEBUG** : Informations de débogage (développement)

## 🚀 Déploiement

### Variables d'environnement Production

```env
ENVIRONMENT=production
DEBUG=False
JWT_SECRET=your-production-secret-change-this
MONGO_URI=mongodb://prod-server:27017/sahelys
CORS_ORIGINS=["https://your-admin-domain.com", "https://your-mobile-app.com"]
```

### Recommandations

1. **Base de données** : Utilisez MongoDB Atlas ou une instance sécurisée
2. **Secrets** : Générez des secrets JWT forts en production
3. **HTTPS** : Utilisez toujours HTTPS en production
4. **Monitoring** : Configurez les alertes et le monitoring
5. **Backups** : Planifiez des sauvegardes régulières

## 📞 Support

Pour toute question ou problème :
- **Email** : support@sahelys.bf
- **Documentation** : http://localhost:8000/docs
- **Issues** : Créez une issue dans le repository

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

**Sahelys API** - Système de compte rendu hebdomadaire pour Burkina Faso 🇧🇫#   b a c k e n d - r a p p o r t  
 