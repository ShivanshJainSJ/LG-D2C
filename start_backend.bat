@echo off
title Livguard Backend API (FastAPI)
cd Backend
call .venv\Scripts\activate
echo Starting Livguard Backend on http://127.0.0.1:8000...
uvicorn app.main:app --reload --port 8000
pause
