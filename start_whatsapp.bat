@echo off
cd /d C:\WhatsAppAutomation

echo Starting Nahar WhatsApp webhook server...
echo Automatic customer replies remain controlled by .env.
echo Keep this window open while the server is running.

C:\WhatsAppAutomation\.venv\Scripts\python.exe -m uvicorn webhook:app --host 127.0.0.1 --port 8000 --no-access-log

echo.
echo The webhook server has stopped.
pause