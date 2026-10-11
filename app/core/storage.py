import sqlite3
import json
import time
import uuid
import threading
from typing import Dict, Any, List, Optional
from app.config import DB_PATH

class Database:
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 30000;")
        # Enable Write-Ahead Logging for high-concurrency resilience
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Triggers table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS triggers (
                trigger_id TEXT PRIMARY KEY,
                idempotency_key TEXT UNIQUE,
                source TEXT,
                event_type TEXT,
                priority TEXT,
                payload_json TEXT,
                checksum TEXT,
                offline_staged INTEGER,
                timestamp REAL,
                status TEXT
            );
            """)

            # Graph Executions table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS graph_executions (
                execution_id TEXT PRIMARY KEY,
                graph_id TEXT,
                trigger_id TEXT,
                status TEXT,
                execution_trace_json TEXT,
                actions_dispatched_json TEXT,
                executed_offline INTEGER,
                created_at REAL,
                completed_at REAL,
                reconciled_at REAL
            );
            """)

            # Outbox & Store-and-Forward Queue
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS outbox_queue (
                queue_id TEXT PRIMARY KEY,
                idempotency_key TEXT UNIQUE,
                item_type TEXT,
                payload_json TEXT,
                status TEXT,
                attempts INTEGER DEFAULT 0,
                created_at REAL,
                last_attempt_at REAL,
                reconciled_at REAL,
                error_message TEXT
            );
            """)

            # Dispatched Actions (Side-Effects log for verifying exactly-once execution)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dispatched_actions (
                action_id TEXT PRIMARY KEY,
                idempotency_key TEXT,
                action_type TEXT,
                params_json TEXT,
                executed_at REAL,
                offline_execution INTEGER,
                result_json TEXT
            );
            """)

            # System Audit & Event Log
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                level TEXT,
                component TEXT,
                event TEXT,
                details_json TEXT
            );
            """)

            conn.commit()

    # --- Trigger Management ---
    def record_trigger(self, trigger_data: Dict[str, Any], status: str = "RECEIVED") -> bool:
        """Records trigger. Returns True if fresh, False if already exists (deduplicated)."""
        is_fresh = False
        with self.lock:
            with self.get_connection() as conn:
                try:
                    conn.execute("""
                    INSERT INTO triggers (
                        trigger_id, idempotency_key, source, event_type, priority,
                        payload_json, checksum, offline_staged, timestamp, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        trigger_data["trigger_id"],
                        trigger_data["idempotency_key"],
                        trigger_data["source"],
                        trigger_data["event_type"],
                        trigger_data["priority"],
                        json.dumps(trigger_data.get("payload", {})),
                        trigger_data.get("checksum", ""),
                        1 if trigger_data.get("offline_staged", False) else 0,
                        trigger_data.get("timestamp", time.time()),
                        status
                    ))
                    conn.commit()
                    is_fresh = True
                except sqlite3.IntegrityError:
                    is_fresh = False

        if not is_fresh:
            # Idempotency key already registered!
            self.log_event("WARNING", "STORAGE", "TRIGGER_DEDUPLICATED", {
                "idempotency_key": trigger_data["idempotency_key"],
                "trigger_id": trigger_data["trigger_id"]
            })
        return is_fresh

    def get_trigger(self, trigger_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM triggers WHERE trigger_id = ?", (trigger_id,)).fetchone()
            if row:
                d = dict(row)
                d["payload"] = json.loads(d["payload_json"])
                return d
            return None

    def get_trigger_by_idempotency_key(self, key: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM triggers WHERE idempotency_key = ?", (key,)).fetchone()
            if row:
                d = dict(row)
                d["payload"] = json.loads(d["payload_json"])
                return d
            return None

    def list_triggers(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM triggers ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["payload"] = json.loads(d["payload_json"])
                results.append(d)
            return results

    # --- Outbox / Queue Management ---
    def enqueue_outbox(self, item_type: str, idempotency_key: str, payload: Dict[str, Any]) -> str:
        queue_id = f"q_{uuid.uuid4().hex[:10]}"
        now = time.time()
        with self.get_connection() as conn:
            try:
                conn.execute("""
                INSERT INTO outbox_queue (
                    queue_id, idempotency_key, item_type, payload_json, status,
                    attempts, created_at, last_attempt_at
                ) VALUES (?, ?, ?, ?, 'STAGED_OFFLINE', 0, ?, NULL)
                """, (queue_id, idempotency_key, item_type, json.dumps(payload), now))
                conn.commit()
                return queue_id
            except sqlite3.IntegrityError:
                # Already enqueued
                return ""

    def get_pending_outbox_items(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("""
            SELECT * FROM outbox_queue 
            WHERE status IN ('STAGED_OFFLINE', 'SYNCING', 'FAILED') 
            ORDER BY created_at ASC
            """).fetchall()
            items = []
            for r in rows:
                d = dict(r)
                d["payload"] = json.loads(d["payload_json"])
                items.append(d)
            return items

    def update_queue_status(self, queue_id: str, status: str, error_message: Optional[str] = None):
        with self.get_connection() as conn:
            now = time.time()
            reconciled = now if status in ("ACKNOWLEDGED", "DEDUPLICATED") else None
            conn.execute("""
            UPDATE outbox_queue 
            SET status = ?, attempts = attempts + 1, last_attempt_at = ?, 
                reconciled_at = COALESCE(reconciled_at, ?), error_message = ?
            WHERE queue_id = ?
            """, (status, now, reconciled, error_message, queue_id))
            conn.commit()

    # --- Graph Executions ---
    def record_execution(self, state: Dict[str, Any]):
        with self.get_connection() as conn:
            conn.execute("""
            INSERT OR REPLACE INTO graph_executions (
                execution_id, graph_id, trigger_id, status, execution_trace_json,
                actions_dispatched_json, executed_offline, created_at, completed_at, reconciled_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                state["execution_id"],
                state["graph_id"],
                state["trigger_id"],
                state["status"],
                json.dumps(state.get("execution_trace", [])),
                json.dumps(state.get("actions_dispatched", [])),
                1 if state.get("executed_offline", False) else 0,
                state.get("created_at", time.time()),
                state.get("completed_at"),
                state.get("reconciled_at")
            ))
            conn.commit()

    def get_execution(self, execution_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM graph_executions WHERE execution_id = ?", (execution_id,)).fetchone()
            if row:
                d = dict(row)
                d["execution_trace"] = json.loads(d["execution_trace_json"])
                d["actions_dispatched"] = json.loads(d["actions_dispatched_json"])
                d["executed_offline"] = bool(d["executed_offline"])
                return d
            return None

    def list_executions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM graph_executions ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["execution_trace"] = json.loads(d["execution_trace_json"])
                d["actions_dispatched"] = json.loads(d["actions_dispatched_json"])
                d["executed_offline"] = bool(d["executed_offline"])
                results.append(d)
            return results

    # --- Dispatched Actions (Side-Effects) ---
    def record_action(self, action_id: str, idempotency_key: str, action_type: str, 
                      params: Dict[str, Any], offline: bool, result: Dict[str, Any]) -> bool:
        duplicate_found = False
        with self.lock:
            with self.get_connection() as conn:
                # Check if this exact idempotency key + action_type already ran
                existing = conn.execute(
                    "SELECT action_id FROM dispatched_actions WHERE idempotency_key = ? AND action_type = ?",
                    (idempotency_key, action_type)
                ).fetchone()
                if existing:
                    duplicate_found = True
                else:
                    conn.execute("""
                    INSERT INTO dispatched_actions (
                        action_id, idempotency_key, action_type, params_json, executed_at,
                        offline_execution, result_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        action_id,
                        idempotency_key,
                        action_type,
                        json.dumps(params),
                        time.time(),
                        1 if offline else 0,
                        json.dumps(result)
                    ))
                    conn.commit()

        if duplicate_found:
            self.log_event("WARNING", "ACTION_ENGINE", "DUPLICATE_ACTION_SUPPRESSED", {
                "idempotency_key": idempotency_key,
                "action_type": action_type
            })
            return False  # Prevent duplicate execution!

        return True

    def list_actions(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM dispatched_actions ORDER BY executed_at DESC LIMIT ?", (limit,)).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["params"] = json.loads(d["params_json"])
                d["result"] = json.loads(d["result_json"])
                results.append(d)
            return results

    # --- Audit Logs ---
    def log_event(self, level: str, component: str, event: str, details: Dict[str, Any]):
        with self.get_connection() as conn:
            conn.execute("""
            INSERT INTO audit_logs (timestamp, level, component, event, details_json)
            VALUES (?, ?, ?, ?, ?)
            """, (time.time(), level, component, event, json.dumps(details)))
            conn.commit()

    def list_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
            results = []
            for r in rows:
                d = dict(r)
                d["details"] = json.loads(d["details_json"])
                results.append(d)
            return results

    def get_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            triggers_count = conn.execute("SELECT COUNT(*) FROM triggers").fetchone()[0]
            offline_triggers = conn.execute("SELECT COUNT(*) FROM triggers WHERE offline_staged = 1").fetchone()[0]
            pending_queue = conn.execute("SELECT COUNT(*) FROM outbox_queue WHERE status IN ('STAGED_OFFLINE', 'SYNCING')").fetchone()[0]
            acknowledged_queue = conn.execute("SELECT COUNT(*) FROM outbox_queue WHERE status = 'ACKNOWLEDGED'").fetchone()[0]
            deduplicated_count = conn.execute("SELECT COUNT(*) FROM outbox_queue WHERE status = 'DEDUPLICATED'").fetchone()[0]
            total_actions = conn.execute("SELECT COUNT(*) FROM dispatched_actions").fetchone()[0]
            offline_actions = conn.execute("SELECT COUNT(*) FROM dispatched_actions WHERE offline_execution = 1").fetchone()[0]
            executions_count = conn.execute("SELECT COUNT(*) FROM graph_executions").fetchone()[0]

            return {
                "triggers_count": triggers_count,
                "offline_triggers": offline_triggers,
                "pending_queue": pending_queue,
                "acknowledged_queue": acknowledged_queue,
                "deduplicated_count": deduplicated_count,
                "total_actions": total_actions,
                "offline_actions": offline_actions,
                "executions_count": executions_count
            }

# Global database singleton
db = Database()
