import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, HTMLResponse
from starlette.staticfiles import StaticFiles

from app.api.routes_triggers import router as triggers_router
from app.api.routes_graphs import router as graphs_router
from app.api.routes_resilience import router as resilience_router
from app.api.routes_proof import router as proof_router
from app.core.storage import db

app = FastAPI(
    title="AegisFlow // Resilient Agentic Decision Orchestrator",
    description="Adaptive Agentic Decision Logic Graph engine engineered for fault-tolerant operation under network dropout.",
    version="1.0.0"
)

# Enable CORS for local testing & external frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(triggers_router)
app.include_router(graphs_router)
app.include_router(resilience_router)
app.include_router(proof_router)

# Mount static folder
STATIC_DIR = Path(__file__).resolve().parent / "static"

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>AegisFlow Backend Online</h1><p>Static dashboard not found.</p>")

@app.get("/static/{file_path:path}")
async def serve_static(file_path: str):
    target = STATIC_DIR / file_path
    if target.exists() and target.is_file():
        return FileResponse(target)
    return HTMLResponse(status_code=404, content="File not found")

@app.on_event("startup")
async def on_startup():
    db.log_event("INFO", "SYSTEM", "SERVER_STARTUP", {
        "version": "1.0.0",
        "description": "AegisFlow Resilient Agentic Engine Initialized"
    })

if __name__ == "__main__":
    import uvicorn
    from app.config import HOST, DEFAULT_PORT
    uvicorn.run("app.main:app", host=HOST, port=DEFAULT_PORT, reload=True)
