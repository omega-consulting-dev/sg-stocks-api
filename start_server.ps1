# Script de démarrage du serveur avec WebSocket
Write-Host "🚀 Démarrage du serveur SG-Stocks API..." -ForegroundColor Green

# Arrêter les anciens processus sur le port 8000
$processes = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
if ($processes) {
    Write-Host "⏹️  Arrêt des processus existants..." -ForegroundColor Yellow
    $processes | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 2
}

# Activer l'environnement virtuel et démarrer Daphne
Set-Location "d:\projet api sgstock\sg_stocks_api new\sg_stocks_api"
& .\.venv\Scripts\Activate.ps1
Write-Host "✅ Environnement virtuel activé" -ForegroundColor Green
Write-Host "🌐 Démarrage de Daphne sur http://0.0.0.0:8000" -ForegroundColor Cyan
# Augmenter les timeouts pour éviter les problèmes de connexion
# --websocket_timeout: Timeout pour les WebSocket (en secondes)
# --application-close-timeout: Timeout pour fermer l'application (en secondes)
# -t: Timeout HTTP (en secondes)
daphne -b 0.0.0.0 -p 8000 --websocket_timeout 300 --application-close-timeout 60 -t 60 myproject.asgi:application
