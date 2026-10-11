import time
from fastapi import APIRouter, HTTPException
from app.models.trigger import TriggerPayload, TriggerResponse
from app.core.storage import db
from app.core.chaos_simulator import chaos
from app.core.graph_executor import graph_executor
from app.core.resilience_manager import resilience_manager

router = APIRouter(prefix="/api/triggers", tags=["Triggers"])

@router.post("", response_model=TriggerResponse)
async def ingest_trigger(trigger: TriggerPayload):
    """
    Ingests an incoming trigger from remote operations manager or field sensors.
    Applies network resilience mechanism if network dropout or degraded link is detected.
    """
    trigger_data = trigger.model_dump()
    
    # Try sending via network (subject to simulated latency and packet drops)
    try:
        await chaos.apply_network_effects()
        
        # ONLINE PATH:
        recorded = db.record_trigger(trigger_data, status="RECEIVED")
        if not recorded:
            return TriggerResponse(
                status="DUPLICATE_IGNORED",
                trigger_id=trigger.trigger_id,
                idempotency_key=trigger.idempotency_key,
                processed_mode="DEDUPLICATED",
                message="Trigger already processed. Deduplication prevented redundant execution."
            )

        # Execute decision logic graph online
        exec_state = graph_executor.execute("remote_ops_incident_graph", trigger_data, is_offline=False)

        return TriggerResponse(
            status="SUCCESS",
            trigger_id=trigger.trigger_id,
            idempotency_key=trigger.idempotency_key,
            processed_mode="ONLINE_REALTIME",
            message="Trigger processed via real-time cloud agent decision graph.",
            execution_id=exec_state.execution_id
        )

    except ConnectionError as ce:
        # NETWORK DROPOUT DETECTED!
        # Fallback to Local-First Network Resilience Mechanism:
        stage_status = await resilience_manager.stage_offline_trigger(trigger_data)
        
        # Execute decision logic graph locally on the edge node without stalling
        exec_state = graph_executor.execute("remote_ops_incident_graph", trigger_data, is_offline=True)

        return TriggerResponse(
            status="STAGED_OFFLINE_AND_EXECUTED",
            trigger_id=trigger.trigger_id,
            idempotency_key=trigger.idempotency_key,
            processed_mode="OFFLINE_BUFFERED",
            message=f"Network dropout intercepted ({str(ce)}). Trigger safely buffered to Write-Ahead Log and executed via Autonomous Edge Agent.",
            execution_id=exec_state.execution_id
        )

@router.get("/history")
async def get_trigger_history(limit: int = 50):
    return db.list_triggers(limit=limit)
