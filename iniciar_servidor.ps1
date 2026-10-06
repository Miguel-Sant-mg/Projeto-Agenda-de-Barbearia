Write-Host "==============================================================================" -ForegroundColor Yellow
Write-Host "   💈 BARBEARIA ARTE DE FAVELA - SERVIDOR WEB LOCAL (REDE WI-FI)" -ForegroundColor Yellow
Write-Host "==============================================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "[1/3] Verificando dependencias necessarias..." -ForegroundColor Cyan
python -m pip install -q -r requirements.txt

Write-Host ""
Write-Host "[2/3] Abrindo o navegador local..." -ForegroundColor Cyan
Start-Process "http://localhost:5000/"

Write-Host ""
Write-Host "[3/3] Iniciando o servidor web..." -ForegroundColor Green
Write-Host "Pressione CTRL + C para encerrar o servidor a qualquer momento." -ForegroundColor Gray
Write-Host ""

python app.py
