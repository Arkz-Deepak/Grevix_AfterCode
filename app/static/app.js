// AegisFlow Client Controller & Real-Time Monitor

let currentPreset = {
  event_type: "PRESSURE_SPIKE_ALERT",
  priority: "CRITICAL",
  reading: 98.4,
  threshold: 80.0,
  critical_threshold: 95.0,
  unit: "psi",
  sensor_id: "VALVE-402",
  zone: "SECTOR_DELTA"
};

// Polling interval for live sync
let pollTimer = null;

document.addEventListener("DOMContentLoaded", () => {
  fetchStatus();
  fetchAuditLogs();
  pollTimer = setInterval(fetchStatus, 2500);

  // Sync button listener
  document.getElementById("btnSyncNow").addEventListener("click", manualSync);
});

function logToTerminal(level, component, msg) {
  const terminal = document.getElementById("terminalLog");
  const line = document.createElement("div");
  line.className = "terminal-line";

  const d = new Date();
  const timeStr = `[${d.toTimeString().split(' ')[0]}]`;

  let lvlClass = "t-info";
  if (level === "WARNING") lvlClass = "t-warn";
  if (level === "ERROR") lvlClass = "t-err";
  if (level === "SUCCESS") lvlClass = "t-success";

  line.innerHTML = `<span class="t-time">${timeStr}</span> <span class="${lvlClass}">[${component}]</span> ${escapeHtml(msg)}`;
  terminal.appendChild(line);
  terminal.scrollTop = terminal.scrollHeight;
}

function escapeHtml(text) {
  return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function clearLogWindow() {
  document.getElementById("terminalLog").innerHTML = "";
}

// --- Status & Polling ---
async function fetchStatus() {
  try {
    const res = await fetch("/api/resilience/status");
    if (!res.ok) throw new Error("Status endpoint unavailable");
    const data = await res.json();

    updateNetworkUI(data.network);
    updateStatsUI(data.stats);
    updateInterlockUI(data.manual_override_enabled);
  } catch (err) {
    // If backend is unreachable (simulating client-side disconnect)
    console.warn("Connection poll failed:", err);
  }
}

function updateInterlockUI(enabled) {
  const btn = document.getElementById("btnSafetyInterlock");
  const txt = document.getElementById("interlockText");
  if (!btn || !txt) return;
  if (enabled) {
    btn.style.background = "rgba(244, 63, 94, 0.2)";
    btn.style.borderColor = "var(--rose)";
    btn.style.color = "var(--rose)";
    txt.textContent = "SAFETY INTERLOCK: ACTIVE (HALTED)";
  } else {
    btn.style.background = "";
    btn.style.borderColor = "rgba(245, 158, 11, 0.4)";
    btn.style.color = "var(--text-main)";
    txt.textContent = "SAFETY INTERLOCK: OFF";
  }
}

async function toggleSafetyInterlock() {
  try {
    const isCurrentlyActive = document.getElementById("interlockText").textContent.includes("ACTIVE");
    const nextState = !isCurrentlyActive;
    const res = await fetch("/api/resilience/override", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled: nextState })
    });
    const data = await res.json();
    updateInterlockUI(data.manual_override_enabled);
    logToTerminal(nextState ? "WARNING" : "SUCCESS", "OPERATOR_LOCKOUT", data.message);
  } catch (err) {
    logToTerminal("ERROR", "OPERATOR_LOCKOUT", `Failed to toggle interlock: ${err.message}`);
  }
}

