# 🚀 Guide de Démarrage Rapide - Sahelys API

## Méthode 1: Démarrage automatique (Windows)

```bash
# Double-cliquer sur start.bat ou exécuter :
start.bat
```

## Méthode 2: Démarrage manuel

### Prérequis
- Python 3.8+ installé
- MongoDB installé et démarré
- Git (optionnel)

### Installation

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Configurer l'environnement (copier .env.example vers .env)
copy .env.example .env

# 3. Démarrer MongoDB (si pas déjà fait)
mongod

# 4. Démarrer l'API
python main.py
```

## Méthode 3: Avec Docker

```bash
# Démarrer avec Docker Compose
docker-compose up

# Ou construire manuellement
docker build -t sahelys-api .
docker run -p 8000:8000 sahelys-api
```

## 🌐 Accès

Une fois démarrée, l'API est accessible sur :

- **API principale** : http://localhost:8000
- **Documentation Swagger** : http://localhost:8000/docs  
- **Documentation ReDoc** : http://localhost:8000/redoc

## 🔑 Connexion Admin

**Email** : admin@sahelys.bf  
**Mot de passe** : admin123

## 🧪 Tests

```bash
# Méthode 1: Script automatique
test.bat

# Méthode 2: Manuel
python test_api.py
```

## 📋 Endpoints Principaux

### Authentification
- `POST /api/v1/auth/login` - Connexion
- `GET /api/v1/auth/me` - Profil utilisateur

### Utilisateurs (Admin)
- `GET /api/v1/users/` - Liste utilisateurs
- `POST /api/v1/users/` - Créer utilisateur

### Rapports
- `POST /api/v1/reports/` - Créer rapport
- `GET /api/v1/reports/` - Liste rapports

### Exports (Admin)
- `GET /api/v1/exports/reports/csv` - Export CSV
- `GET /api/v1/exports/reports/pdf` - Export PDF

## 🐛 Dépannage

### Erreur MongoDB
```bash
# Vérifier que MongoDB fonctionne
mongo --eval "db.adminCommand('ismaster')"
```

### Erreur Port 8000 occupé
```bash
# Changer le port dans .env ou tuer le processus
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Logs de Debug
Modifier dans `.env` :
```
DEBUG=True
```

## 🎯 Prêt à l'emploi !

L'API est maintenant fonctionnelle avec :
- ✅ Base de données MongoDB configurée
- ✅ Utilisateur admin créé automatiquement  
- ✅ Documentation Swagger interactive
- ✅ Tous les endpoints implémentés
- ✅ Exports CSV/PDF fonctionnels
- ✅ Tests automatisés inclus