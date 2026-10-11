# AegisFlow // Resilient Agentic Decision Orchestrator

[![Grevix AfterCode](https://img.shields.io/badge/Grevix%20AfterCode-Phase%202:%20The%20Shift-00f2fe?style=for-the-badge)](https://unstop.com)
[![Challenge Card 01](https://img.shields.io/badge/Challenge%20Card%2001-Network%20Dropout%20Resilience-10b981?style=for-the-badge)](#)
[![Python](https://img.shields.io/badge/Python-3.13-blue?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)

> **"One Builder. One Idea. 24 Hours. No Boundaries."**  
> AegisFlow is an edge-to-cloud Agentic Workflow Orchestrator engineered to survive severe network disruptions and continue executing mission-critical decision logic graphs without downtime or data loss.

---

## 🚀 The Disruption: Challenge Card 01

### The Scenario:
In a remote industrial facility (e.g. offshore drilling platform, remote solar farm, isolated pipeline valve station), an operations manager relies on real-time agentic decision workflows. Suddenly, the network uplink drops completely (0 Mbps). 

Under traditional LLM architectures, incoming triggers stall, requests time out with HTTP 500 errors, and critical safety commands are lost.

### The Solution:
AegisFlow redesigns the agentic platform with a **Local-First, Dual-Mode Resilient Architecture**:
1. **Write-Ahead Outbox Queue (WAL Mode):** Triggers are instantly persisted to a crash-resilient local SQLite WAL outbox with SHA-256 checksums and cryptographic idempotency keys.
2. **Dual-Mode Agentic DAG Engine:** When offline, workflows automatically switch to an **Autonomous Edge Local Fallback Agent** that evaluates safety boundaries and executes physical actuator fail-safes (e.g. `EMERGENCY_SHUTDOWN`, `DEPLOY_DRONE`) in sub-5ms without cloud connectivity.
3. **Store-and-Forward Reconciler:** Background health monitors detect uplink restoration and trigger an automated monotonic reconciliation that flushes the outbox with zero data loss.
4. **Exactly-Once Idempotency Guarantee:** Enforces atomic constraints preventing duplicate triggers or duplicate actuator side-effects during network retry storms.

---

## ⚡ Quickstart

### 1. Installation
Ensure Python 3.10+ is installed. Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Run the AegisFlow Server
Start the FastAPI server:
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
or run `run.bat` (Windows) / `run.sh` (Linux/macOS).

Open your browser to:
👉 **`http://localhost:8000`** to access the interactive web dashboard!

### 3. Run the Automated Proof Verification Suite
Execute the concrete proof benchmark directly in your terminal:
```bash
python tests/test_network_resilience.py
```

---

## 📊 Concrete Proof of Resilience

AegisFlow provides verifiable proof of its resilience through both the automated CLI test runner and the interactive 1-click proof suite on the dashboard:

```text
======================================================================
 ALL TESTS PASSED! [100% SUCCESS in 993.75ms]
======================================================================
CONCRETE PROOF ESTABLISHED:
 [PASS] System survives 100% network blackout with zero data loss (RPO = 0)
 [PASS] Decision Logic Graph continues autonomous execution on Edge Node
 [PASS] Store-and-Forward WAL safely buffers outbox without dropping triggers
 [PASS] Post-reconnect reconciliation drains queue in < 50ms (RTO < 50ms)
 [PASS] Exactly-once idempotency guarantees zero duplicate side-effects
======================================================================
```

| Metric | Target | AegisFlow Benchmark Result | Status |
| :--- | :--- | :--- | :--- |
| **Data Loss Rate** | 0% | **0.0%** (Zero dropped triggers) | **PASSED** |
| **Recovery Point Objective (RPO)** | 0 | **0 triggers lost** | **PASSED** |
| **Recovery Time Objective (RTO)** | < 100ms | **30 - 45ms** | **PASSED** |
| **Edge Decision Latency** | < 50ms | **< 5ms** | **PASSED** |
| **Idempotency Deduplication** | 100% | **100%** (0 duplicate side-effects) | **PASSED** |

---

## 🛠️ Architecture & System Design

```
[Remote Operations Tablet / Field Sensors]
                   │
                   ▼ (Trigger + Idempotency Key)
        ┌──────────────────────────────────────┐
        │       Network Sentinel Layer         │
        └──────────────────┬───────────────────┘
                           │
             ┌─────────────┴─────────────┐
             │ Connectivity Check        │
             ▼                           ▼
      [ONLINE (Fast-Path)]        [NETWORK DROPOUT (Failsafe)]
             │                           │
             │                           ├─► 1. Local SQLite WAL Outbox Buffer
             │                           │      (Immutable event store, 0 data loss)
             │                           │
             ▼                           ├─► 2. Edge Autonomous Failsafe Agent
     Cloud LLM Multi-Agent               │      (Deterministic heuristic DAG execution)
     Synthesis & Global Sync             │
             │                           ├─► 3. Local Actuator Dispatch
             │                           │      (Immediate valve cutoff / drone deploy)
             │                           │
             │                           └─► 4. Store-and-Forward Reconciler
             │                                  (Awaits heartbeat -> flushes outbox
             │                                   with idempotency deduplication)
             ▼                           ▼
    [Global State Store] ◄─────── [Reconciliation Protocol]
```

### Key Modules:
- **`app/models/`**: Pydantic schemas for triggers, DAG nodes, resilience configs, and outbox queues.
- **`app/core/storage.py`**: SQLite WAL persistence layer with thread-safe connection pooling, atomic outbox queues, and audit logs.
- **`app/core/agent_engine.py`**: Dual-Mode Reasoner featuring Cloud LLM synthesis and Edge Local Fallback Agent.
- **`app/core/graph_executor.py`**: DAG execution engine supporting triggers, condition branching, agent reasoning, and actuator dispatch.
- **`app/core/chaos_simulator.py`**: Live network chaos engine simulating latency, jitter, packet loss, and total blackouts.
- **`app/core/resilience_manager.py`**: Store-and-forward outbox orchestrator, heartbeat probe, and conflict-free reconciler.
- **`app/static/`**: Futuristic web dashboard with real-time DAG node visualization, chaos injection, operations console, and proof runner.

---

## 📂 Project Structure

```text
C:\Projects\Grevix_AfterCode\
├── app/
│   ├── api/
│   │   ├── routes_triggers.py       # POST /api/triggers with network interception
│   │   ├── routes_graphs.py         # GET /api/graphs and execution traces
│   │   ├── routes_resilience.py     # Network chaos control & outbox sync
│   │   └── routes_proof.py          # 6-phase automated proof benchmark
│   ├── core/
│   │   ├── storage.py               # SQLite WAL event store & outbox
│   │   ├── agent_engine.py          # Dual-Mode AI reasoner (Cloud / Edge)
│   │   ├── graph_executor.py        # Decision logic graph DAG executor
│   │   ├── resilience_manager.py    # Store-and-forward outbox & reconciler
│   │   └── chaos_simulator.py       # Online/Degraded/Blackout/Flapping simulator
│   ├── models/                      # Pydantic data models
│   ├── static/                      # Interactive Web Console UI
│   ├── config.py                    # System configuration
│   └── main.py                      # FastAPI server
├── docs/
│   ├── CHALLENGE_CARD_01.md         # Full Challenge Card 01 adaptation report
│   ├── ARCHITECTURE.md              # Detailed architecture & Mermaid specs
│   └── DECISION_LOG.md              # Grevix Build & Decision Log
├── tests/
│   └── test_network_resilience.py   # Automated CLI verification suite
├── requirements.txt
├── run.bat
├── run.sh
└── README.md
```

---

## 🏆 Grevix AfterCode Submission Deliverables

- **Project Name:** AegisFlow
- **Core Pitch:** Resilient Distributed Agentic Workflow Orchestrator with Network Dropout Fault-Tolerance & Store-and-Forward Reconciler.
- **Challenge Card 01 Evolution:** Adapted from a naive cloud-dependent agent to an edge-resilient local-first architecture with dual-mode reasoning, SQLite WAL outbox, and idempotent reconciliation.
- **Tech Stack:** Python 3.13, FastAPI, SQLite WAL, Pydantic v2, Vanilla JS / CSS3, Lucide Icons.
- **Build Log:** Available in [`docs/DECISION_LOG.md`](file:///C:/Projects/Grevix_AfterCode/docs/DECISION_LOG.md).
- **Challenge Report:** Available in [`docs/CHALLENGE_CARD_01.md`](file:///C:/Projects/Grevix_AfterCode/docs/CHALLENGE_CARD_01.md).

---

*Engineered with precision for Grevix AfterCode 2026.*
