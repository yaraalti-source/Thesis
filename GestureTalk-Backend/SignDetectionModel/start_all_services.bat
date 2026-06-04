@echo off
echo ========================================
echo Starting All Sign Detection Services
echo ========================================
cd /d "%~dp0"

echo.
echo Starting Uploaded Files Classifier on port 8001...
start "Uploaded Files Classifier" cmd /k "python -m uvicorn uploaded_files_classifier:app --host 0.0.0.0 --port 8001"

timeout /t 2 /nobreak >nul

echo.
echo Starting WebSocket Classifier on port 8002...
echo (Using final_classifier.py models and logic)
start "WebSocket Final Classifier" cmd /k "python websocket_final_classifier.py"

echo.
echo ========================================
echo All services started!
echo ========================================
echo Uploaded Files Classifier: http://localhost:8001
echo WebSocket Classifier: ws://localhost:8002
echo.
echo Press any key to close this window...
pause >nul

