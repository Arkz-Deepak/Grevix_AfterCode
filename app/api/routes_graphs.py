from fastapi import APIRouter, HTTPException
from app.core.graph_executor import graph_executor
from app.core.storage import db

router = APIRouter(prefix="/api/graphs", tags=["Decision Graphs"])

@router.get("")
async def get_graphs():
    """Returns available decision logic graphs and their node topologies."""
    return {
        graph_id: graph.model_dump()
        for graph_id, graph in graph_executor.graphs.items()
    }

@router.get("/executions")
async def get_executions(limit: int = 50):
    """Returns recent graph executions with full trace and offline status."""
    return db.list_executions(limit=limit)

@router.get("/executions/{execution_id}")
async def get_execution_detail(execution_id: str):
    exec_state = db.get_execution(execution_id)
    if not exec_state:
        raise HTTPException(status_code=404, detail="Execution not found")
    return exec_state
