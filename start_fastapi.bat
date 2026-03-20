@echo off
cd /d D:\CODE\PythonProject\Python_crew_ai_demo

echo Releasing port 8001 if needed...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do taskkill /PID %%a /F >nul 2>nul

echo Starting FastAPI...
set PYTHONPATH=D:\CODE\PythonProject\Python_crew_ai_demo\study_demo\src
"C:\Users\24044\.conda\envs\Python_crew_ai_demo\python.exe" -m uvicorn study_demo.api:app --host 127.0.0.1 --port 8001

pause
