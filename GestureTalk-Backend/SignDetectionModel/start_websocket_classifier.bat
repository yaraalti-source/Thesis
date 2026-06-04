@echo off
echo ========================================
echo Starting WebSocket Classifier
echo (Using final_classifier.py models and logic)
echo ========================================
cd /d "%~dp0"
python websocket_final_classifier.py
pause

