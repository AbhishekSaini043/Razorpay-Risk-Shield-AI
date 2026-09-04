// Razorpay Risk Shield AI - Client Application Logic

let currentBatchResults = [];

document.addEventListener("DOMContentLoaded", () => {
  fetchModelInfo();
  fetchAnalytics();
  fetchAuditLog();
  // Auto-run initial evaluation with default values
  triggerLiveEvaluation();
});

// Tab Navigation
function switchTab(tabId) {
  document.querySelectorAll(".tab-pane").forEach(pane => pane.classList.remove("active"));
  document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));

  const targetPane = document.getElementById(`tab-${tabId}`);
  const targetBtn = document.getElementById(`tab-btn-${tabId}`);
  if (targetPane) targetPane.classList.add("active");
  if (targetBtn) targetBtn.classList.add("active");

  if (tabId === "analytics") fetchAnalytics();
  if (tabId === "audit") fetchAuditLog();
}

// Form Syncing Helpers
function syncAmount(val) {
  const num = Math.min(Math.max(Number(val) || 500, 100), 100000);
  document.getElementById("input-amount").value = num;
  document.getElementById("input-amount-num").value = num;
  document.getElementById("label-amount-val").innerText = `₹${num.toLocaleString('en-IN')}`;
}

function syncReturns(val) {
  const num = Math.min(Math.max(Number(val) || 0, 0), 20);
  document.getElementById("input-returns").value = num;
  document.getElementById("input-returns-num").value = num;
  document.getElementById("label-returns-val").innerText = `${num} ${num === 1 ? 'return' : 'returns'}`;
}

function syncDistance(val) {
  const num = Math.min(Math.max(Number(val) || 5, 1), 3000);
  document.getElementById("input-distance").value = num;
  document.getElementById("input-distance-num").value = num;
  document.getElementById("label-distance-val").innerText = `${num} km`;
}

function syncThreshold(val) {
  const pct = Math.round(Number(val) * 100);
  document.getElementById("label-threshold-val").innerText = `${pct}% ${pct === 22 ? '(Optimal Profit)' : 'Cutoff'}`;
}

function setCategoryPreset(riskVal, categoryName, btnElem) {
  document.getElementById("input-category-risk").value = riskVal;
  document.querySelectorAll(".chip-btn").forEach(btn => btn.classList.remove("active"));
  if (btnElem) btnElem.classList.add("active");
  document.getElementById("label-category-val").innerText = `${categoryName} (${riskVal})`;
}

function setPaymentMode(isCod) {
  document.getElementById("input-is-cod").value = isCod;
  const optCod = document.getElementById("opt-cod");
  const optPre = document.getElementById("opt-prepaid");
  if (isCod === 1) {
    optCod.classList.add("active");
    optPre.classList.remove("active");
  } else {
    optCod.classList.remove("active");
    optPre.classList.add("active");
  }
}

function populateRandomOrder() {
  const amounts = [1299, 2499, 4800, 8900, 14500];
  const returns = [0, 1, 2, 4, 6];
  const categories = [
    { name: "Fashion Apparel", risk: 0.75 },
    { name: "Consumer Electronics", risk: 0.55 },
    { name: "Home & Kitchen", risk: 0.40 },
    { name: "Books & Media", risk: 0.15 }
  ];
  const distances = [25, 80, 210, 450, 680];
  const codChoices = [1, 1, 1, 0];

  const amt = amounts[Math.floor(Math.random() * amounts.length)];
  const ret = returns[Math.floor(Math.random() * returns.length)];
  const cat = categories[Math.floor(Math.random() * categories.length)];
  const dist = distances[Math.floor(Math.random() * distances.length)];
  const isCod = codChoices[Math.floor(Math.random() * codChoices.length)];

  syncAmount(amt);
  syncReturns(ret);
  syncDistance(dist);
  setPaymentMode(isCod);

  // find matching category button
  const chips = document.querySelectorAll(".chip-btn");
  chips.forEach(chip => {
    if (chip.innerText.includes(cat.name.split(' ')[0])) {
      setCategoryPreset(cat.risk, cat.name, chip);
    }
  });

  triggerLiveEvaluation();
}

function handleSingleEvaluation(e) {
  if (e) e.preventDefault();
  triggerLiveEvaluation();
}

