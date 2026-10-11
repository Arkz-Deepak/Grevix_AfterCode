from fastapi import APIRouter
from pydantic import BaseModel
from app.core.chaos_simulator import chaos
from app.core.resilience_manager import resilience_manager
from app.core.storage import db

router = APIRouter(prefix="/api/resilience", tags=["Resilience"])

class ChaosUpdateRequest(BaseModel):
    mode: str
    latency_ms: int = None
    packet_loss_rate: float = None

@router.get("/status")
async def get_resilience_status():
    """Returns network chaos mode, edge store statistics, and queue count."""
    chaos_status = chaos.get_status()
    stats = db.get_stats()
    pending_items = db.get_pending_outbox_items()
    
    return {
        "network": chaos_status,
        "stats": stats,
        "pending_outbox_count": len(pending_items),
        "pending_items": pending_items[:10],
        "is_syncing": resilience_manager.is_syncing
    }

@router.post("/chaos")
async def update_chaos_mode(req: ChaosUpdateRequest):
    """Dynamically modifies network condition (ONLINE, DEGRADED, BLACKOUT, FLAPPING)."""
    updated_status = chaos.set_mode(
        mode=req.mode,
        latency_ms=req.latency_ms,
        packet_loss_rate=req.packet_loss_rate
    )
    db.log_event("WARNING", "CHAOS_CONTROLLER", "NETWORK_MODE_CHANGED", updated_status)
    return updated_status

@router.post("/sync")
async def run_reconciliation():
    """Manually triggers Store-and-Forward outbox reconciliation."""
    report = await resilience_manager.trigger_reconciliation()
    return report

@router.get("/audit-logs")
async def get_audit_logs(limit: int = 50):
    return db.list_audit_logs(limit=limit)

@router.get("/actions")
async def get_dispatched_actions(limit: int = 50):
    return db.list_actions(limit=limit)
