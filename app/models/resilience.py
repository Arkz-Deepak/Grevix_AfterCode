import time
import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class NetworkMode(str):
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"      # High latency, 50% packet drop
    BLACKOUT = "BLACKOUT"      # Complete disconnection (100% loss)
    FLAPPING = "FLAPPING"      # Drops intermittently every few seconds

class ChaosConfig(BaseModel):
    mode: str = "ONLINE"  # ONLINE, DEGRADED, BLACKOUT, FLAPPING
    latency_ms: int = 20
    packet_loss_rate: float = 0.0  # 0.0 to 1.0
    auto_flap_interval_sec: int = 5
    description: str = "Standard high-speed network connection"

class QueueItem(BaseModel):
    queue_id: str = Field(default_factory=lambda: f"q_{uuid.uuid4().hex[:12]}")
    idempotency_key: str
    item_type: str  # "TRIGGER", "GRAPH_EXECUTION", "ACTION_DISPATCH"
    payload: Dict[str, Any]
    status: str = "STAGED_OFFLINE"  # STAGED_OFFLINE, SYNCING, ACKNOWLEDGED, DEDUPLICATED, FAILED
    attempts: int = 0
    created_at: float = Field(default_factory=time.time)
    last_attempt_at: Optional[float] = None
    reconciled_at: Optional[float] = None
    error_message: Optional[str] = None

class SyncReport(BaseModel):
    sync_id: str = Field(default_factory=lambda: f"sync_{uuid.uuid4().hex[:8]}")
    timestamp: float = Field(default_factory=time.time)
    items_processed: int = 0
    items_reconciled: int = 0
    duplicates_prevented: int = 0
    execution_time_ms: float = 0.0
    conflicts_resolved: int = 0
    details: list[dict] = Field(default_factory=list)
