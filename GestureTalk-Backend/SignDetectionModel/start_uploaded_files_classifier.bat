@echo off
echo ========================================
echo Starting Uploaded Files Classifier
echo ========================================
cd /d "%~dp0"
python -m uvicorn uploaded_files_classifier:app --host 0.0.0.0 --port 8001
pause

