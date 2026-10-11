from enum import Enum
from typing import Dict, List, Any, Optional
import time
import uuid
from pydantic import BaseModel, Field

class NodeType(str, Enum):
    TRIGGER = "TRIGGER"
    CONDITION = "CONDITION"
    AGENT_DECISION = "AGENT_DECISION"
    ACTION = "ACTION"
    AGGREGATOR = "AGGREGATOR"

class DecisionNode(BaseModel):
    id: str
    name: str
    type: NodeType
    description: str = ""
    agent_prompt: Optional[str] = None
    condition_expression: Optional[str] = None  # e.g. "reading > 85.0"
    action_type: Optional[str] = None          # e.g. "SHUTDOWN_VALVE", "DISPATCH_DRONE"
    action_params: Optional[Dict[str, Any]] = Field(default_factory=dict)
    next_nodes: List[str] = Field(default_factory=list)
    fallback_node: Optional[str] = None

class DecisionGraph(BaseModel):
    graph_id: str
    title: str
    description: str
    entrypoint: str
    nodes: Dict[str, DecisionNode]

class StepTrace(BaseModel):
    node_id: str
    node_name: str
    node_type: NodeType
    timestamp: float = Field(default_factory=time.time)
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    reasoning: Optional[str] = None
    execution_mode: str = "ONLINE"  # "ONLINE_LLM", "OFFLINE_HEURISTIC_AGENT", "DETERMINISTIC"

class GraphExecutionState(BaseModel):
    execution_id: str = Field(default_factory=lambda: f"exec_{uuid.uuid4().hex[:10]}")
    graph_id: str
    trigger_id: str
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, OFFLINE_STAGED, RECONCILED, FAILED
    current_node: Optional[str] = None
    execution_trace: List[StepTrace] = Field(default_factory=list)
    actions_dispatched: List[Dict[str, Any]] = Field(default_factory=list)
    executed_offline: bool = False
    reconciled_at: Optional[float] = None
    created_at: float = Field(default_factory=time.time)
    completed_at: Optional[float] = None
    error: Optional[str] = None
