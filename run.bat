@echo off
echo ======================================================================
echo  AegisFlow // Resilient Agentic Decision Orchestrator
echo  Grevix AfterCode: Phase 2 Edition
echo ======================================================================
echo.
echo Starting FastAPI Uvicorn Server on http://localhost:8000 ...
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
