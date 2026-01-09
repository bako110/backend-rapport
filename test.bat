@echo off
echo 🧪 Tests de l'API Sahelys
echo =========================

REM Vérifier que l'API est démarrée
curl -s http://localhost:8000/ >nul 2>&1
if errorlevel 1 (
    echo ❌ L'API n'est pas accessible sur http://localhost:8000
    echo 💡 Assurez-vous qu'elle soit démarrée avec start.bat
    pause
    exit /b 1
)

echo ✅ API accessible, lancement des tests...
echo.

REM Activer l'environnement virtuel si disponible
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Installer aiohttp si nécessaire pour les tests
pip install aiohttp >nul 2>&1

REM Lancer les tests Python
python test_api.py

echo.
echo 🏁 Tests terminés
pause