async function toggleOutboxInspector() {
  const panel = document.getElementById("outboxInspectorPanel");
  const content = document.getElementById("outboxInspectorContent");
  if (!panel || !content) return;

  if (panel.style.display === "block") {
    panel.style.display = "none";
    return;
  }

  panel.style.display = "block";
  content.innerHTML = "Fetching staged outbox items...";

  try {
    const res = await fetch("/api/resilience/outbox");
    const items = await res.json();
    if (!items || items.length === 0) {
      content.innerHTML = "<div style='color: var(--text-muted);'>Outbox is empty (all items reconciled).</div>";
      return;
    }

    let html = "";
    items.forEach(it => {
      const statusColor = it.status === "ACKNOWLEDGED" ? "var(--emerald)" : "var(--amber)";
      html += `<div style="border-bottom: 1px solid rgba(255,255,255,0.06); padding: 4px 0;">
        <span style="color: ${statusColor}; font-weight: bold;">[${it.status}]</span> 
        <strong>${it.item_type}:</strong> ${it.idempotency_key} 
        <span style="color: #64748b;">(Attempts: ${it.attempts})</span><br>
        <span style="color: #94a3b8; font-size: 0.68rem;">Event: ${it.payload.event_type || 'N/A'} | Sensor: ${it.payload.payload?.sensor_id || 'N/A'}</span>
      </div>`;
    });
    content.innerHTML = html;
  } catch (err) {
    content.innerHTML = `<span style='color: var(--rose);'>Failed to load outbox: ${err.message}</span>`;
  }
}

function updateNetworkUI(network) {
  const pill = document.getElementById("statusPill");
  const text = document.getElementById("statusText");
  const latencyInd = document.getElementById("latencyIndicator");
  const desc = document.getElementById("linkDesc");
  const modeBadge = document.getElementById("activeModeBadge");

  // Reset classes
  pill.className = "status-pill";
  document.querySelectorAll(".chaos-btn").forEach(btn => btn.classList.remove("active", "blackout", "degraded"));

  if (network.mode === "ONLINE") {
    pill.classList.add("status-online");
    text.textContent = "ONLINE // FAST LINK";
    latencyInd.textContent = `${network.latency_ms}ms (0% Loss)`;
    document.getElementById("btnModeOnline").classList.add("active");
    modeBadge.textContent = "ONLINE CLOUD AGENT";
    modeBadge.className = "badge-tag";
  } else if (network.mode === "DEGRADED") {
    pill.classList.add("status-degraded");
    text.textContent = `DEGRADED // JITTER (${network.latency_ms}ms)`;
    latencyInd.textContent = `${network.latency_ms}ms (${Math.round(network.packet_loss_rate * 100)}% Loss)`;
    const btn = document.getElementById("btnModeDegraded");
    btn.classList.add("active", "degraded");
    modeBadge.textContent = "DEGRADED / DUAL-MODE";
  } else if (network.mode === "BLACKOUT") {
    pill.classList.add("status-blackout");
    text.textContent = "BLACKOUT // 0 MBPS SEVERED";
    latencyInd.textContent = "OFFLINE (100% Drop)";
    const btn = document.getElementById("btnModeBlackout");
    btn.classList.add("active", "blackout");
    modeBadge.textContent = "EDGE AUTONOMOUS FAILSAFE";
    modeBadge.className = "badge-tag";
    modeBadge.style.background = "rgba(244, 63, 94, 0.2)";
    modeBadge.style.color = "var(--rose)";
    modeBadge.style.borderColor = "var(--rose)";
  } else if (network.mode === "FLAPPING") {
    pill.classList.add("status-degraded");
    text.textContent = "FLAPPING // UNSTABLE LINK";
    latencyInd.textContent = "INTERMITTENT";
    document.getElementById("btnModeFlapping").classList.add("active", "degraded");
    modeBadge.textContent = "STORE-AND-FORWARD BUFFERING";
  }

  desc.textContent = network.description || "Operational";
}

function updateStatsUI(stats) {
  if (!stats) return;
  document.getElementById("valPendingOutbox").textContent = stats.pending_queue || 0;
  document.getElementById("valReconciled").textContent = stats.acknowledged_queue || 0;
  document.getElementById("valDeduplicated").textContent = stats.deduplicated_count || 0;
  document.getElementById("valEdgeExecs").textContent = stats.offline_actions || 0;
}

// --- Chaos Control ---
async function setChaosMode(mode) {
  try {
    logToTerminal("WARNING", "CHAOS_INJECTOR", `Injecting network environment change: ${mode}...`);
    const res = await fetch("/api/resilience/chaos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: mode })
    });
    const updated = await res.json();
    updateNetworkUI(updated);
    logToTerminal("INFO", "CHAOS_INJECTOR", `Network state transition complete: ${updated.description}`);
  } catch (err) {
    logToTerminal("ERROR", "CHAOS_INJECTOR", `Failed to set chaos mode: ${err.message}`);
  }
}

