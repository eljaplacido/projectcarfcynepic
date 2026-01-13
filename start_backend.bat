@echo off
echo Starting CARF FastAPI Backend...
cd /d "%~dp0"
call .venv\Scripts\activate
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