async function triggerLiveEvaluation() {
  const payload = {
    transaction_amount: parseFloat(document.getElementById("input-amount").value),
    user_history_returns: parseInt(document.getElementById("input-returns").value),
    item_category_risk: parseFloat(document.getElementById("input-category-risk").value),
    delivery_distance_km: parseFloat(document.getElementById("input-distance").value),
    is_cod: parseInt(document.getElementById("input-is-cod").value),
    threshold_override: parseFloat(document.getElementById("input-threshold").value)
  };

  const btn = document.getElementById("btn-submit-eval");
  if (btn) btn.disabled = true;

  try {
    const res = await fetch("/score-risk", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const data = await res.json();
    renderEvaluationResults(data);
  } catch (err) {
    console.error("Evaluation error:", err);
  } finally {
    if (btn) btn.disabled = false;
  }
}

function renderEvaluationResults(data) {
  const prob = data.risk_probability || 0.0;
  const pct = Math.round(prob * 100);

  // Animate Gauge
  const meter = document.getElementById("gauge-meter");
  const readout = document.getElementById("risk-score-display");
  const maxDash = 251.2;
  const offset = maxDash - (maxDash * prob);

  meter.style.strokeDashoffset = offset;
  readout.innerText = `${pct}%`;

  // Dynamic Gauge Color
  let gaugeColor = "var(--safe-green)";
  let tierClass = "badge-safe";

  if (prob >= 0.75) {
    gaugeColor = "var(--critical-purple)";
    tierClass = "badge-critical";
  } else if (prob >= 0.55) {
    gaugeColor = "var(--danger-red)";
    tierClass = "badge-danger";
  } else if (prob >= 0.30) {
    gaugeColor = "var(--warning-amber)";
    tierClass = "badge-warning";
  }

  meter.style.stroke = gaugeColor;
  readout.style.color = gaugeColor;

  // Tier Badge & Action
  const tierBadge = document.getElementById("tier-badge");
  tierBadge.className = `tier-badge ${tierClass}`;
  tierBadge.innerText = `${data.risk_tier || 'UNKNOWN'} RISK`;

  const actionBadge = document.getElementById("cod-action-badge");
  actionBadge.innerText = data.block_cod ? "COD RESTRICTED" : "COD PERMITTED";
  actionBadge.style.color = data.block_cod ? "var(--danger-red)" : "var(--safe-green)";

  // Recommendation text
  document.getElementById("recommendation-title").innerText = formatRecTitle(data.recommendation);
  document.getElementById("recommendation-desc").innerText = data.recommendation_description;

  // ROI Impact
  document.getElementById("roi-savings-val").innerText = data.block_cod ? "₹800 Saved" : "₹0 (Frictionless)";
  document.getElementById("roi-fp-val").innerText = data.block_cod ? "Low Loss Risk" : "None";

  // XAI Factors
  renderFactors(data.top_factors || []);
}

function formatRecTitle(rec) {
  const map = {
    "ALLOW_COD": "Allow Frictionless COD Checkout",
    "VERIFY_OTP_BEFORE_DISPATCH": "Send OTP Verification SMS Before Dispatch",
    "REQUIRE_PARTIAL_ADVANCE": "Require ₹150 Partial Advance Deposit",
    "BLOCK_COD_PREPAID_ONLY": "Block COD & Enforce Digital Prepaid Payment"
  };
  return map[rec] || rec || "Decision Complete";
}

function renderFactors(factors) {
  const container = document.getElementById("xai-factor-list");
  if (!factors || factors.length === 0) {
    container.innerHTML = '<div class="empty-factors">No abnormal risk factors detected. Order aligns with safe buyer profile.</div>';
    return;
  }

  container.innerHTML = factors.map(f => `
    <div class="factor-card">
      <div class="factor-info">
        <span class="factor-title">${f.factor}</span>
        <span class="factor-detail">${f.detail}</span>
      </div>
      <span class="factor-impact ${f.direction || 'safe'}">${f.impact}</span>
    </div>
  `).join("");
}

// ================= BATCH PROCESSING =================
async function loadSampleBatch() {
  const sampleTransactions = [
    { transaction_amount: 4999.0, user_history_returns: 4, item_category_risk: 0.85, delivery_distance_km: 350.0, is_cod: 1 },
    { transaction_amount: 1199.0, user_history_returns: 0, item_category_risk: 0.15, delivery_distance_km: 18.0, is_cod: 0 },
    { transaction_amount: 2799.0, user_history_returns: 2, item_category_risk: 0.55, delivery_distance_km: 120.0, is_cod: 1 },
    { transaction_amount: 8500.0, user_history_returns: 5, item_category_risk: 0.90, delivery_distance_km: 520.0, is_cod: 1 },
    { transaction_amount: 1850.0, user_history_returns: 1, item_category_risk: 0.35, delivery_distance_km: 45.0, is_cod: 1 },
    { transaction_amount: 6200.0, user_history_returns: 3, item_category_risk: 0.75, delivery_distance_km: 290.0, is_cod: 1 },
    { transaction_amount: 950.0, user_history_returns: 0, item_category_risk: 0.10, delivery_distance_km: 12.0, is_cod: 1 },
    { transaction_amount: 3400.0, user_history_returns: 2, item_category_risk: 0.60, delivery_distance_km: 160.0, is_cod: 0 },
    { transaction_amount: 12500.0, user_history_returns: 6, item_category_risk: 0.85, delivery_distance_km: 610.0, is_cod: 1 },
    { transaction_amount: 2100.0, user_history_returns: 0, item_category_risk: 0.40, delivery_distance_km: 65.0, is_cod: 1 }
  ];

  try {
    const res = await fetch("/score-risk/batch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ transactions: sampleTransactions })
    });
    const data = await res.json();
    displayBatchData(sampleTransactions, data.results, data);
  } catch (err) {
    console.error("Batch error:", err);
  }
}

