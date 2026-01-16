# Script PowerShell pour démarrer Celery Worker
# Usage: .\start_celery.ps1

Write-Host "🚀 Démarrage de Celery Worker pour SG Stocks..." -ForegroundColor Green
Write-Host ""

# Activer l'environnement virtuel
& .venv\Scripts\Activate.ps1

# Démarrer Celery Worker avec loglevel INFO
celery -A myproject worker --loglevel=info --pool=solo

# Note: --pool=solo est nécessaire sur Windows
# En production Linux, vous pouvez utiliser: celery -A myproject worker --loglevel=info
