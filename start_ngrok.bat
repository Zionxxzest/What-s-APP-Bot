@echo off
cd /d C:\WhatsAppAutomation

echo Starting ngrok tunnel for the Nahar webhook...
echo Keep this window open while the tunnel is running.

C:\Users\anikd\AppData\Local\Microsoft\WindowsApps\ngrok.exe http 8000

echo.
echo The ngrok tunnel has stopped.
pause