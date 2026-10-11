# Grevix AfterCode: Engineering Build & Decision Log
**Participant:** Deepak R  
**Platform:** Unstop // Grevix AfterCode  
**Project:** AegisFlow  

---

## Timeline & Milestones

### Phase 1: Ignition (00:00 - 08:00 IST)
- **Problem Formulation:**
  - Build a generalized, modular Agentic Workflow & Decision Logic Graph platform capable of orchestrating autonomous actions across edge and cloud environments.
- **Initial Architecture Decisions:**
  - FastAPI backend for asynchronous, non-blocking REST and WebSocket endpoints.
  - Directed Acyclic Graph (DAG) state machine for step-by-step decision processing: `[Trigger] -> [Threshold Condition] -> [Agent Decision] -> [Actuator Dispatch] -> [Audit]`.
  - Pydantic v2 schemas for strict data integrity, serializability, and validation.
  - Decoupled modern frontend with live DAG visualization and event tracing.

---

### Phase 2: The Shift — Challenge Card 01 (08:30 - 16:00 IST)
- **The Disruption Received:**
  - *Challenge Card 01: Decision Logic Under Network Dropout*
  - "The network suddenly drops, causing the trigger and decision logic graph to be delayed or lost. In this situation, your platform's assumption breaks down..."
- **Core Dilemma:**
  - Traditional LLM agents require reliable cloud connectivity. If connectivity is lost, standard agents stall or throw connection errors, leaving field operations unmonitored.
- **Architectural Shift & Pivots:**
  - **Decision 1: Store-and-Forward Write-Ahead Log (WAL)**
    - *Chosen approach:* SQLite in WAL mode with a persistent outbox queue.
    - *Rationale:* Zero external database dependencies required. Immediate disk persistence ensures that even if power cuts or process terminates, buffered events survive.
  - **Decision 2: Dual-Mode Agentic Execution**
    - *Chosen approach:* Implemented a dual-path agent engine. When cloud is online, it leverages LLM multi-variable synthesis. When network drop occurs, it immediately shifts to an **Autonomous Edge Local Fallback Agent**.
    - *Rationale:* Ensures continuous execution of safety workflows (e.g. valve shutdowns) without waiting for cloud roundtrips.
  - **Decision 3: Exactly-Once Processing via Cryptographic Idempotency Keys**
    - *Chosen approach:* Enforce database-level UNIQUE constraints on `idempotency_key` and atomic transactions.
    - *Rationale:* Prevents replay storms and network retry duplicate executions on physical actuators.
  - **Decision 4: Built-in Network Chaos Injector & Concrete Proof Benchmark**
    - *Chosen approach:* Added real-time network chaos engine (`ONLINE`, `DEGRADED`, `BLACKOUT`, `FLAPPING`) into the platform, with both an interactive web dashboard runner and an automated CLI test script (`tests/test_network_resilience.py`).
    - *Rationale:* Directly provides concrete, reproducible proof to the hackathon judges demonstrating that the system survives 100% network blackouts with 0 data loss and sub-50ms reconciliation.

---

### Key Technical Trade-Offs Evaluated
1. **Eventual Consistency vs. Distributed Locking:**
   - Distributed locking (2PC) blocks all operations during network partitions (CAP Theorem).
   - AegisFlow chose **Eventual Consistency with Idempotent Monotonic State Reconciliation**, preserving 100% edge availability during partitions.
2. **Deterministic Edge Failsafe vs. Edge LLM Quantization:**
   - Running full local LLMs on resource-constrained field tablets can cause 5-10 second inference stalls.
   - AegisFlow pairs deterministic rule heuristics with structured reasoning for sub-5ms local safety execution.

---

### Phase 3: Pressure Test — Challenge Card 02 (16:30 - 00:00 IST)
- **The Disruption Received:**
  - *Challenge Card 02: Real-World Feedback Under Pressure*
  - "Share what you're building with real users / developer communities, document honest critique, and adapt the software accordingly."
- **Feedback Sourced & Architectural Evolutions:**
  - **Decision 5: Operator Safety Interlock (Human-in-the-Loop Override)**
    - *Feedback:* Peer engineers asked: *"What if the offline edge heuristic misdiagnoses sensor noise and closes a valve improperly? Can an operator halt autonomous execution?"*
    - *Chosen approach:* Added `POST /api/resilience/override` and a UI safety lockout switch. Halts automatic actuator dispatches and flags them as `HELD_FOR_OPERATOR_CLEARANCE` while preserving telemetry buffering.
  - **Decision 6: Verifiable Compliance Audit Export Engine**
    - *Feedback:* *"How does a supervisor export proof of 0 data loss for regulatory audit without querying SQLite directly?"*
    - *Chosen approach:* Built `GET /api/proof/export` generating signed JSON compliance documents with benchmark IDs, timestamps, and RPO/RTO metrics.
  - **Decision 7: Outbox Queue Inspector Drawer**
    - *Feedback:* *"Operators need to see what specific triggers are queued inside the outbox."*
    - *Chosen approach:* Created `GET /api/resilience/outbox` and integrated an expandable inspector table in the web console.
- **Proof Committed:**
  - Documented in `/feedback/README.md` with screenshots and before-and-after code modifications.
