@echo off
echo 🚀 Démarrage de l'API Sahelys Backend
echo =====================================

REM Vérifier que Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python n'est pas installé ou pas dans le PATH
    pause
    exit /b 1
)

REM Vérifier que MongoDB est accessible (optionnel)
echo 📍 Vérification des prérequis...

REM Installer les dépendances si nécessaire
if not exist "venv\" (
    echo 📦 Création de l'environnement virtuel...
    python -m venv venv
)

REM Activer l'environnement virtuel
call venv\Scripts\activate.bat

REM Installer les dépendances
echo 📦 Installation des dépendances...
pip install -r requirements.txt

REM Vérifier le fichier .env
if not exist ".env" (
    echo ⚠️  Fichier .env manquant, copie depuis .env.example
    copy .env.example .env
)

REM Démarrer l'API
echo 🚀 Démarrage de l'API sur http://localhost:8000
echo 📚 Documentation: http://localhost:8000/docs
echo ⏹️  Appuyez sur Ctrl+C pour arrêter
echo.
python start.py

pause