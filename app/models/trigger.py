import time
import uuid
import hashlib
import json
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class TriggerPayload(BaseModel):
    trigger_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    idempotency_key: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source: str = "remote_ops_console"
    timestamp: float = Field(default_factory=time.time)
    priority: str = "HIGH"  # CRITICAL, HIGH, MEDIUM, LOW
    event_type: str = "PRESSURE_SPIKE_ALERT"
    payload: Dict[str, Any] = Field(default_factory=dict)
    offline_staged: bool = False
    retry_count: int = 0
    checksum: Optional[str] = None

    def compute_checksum(self) -> str:
        data_string = f"{self.idempotency_key}:{self.source}:{self.event_type}:{json.dumps(self.payload, sort_keys=True)}"
        return hashlib.sha256(data_string.encode("utf-8")).hexdigest()

    def model_post_init(self, __context: Any) -> None:
        if not self.checksum:
            self.checksum = self.compute_checksum()

class TriggerResponse(BaseModel):
    status: str
    trigger_id: str
    idempotency_key: str
    processed_mode: str  # "ONLINE_REALTIME", "OFFLINE_BUFFERED", "DEDUPLICATED"
    message: str
    execution_id: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)