async function handleCSVUpload(file) {
  if (!file) return;
  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch("/score-risk/upload-csv", {
      method: "POST",
      body: formData
    });
    const data = await res.json();
    if (data.error) {
      alert(data.error);
      return;
    }
    displayBatchData(data.sample_preview, data.sample_preview, data);
  } catch (err) {
    console.error("CSV Upload error:", err);
  }
}

function displayBatchData(inputs, results, summary) {
  currentBatchResults = [];
  const tbody = document.getElementById("batch-table-body");
  tbody.innerHTML = "";

  document.getElementById("batch-metrics-bar").style.display = "flex";
  document.getElementById("bm-total").innerText = summary.total_scored;
  document.getElementById("bm-blocked").innerText = summary.blocked_cod_count;
  document.getElementById("bm-savings").innerText = `₹${summary.total_estimated_savings_inr.toLocaleString('en-IN')}`;
  document.getElementById("btn-export-csv").disabled = false;

  results.forEach((res, i) => {
    const inp = inputs[i] || res;
    const isBlocked = res.block_cod;
    const tier = res.risk_tier || "LOW";

    currentBatchResults.push({
      id: i + 1,
      amount: inp.transaction_amount,
      returns: inp.user_history_returns,
      category_risk: inp.item_category_risk,
      distance: inp.delivery_distance_km,
      is_cod: inp.is_cod ? "COD" : "Prepaid",
      risk_prob: res.risk_probability,
      tier: tier,
      recommendation: res.recommendation,
      blocked: isBlocked
    });

    const tr = document.createElement("tr");
    tr.dataset.tier = isBlocked ? "blocked" : "safe";
    tr.innerHTML = `
      <td>#${i + 1}</td>
      <td><strong>₹${Number(inp.transaction_amount).toLocaleString('en-IN')}</strong></td>
      <td>${inp.user_history_returns}</td>
      <td>${inp.item_category_risk}</td>
      <td>${inp.delivery_distance_km} km</td>
      <td><span class="action-badge">${inp.is_cod ? '💵 COD' : '💳 Prepaid'}</span></td>
      <td><strong>${Math.round(res.risk_probability * 100)}%</strong></td>
      <td><span class="tier-badge ${getTierBadgeClass(tier)}">${tier}</span></td>
      <td><span style="font-size:0.775rem; color:${isBlocked ? 'var(--danger-red)' : 'var(--safe-green)'}; font-weight:600;">${res.recommendation}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

function getTierBadgeClass(tier) {
  switch (tier) {
    case "CRITICAL": return "badge-critical";
    case "HIGH": return "badge-danger";
    case "MEDIUM": return "badge-warning";
    default: return "badge-safe";
  }
}

function filterBatchTable(filter, btnElem) {
  document.querySelectorAll(".filter-pill").forEach(p => p.classList.remove("active"));
  if (btnElem) btnElem.classList.add("active");

  const rows = document.querySelectorAll("#batch-table-body tr");
  rows.forEach(r => {
    if (filter === "all") {
      r.style.display = "";
    } else if (filter === "blocked") {
      r.style.display = r.dataset.tier === "blocked" ? "" : "none";
    } else if (filter === "safe") {
      r.style.display = r.dataset.tier === "safe" ? "" : "none";
    }
  });
}

function exportResultsCSV() {
  if (currentBatchResults.length === 0) return;
  const headers = ["ID", "Amount", "Prior_Returns", "Category_Risk", "Distance_KM", "Payment_Mode", "Risk_Probability", "Tier", "Recommendation", "COD_Blocked"];
  const rows = currentBatchResults.map(r => [
    r.id, r.amount, r.returns, r.category_risk, r.distance, r.is_cod, r.risk_prob, r.tier, r.recommendation, r.blocked
  ]);

  let csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `scored_risk_batch_${new Date().toISOString().slice(0,10)}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// ================= ANALYTICS & AUDIT =================
async function fetchAnalytics() {
  try {
    const res = await fetch("/api/analytics");
    const data = await res.json();

    document.getElementById("kpi-total").innerText = data.total_transactions;
    document.getElementById("kpi-block-rate").innerText = `${data.block_rate_percent}%`;
    document.getElementById("kpi-blocked-count").innerText = `${data.blocked_cod_count} consignments blocked`;
    document.getElementById("kpi-savings").innerText = `₹${(data.estimated_savings_inr || 0).toLocaleString('en-IN')}`;

    // Update distribution bars
    const dist = data.tier_distribution || {};
    const total = data.total_transactions || 1;

    const setBar = (tier, count) => {
      const pct = Math.round((count / total) * 100);
      const bar = document.getElementById(`dist-bar-${tier}`);
      const cnt = document.getElementById(`dist-count-${tier}`);
      if (bar) bar.style.width = `${pct}%`;
      if (cnt) cnt.innerText = count;
    };

    setBar("low", dist.LOW || 0);
    setBar("med", dist.MEDIUM || 0);
    setBar("high", dist.HIGH || 0);
    setBar("crit", dist.CRITICAL || 0);

  } catch (err) {
    console.error("Analytics fetch error:", err);
  }
}

async function fetchAuditLog() {
  try {
    const res = await fetch("/api/audit-log?limit=30");
    const rows = await res.json();
    const tbody = document.getElementById("audit-table-body");
    tbody.innerHTML = "";

    if (rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="10" class="empty-state">No transaction logs available yet.</td></tr>';
      return;
    }

    rows.forEach(r => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>#${r.id}</td>
        <td><span style="font-size:0.75rem; color:var(--text-muted);">${r.created_at}</span></td>
        <td><strong>₹${Number(r.transaction_amount).toLocaleString('en-IN')}</strong></td>
        <td>${r.user_history_returns}</td>
        <td>${r.item_category_risk}</td>
        <td>${r.delivery_distance_km} km</td>
        <td><span class="action-badge">${r.is_cod ? '💵 COD' : '💳 Prepaid'}</span></td>
        <td><strong>${Math.round(r.risk_probability * 100)}%</strong></td>
        <td><span class="tier-badge ${getTierBadgeClass(r.risk_tier)}">${r.risk_tier}</span></td>
        <td><span style="font-size:0.775rem; font-weight:600; color:${r.block_cod ? 'var(--danger-red)' : 'var(--safe-green)'};">${r.recommendation}</span></td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Audit log error:", err);
  }
}

async function fetchModelInfo() {
  try {
    const res = await fetch("/api/model-info");
    const info = await res.json();

    const statusPill = document.getElementById("model-status-text");
    if (statusPill && info.model_loaded) {
      statusPill.innerText = `Model Active (ROC-AUC: ${info.roc_auc} | Cutoff: ${Math.round(info.optimal_threshold * 100)}%)`;
    }
    const kpiAuc = document.getElementById("kpi-auc");
    if (kpiAuc && info.roc_auc) {
      kpiAuc.innerText = info.roc_auc;
    }
  } catch (err) {
    console.error("Model info fetch error:", err);
  }
}
