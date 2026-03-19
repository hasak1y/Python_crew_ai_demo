@echo off
cd /d D:\CODE\PythonProject\Python_crew_ai_demo
call conda activate Python_crew_ai_demo
set PYTHONPATH=D:\CODE\PythonProject\Python_crew_ai_demo\study_demo\src
uvicorn study_demo.api:app --reload
pause
