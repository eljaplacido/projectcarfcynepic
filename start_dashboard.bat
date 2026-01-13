@echo off
echo Starting CARF Streamlit Dashboard...
cd /d "%~dp0"
call .venv\Scripts\activate
set CARF_API_URL=http://localhost:8000
python -m streamlit run src/dashboard/app.py --server.port 8501
