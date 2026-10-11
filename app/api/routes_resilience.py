from fastapi import APIRouter
from pydantic import BaseModel
from app.core.chaos_simulator import chaos
from app.core.resilience_manager import resilience_manager
from app.core.graph_executor import graph_executor
from app.core.storage import db

router = APIRouter(prefix="/api/resilience", tags=["Resilience"])

class ChaosUpdateRequest(BaseModel):
    mode: str
    latency_ms: int = None
    packet_loss_rate: float = None

class OverrideUpdateRequest(BaseModel):
    enabled: bool

@router.get("/status")
async def get_resilience_status():
    """Returns network chaos mode, edge store statistics, queue count, and safety lockout status."""
    chaos_status = chaos.get_status()
    stats = db.get_stats()
    pending_items = db.get_pending_outbox_items()
    
    return {
        "network": chaos_status,
        "stats": stats,
        "pending_outbox_count": len(pending_items),
        "pending_items": pending_items[:10],
        "is_syncing": resilience_manager.is_syncing,
        "manual_override_enabled": graph_executor.manual_override_enabled
    }

@router.post("/override")
async def toggle_manual_override(req: OverrideUpdateRequest):
    """
    User-Feedback Capability:
    Enables/Disables the Human Operator Manual Interlock.
    When enabled, autonomous actuator dispatches are halted pending human confirmation.
    """
    graph_executor.manual_override_enabled = req.enabled
    db.log_event("WARNING", "SAFETY_INTERLOCK", "MANUAL_OVERRIDE_TOGGLED", {
        "enabled": req.enabled,
        "status": "SAFETY_LOCKOUT_ACTIVE" if req.enabled else "AUTONOMOUS_MODE_ACTIVE"
    })
    return {
        "manual_override_enabled": graph_executor.manual_override_enabled,
        "message": "Manual Safety Interlock ENGAGED. Autonomous physical commands paused." if req.enabled else "Autonomous Edge Execution RESTORED."
    }

@router.get("/outbox")
async def get_outbox_details():
    """Returns all outbox queue items for the visual Outbox Inspector."""
    with db.get_connection() as conn:
        rows = conn.execute("SELECT * FROM outbox_queue ORDER BY created_at DESC LIMIT 50").fetchall()
        import json
        items = []
        for r in rows:
            d = dict(r)
            d["payload"] = json.loads(d["payload_json"])
            items.append(d)
        return items

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
