@echo off
title Barbearia Arte de Favela - Servidor Web Local
color 0E

echo ==============================================================================
echo    💈 BARBEARIA ARTE DE FAVELA - SERVIDOR WEB LOCAL (REDE WI-FI)
echo ==============================================================================
echo.
echo [1/3] Verificando dependencias necessarias...
python -m pip install -q -r requirements.txt

echo.
echo [2/3] Abrindo o navegador local...
start http://localhost:5000/

echo.
echo [3/3] Iniciando o servidor web...
echo.
echo Para acessar pelo celular na mesma rede Wi-Fi, observe o endereco IP
echo exibido no terminal abaixo.
echo.
echo Pressione CTRL + C para encerrar o servidor quando desejar.
echo ==============================================================================
echo.

python app.py

pause
