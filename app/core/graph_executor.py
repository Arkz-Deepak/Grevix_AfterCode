import time
import uuid
from typing import Dict, Any, Optional
from app.models.graph import (
    DecisionGraph, DecisionNode, NodeType, 
    GraphExecutionState, StepTrace
)
from app.core.storage import db
from app.core.agent_engine import agent_engine

class GraphExecutor:
    def __init__(self):
        self.graphs: Dict[str, DecisionGraph] = {}
        self.manual_override_enabled = False
        self._init_default_graphs()

    def _init_default_graphs(self):
        """Creates the default Remote Operations Industrial Decision Graph."""
        nodes = {
            "node_trigger": DecisionNode(
                id="node_trigger",
                name="Ingest Remote Ops Trigger",
                type=NodeType.TRIGGER,
                description="Receives remote operations manager telemetry or manual trigger",
                next_nodes=["node_filter"]
            ),
            "node_filter": DecisionNode(
                id="node_filter",
                name="Telemetry Threshold Evaluation",
                type=NodeType.CONDITION,
                description="Checks if incoming reading surpasses safety operational envelope",
                condition_expression="reading >= threshold",
                next_nodes=["node_agent_assessor"],
                fallback_node="node_action_log"
            ),
            "node_agent_assessor": DecisionNode(
                id="node_agent_assessor",
                name="Autonomous Agent Risk Engine",
                type=NodeType.AGENT_DECISION,
                description="Synthesizes incident severity and determines mitigation trajectory",
                agent_prompt="Analyze sensor anomaly and determine emergency containment protocol",
                next_nodes=["node_action_dispatcher"]
            ),
            "node_action_dispatcher": DecisionNode(
                id="node_action_dispatcher",
                name="Fail-Safe Action Dispatcher",
                type=NodeType.ACTION,
                description="Dispatches physical actuator or drone inspection command",
                action_type="DYNAMIC_DISPATCH",
                next_nodes=["node_audit"]
            ),
            "node_action_log": DecisionNode(
                id="node_action_log",
                name="Log Normal Telemetry",
                type=NodeType.ACTION,
                description="Persists normal nominal readings into immutable audit trail",
                action_type="LOG_NORMAL_TELEMETRY",
                next_nodes=["node_audit"]
            ),
            "node_audit": DecisionNode(
                id="node_audit",
                name="Audit & Reconcile Verification",
                type=NodeType.AGGREGATOR,
                description="Finalizes transaction, creates cryptographic audit stamp",
                next_nodes=[]
            )
        }

        default_graph = DecisionGraph(
            graph_id="remote_ops_incident_graph",
            title="Remote Industrial Fail-Safe Decision Graph",
            description="Autonomous edge-resilient decision graph for remote operational incident mitigation",
            entrypoint="node_trigger",
            nodes=nodes
        )
        self.graphs[default_graph.graph_id] = default_graph

    def get_graph(self, graph_id: str) -> Optional[DecisionGraph]:
        return self.graphs.get(graph_id)

    def execute(self, graph_id: str, trigger_data: Dict[str, Any], is_offline: bool) -> GraphExecutionState:
        graph = self.get_graph(graph_id)
        if not graph:
            raise ValueError(f"Graph '{graph_id}' not found.")

        execution_id = f"exec_{uuid.uuid4().hex[:10]}"
        state = GraphExecutionState(
            execution_id=execution_id,
            graph_id=graph_id,
            trigger_id=trigger_data["trigger_id"],
            status="RUNNING",
            executed_offline=is_offline,
            created_at=time.time()
        )

        current_node_id = graph.entrypoint
        context = {
            "trigger": trigger_data,
            "payload": trigger_data.get("payload", {}),
            "event_type": trigger_data.get("event_type", "UNKNOWN"),
            "is_offline": is_offline,
            "idempotency_key": trigger_data.get("idempotency_key")
        }

        while current_node_id:
            node = graph.nodes.get(current_node_id)
            if not node:
                break

            state.current_node = current_node_id
            step = StepTrace(
                node_id=node.id,
                node_name=node.name,
                node_type=node.type,
                timestamp=time.time(),
                inputs=dict(context),
                execution_mode="OFFLINE_HEURISTIC_AGENT" if is_offline else "ONLINE_LLM"
            )

            # Node Execution Logic
            if node.type == NodeType.TRIGGER:
                step.outputs = {"status": "TRIGGER_INGESTED", "trigger_id": trigger_data["trigger_id"]}
                current_node_id = node.next_nodes[0] if node.next_nodes else None

            elif node.type == NodeType.CONDITION:
                payload = context.get("payload", {})
                reading = float(payload.get("reading", 0.0))
                threshold = float(payload.get("threshold", 80.0))
                condition_met = reading >= threshold
                step.outputs = {"condition_met": condition_met, "reading": reading, "threshold": threshold}
                step.reasoning = f"Evaluated condition '{node.condition_expression}': reading={reading}, threshold={threshold} -> {condition_met}"
                if condition_met:
                    current_node_id = node.next_nodes[0] if node.next_nodes else None
                else:
                    current_node_id = node.fallback_node

            elif node.type == NodeType.AGENT_DECISION:
                decision = agent_engine.evaluate_node(node.agent_prompt or "", context, is_offline=is_offline)
                step.outputs = decision.to_dict()
                step.reasoning = decision.reasoning
                context["agent_verdict"] = decision.verdict
                context["recommended_action"] = decision.recommended_action
                context["action_params"] = decision.action_params
                current_node_id = node.next_nodes[0] if node.next_nodes else None

            elif node.type == NodeType.ACTION:
                act_type = context.get("recommended_action") or node.action_type
                act_params = context.get("action_params") or node.action_params or {}
                action_id = f"act_{uuid.uuid4().hex[:8]}"

                if self.manual_override_enabled:
                    # User-feedback feature: Human Operator Interlock suppresses automatic actuator dispatch
                    action_record = {
                        "action_id": action_id,
                        "action_type": act_type,
                        "params": act_params,
                        "offline": is_offline,
                        "dispatched": False,
                        "override_status": "HELD_FOR_OPERATOR_CLEARANCE",
                        "timestamp": time.time()
                    }
                    state.actions_dispatched.append(action_record)
                    step.outputs = action_record
                    step.reasoning = f"[OPERATOR SAFETY INTERLOCK] Autonomous dispatch paused. Action '{act_type}' held pending manual human confirmation."
                    current_node_id = node.next_nodes[0] if node.next_nodes else None
                else:
                    # Idempotency check: record and execute action
                    action_dispatched = db.record_action(
                        action_id=action_id,
                        idempotency_key=context["idempotency_key"],
                        action_type=act_type,
                        params=act_params,
                        offline=is_offline,
                        result={"status": "EXECUTED", "action_id": action_id}
                    )

                    action_record = {
                        "action_id": action_id,
                        "action_type": act_type,
                        "params": act_params,
                        "offline": is_offline,
                        "dispatched": action_dispatched,
                        "timestamp": time.time()
                    }
                    state.actions_dispatched.append(action_record)
                    step.outputs = action_record
                    step.reasoning = f"Dispatched action '{act_type}' (Idempotency Safe: {action_dispatched})"
                    current_node_id = node.next_nodes[0] if node.next_nodes else None

            elif node.type == NodeType.AGGREGATOR:
                step.outputs = {"status": "GRAPH_COMPLETED", "actions_count": len(state.actions_dispatched)}
                current_node_id = None

            state.execution_trace.append(step)

        state.status = "OFFLINE_STAGED" if is_offline else "COMPLETED"
        state.completed_at = time.time()

        # Persist to local database
        db.record_execution(state.model_dump())
        db.log_event("INFO", "GRAPH_EXECUTOR", f"GRAPH_EXECUTION_{state.status}", {
            "execution_id": state.execution_id,
            "is_offline": is_offline,
            "actions_dispatched": len(state.actions_dispatched)
        })

        return state

# Global graph executor singleton
graph_executor = GraphExecutor()
