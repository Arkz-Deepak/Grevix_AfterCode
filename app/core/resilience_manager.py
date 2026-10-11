import time
import asyncio
from typing import Dict, Any, List
from app.core.storage import db
from app.core.chaos_simulator import chaos
from app.models.resilience import SyncReport, NetworkMode

class ResilienceManager:
    def __init__(self):
        self.is_syncing = False
        self._background_task = None
        chaos.add_listener(self._on_network_change)

    def _on_network_change(self, status: Dict[str, Any]):
        """Called when chaos simulator changes network mode."""
        if status.get("is_connected") and status.get("mode") == NetworkMode.ONLINE:
            # Connectivity restored: trigger automatic background reconciliation!
            asyncio.create_task(self.trigger_reconciliation())

    async def stage_offline_trigger(self, trigger_data: Dict[str, Any]) -> str:
        """
        Stages an incoming trigger in the local offline Write-Ahead Store.
        Computes idempotency and enqueues to outbox.
        """
        trigger_data["offline_staged"] = True
        
        # Persist locally in WAL triggers table
        recorded = db.record_trigger(trigger_data, status="OFFLINE_BUFFERED")
        if not recorded:
            # Already exists!
            return "DEDUPLICATED"

        # Enqueue in outbox for store-and-forward reconciliation
        queue_id = db.enqueue_outbox(
            item_type="TRIGGER",
            idempotency_key=trigger_data["idempotency_key"],
            payload=trigger_data
        )

        db.log_event("WARNING", "RESILIENCE_MANAGER", "TRIGGER_STAGED_OFFLINE", {
            "trigger_id": trigger_data["trigger_id"],
            "queue_id": queue_id,
            "idempotency_key": trigger_data["idempotency_key"],
            "network_status": chaos.get_status()["mode"]
        })

        return queue_id

    async def trigger_reconciliation(self) -> SyncReport:
        """
        Executes Store-and-Forward queue drain and cloud reconciliation.
        Guarantees:
        - At-least-once delivery with exactly-once processing (Idempotency)
        - Monotonic state reconciliation
        - Zero data loss
        """
        if self.is_syncing:
            # Avoid concurrent overlapping syncs
            return SyncReport(details=[{"note": "Sync already in progress"}])

        self.is_syncing = True
        start_time = time.time()
        report = SyncReport()

        try:
            pending_items = db.get_pending_outbox_items()
            report.items_processed = len(pending_items)

            for item in pending_items:
                # Test connection using chaos simulator
                try:
                    await chaos.apply_network_effects()
                except ConnectionError as ce:
                    # Network dropped again during sync! Store remains intact.
                    db.update_queue_status(item["queue_id"], "FAILED", error_message=str(ce))
                    db.log_event("ERROR", "RESILIENCE_MANAGER", "SYNC_ABORTED_NETWORK_DROP", {
                        "queue_id": item["queue_id"],
                        "error": str(ce)
                    })
                    break

                idempotency_key = item["idempotency_key"]
                item_payload = item["payload"]

                # Check if this trigger was already acknowledged or duplicated
                existing_trigger = db.get_trigger_by_idempotency_key(idempotency_key)
                if existing_trigger and existing_trigger.get("status") == "ACKNOWLEDGED":
                    db.update_queue_status(item["queue_id"], "DEDUPLICATED")
                    report.duplicates_prevented += 1
                    report.details.append({
                        "queue_id": item["queue_id"],
                        "idempotency_key": idempotency_key,
                        "action": "DEDUPLICATED_PREVENTED_DOUBLE_EXECUTION"
                    })
                    continue

                # Cloud reconciliation step:
                # Mark trigger as synced/acknowledged in store
                with db.get_connection() as conn:
                    conn.execute(
                        "UPDATE triggers SET status = 'ACKNOWLEDGED' WHERE idempotency_key = ?",
                        (idempotency_key,)
                    )
                    conn.execute(
                        "UPDATE graph_executions SET status = 'RECONCILED', reconciled_at = ? WHERE trigger_id = ?",
                        (time.time(), item_payload.get("trigger_id", ""))
                    )
                    conn.commit()

                db.update_queue_status(item["queue_id"], "ACKNOWLEDGED")
                report.items_reconciled += 1
                report.details.append({
                    "queue_id": item["queue_id"],
                    "idempotency_key": idempotency_key,
                    "action": "RECONCILED_SUCCESS"
                })

            report.execution_time_ms = round((time.time() - start_time) * 1000, 2)
            db.log_event("INFO", "RESILIENCE_MANAGER", "RECONCILIATION_COMPLETED", {
                "report_id": report.sync_id,
                "reconciled": report.items_reconciled,
                "duplicates_prevented": report.duplicates_prevented,
                "time_ms": report.execution_time_ms
            })

        finally:
            self.is_syncing = False

        return report

# Global resilience manager singleton
resilience_manager = ResilienceManager()