// --- Operations Manager Trigger Sending ---
function loadPreset(presetName) {
  if (presetName === "NORMAL") {
    currentPreset = {
      event_type: "NOMINAL_TELEMETRY",
      priority: "LOW",
      reading: 45.0,
      threshold: 80.0,
      critical_threshold: 95.0,
      unit: "psi",
      sensor_id: "VALVE-402",
      zone: "SECTOR_DELTA"
    };
    logToTerminal("INFO", "CONSOLE", "Loaded Preset: Nominal Baseline (45 psi).");
  } else if (presetName === "WARNING") {
    currentPreset = {
      event_type: "PRESSURE_ANOMALY",
      priority: "HIGH",
      reading: 88.0,
      threshold: 80.0,
      critical_threshold: 95.0,
      unit: "psi",
      sensor_id: "PUMP-109",
      zone: "SECTOR_DELTA"
    };
    logToTerminal("WARNING", "CONSOLE", "Loaded Preset: Elevated Leak Risk (88 psi).");
  } else if (presetName === "CRITICAL") {
    currentPreset = {
      event_type: "PRESSURE_SPIKE_ALERT",
      priority: "CRITICAL",
      reading: 98.4,
      threshold: 80.0,
      critical_threshold: 95.0,
      unit: "psi",
      sensor_id: "VALVE-402",
      zone: "SECTOR_DELTA"
    };
    logToTerminal("WARNING", "CONSOLE", "Loaded Preset: Critical Blowout Risk (98.4 psi).");
  }
}

