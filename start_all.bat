@echo off
cd /d C:\WhatsAppAutomation

echo Starting Nahar WhatsApp automation...

start "Nahar WhatsApp Webhook" cmd /k "C:\WhatsAppAutomation\start_whatsapp.bat"

echo Waiting for the webhook server to start...
timeout /t 8 /nobreak >nul

start "Nahar ngrok Tunnel" cmd /k "C:\WhatsAppAutomation\start_ngrok.bat"

echo Startup commands launched.
exit