async function sendActiveTrigger() {
  const btn = document.getElementById("btnSendTrigger");
  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader" class="spin"></i> <span>PROCESSING TRIGGER...</span>`;

  const payload = {
    trigger_id: "trig_" + Math.random().toString(36).substring(2, 9),
    idempotency_key: "key_" + Math.random().toString(36).substring(2, 11),
    source: "remote_ops_manager_tablet",
    event_type: currentPreset.event_type,
    priority: currentPreset.priority,
    payload: currentPreset
  };

  logToTerminal("INFO", "DISPATCHER", `Transmitting trigger [${payload.event_type}] with Idempotency Key: ${payload.idempotency_key}...`);

  try {
    const res = await fetch("/api/triggers", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const result = await res.json();

    if (result.processed_mode === "OFFLINE_BUFFERED") {
      logToTerminal("WARNING", "RESILIENCE_STORE", `[OFFLINE FALLBACK ACTIVATED] ${result.message}`);
    } else if (result.processed_mode === "ONLINE_REALTIME") {
      logToTerminal("SUCCESS", "CLOUD_ORCHESTRATOR", `[ONLINE REALTIME] Processed via cloud: ${result.execution_id}`);
    } else {
      logToTerminal("INFO", "IDEMPOTENCY_ENGINE", `[DEDUPLICATED] ${result.message}`);
    }

    if (result.execution_id) {
      highlightGraphExecution(result.execution_id);
    }
  } catch (err) {
    logToTerminal("ERROR", "NETWORK", `Trigger transmission failed: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="send" style="width: 16px; height: 16px;"></i> <span>DISPATCH TRIGGER TO ENGINE</span>`;
    lucide.createIcons();
    fetchStatus();
  }
}

// Highlight the DAG steps for an execution
async function highlightGraphExecution(executionId) {
  try {
    const res = await fetch(`/api/graphs/executions/${executionId}`);
    if (!res.ok) return;
    const exec = await res.json();

    // Reset all DAG nodes
    document.querySelectorAll(".dag-node").forEach(node => {
      node.classList.remove("active", "offline-active");
    });

    const isOffline = exec.executed_offline;
    const activeClass = isOffline ? "offline-active" : "active";

    // Sequentially highlight nodes
    for (let i = 0; i < exec.execution_trace.length; i++) {
      const step = exec.execution_trace[i];
      const el = document.getElementById(`node-${step.node_id}`);
      if (el) {
        el.classList.add(activeClass);
      }

      if (step.node_type === "AGENT_DECISION") {
        const cotBox = document.getElementById("cotDisplay");
        const cotText = document.getElementById("cotText");
        cotBox.style.display = "block";
        cotBox.className = isOffline ? "cot-box offline" : "cot-box";
        cotText.textContent = step.reasoning || "Reasoning complete.";
      }
    }

    // Display dispatched action
    if (exec.actions_dispatched && exec.actions_dispatched.length > 0) {
      const act = exec.actions_dispatched[0];
      const card = document.getElementById("lastActionCard");
      const title = document.getElementById("lastActionTitle");
      const details = document.getElementById("lastActionDetails");
      card.style.display = "block";
      title.textContent = `${act.action_type} (${act.offline ? "AUTONOMOUS EDGE FAILSAFE" : "ONLINE DISPATCH"})`;
      details.textContent = JSON.stringify(act.params);
    }

  } catch (err) {
    console.error("Failed to render graph execution trace:", err);
  }
}

// --- Manual Reconciliation ---
async function manualSync() {
  const btn = document.getElementById("btnSyncNow");
  btn.disabled = true;
  logToTerminal("INFO", "RECONCILER", "Starting Store-and-Forward Outbox drain...");

  try {
    const res = await fetch("/api/resilience/sync", { method: "POST" });
    const report = await res.json();
    logToTerminal("SUCCESS", "RECONCILER", `Reconciliation complete: ${report.items_reconciled} items acknowledged, ${report.duplicates_prevented} duplicates prevented (${report.execution_time_ms}ms).`);
    fetchStatus();
  } catch (err) {
    logToTerminal("ERROR", "RECONCILER", `Reconciliation error: ${err.message}`);
  } finally {
    btn.disabled = false;
  }
}

// --- Run Concrete Proof Benchmark (Challenge Card 01 Hero) ---
async function runConcreteProof() {
  const btn = document.getElementById("btnRunProof");
  const resultsBox = document.getElementById("proofResultsBox");
  const phasesList = document.getElementById("proofPhasesList");

  btn.disabled = true;
  btn.innerHTML = `<i data-lucide="loader" class="spin"></i> <span>RUNNING 6-PHASE PROOF SUITE...</span>`;
  resultsBox.style.display = "none";
  phasesList.innerHTML = "";

  logToTerminal("WARNING", "BENCHMARK", ">>> STARTING CONCRETE PROOF OF NETWORK RESILIENCE (CHALLENGE CARD 01) <<<");

  try {
    const res = await fetch("/api/proof/run-simulation", { method: "POST" });
    if (!res.ok) throw new Error("Proof runner failed");
    const data = await res.json();

    logToTerminal("SUCCESS", "BENCHMARK", `All 6 resilience phases executed in ${data.total_duration_ms}ms. Overall Verdict: ${data.overall_verdict}`);

    // Update UI Metrics
    resultsBox.style.display = "block";
    document.getElementById("proofDataLoss").textContent = `${data.metrics.data_loss_percentage}%`;
    document.getElementById("proofRTO").textContent = `${data.metrics.recovery_time_objective_ms}ms`;
    document.getElementById("proofDedupe").textContent = data.metrics.idempotency_compliance;

    // Render Phases List
    data.phases.forEach(ph => {
      const pDiv = document.createElement("div");
      pDiv.style.marginBottom = "6px";
      pDiv.innerHTML = `<span style="color: var(--cyan); font-weight: bold;">[${ph.status}]</span> <strong>${ph.phase}:</strong> ${ph.description}`;
      phasesList.appendChild(pDiv);
    });

    fetchStatus();

  } catch (err) {
    logToTerminal("ERROR", "BENCHMARK", `Proof run aborted: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i data-lucide="zap" style="width: 18px; height: 18px;"></i> <span>RUN 6-PHASE PROOF TEST</span>`;
    lucide.createIcons();
  }
}

async function fetchAuditLogs() {
  try {
    const res = await fetch("/api/resilience/audit-logs?limit=15");
    if (!res.ok) return;
    const logs = await res.json();
    logs.reverse().forEach(l => {
      logToTerminal(l.level, l.component, `${l.event}: ${JSON.stringify(l.details)}`);
    });
  } catch (e) {}
}
