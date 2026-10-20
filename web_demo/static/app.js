const elements = {
  input: document.querySelector("#json-input"),
  loadSample: document.querySelector("#load-sample"),
  formatJson: document.querySelector("#format-json"),
  run: document.querySelector("#run-inference"),
  refreshStatus: document.querySelector("#refresh-status"),
  endpointStatus: document.querySelector("#endpoint-status"),
  statusDot: document.querySelector("#status-dot"),
  message: document.querySelector("#request-message"),
  empty: document.querySelector("#empty-state"),
  results: document.querySelector("#results"),
  chip: document.querySelector("#risk-chip"),
  score: document.querySelector("#risk-score"),
  threshold: document.querySelector("#risk-threshold"),
  scoreFill: document.querySelector("#score-fill"),
  thresholdMarker: document.querySelector("#threshold-marker"),
  predictedClass: document.querySelector("#predicted-class"),
  priorityFlag: document.querySelector("#priority-flag"),
  modelVersion: document.querySelector("#model-version"),
  latency: document.querySelector("#latency"),
  businessPanel: document.querySelector("#business-panel"),
  businessHeadline: document.querySelector("#business-headline"),
  businessSummary: document.querySelector("#business-summary"),
  queueName: document.querySelector("#queue-name"),
  actionGrid: document.querySelector("#action-grid"),
  summaryOrder: document.querySelector("#summary-order"),
  summaryDelay: document.querySelector("#summary-delay"),
  summaryCategory: document.querySelector("#summary-category"),
  summaryRoute: document.querySelector("#summary-route"),
  summaryValue: document.querySelector("#summary-value"),
};

function showError(title, detail) {
  elements.message.textContent = detail ? `${title}: ${detail}` : title;
  elements.message.hidden = false;
}

function clearError() {
  elements.message.hidden = true;
  elements.message.textContent = "";
}

async function loadSample() {
  clearError();
  try {
    const response = await fetch("/api/sample");
    if (!response.ok) throw new Error("Could not load the verified sample request.");
    const payload = await response.json();
    elements.input.value = JSON.stringify(payload, null, 2);
  } catch (error) {
    showError("Sample unavailable", error.message);
  }
}

function formatJson() {
  clearError();
  try {
    elements.input.value = JSON.stringify(JSON.parse(elements.input.value), null, 2);
  } catch (error) {
    showError("Invalid JSON", error.message);
  }
}

async function refreshEndpointStatus() {
  elements.endpointStatus.textContent = "Checking…";
  elements.statusDot.className = "status-dot";
  try {
    const response = await fetch("/api/endpoint-status");
    const data = await response.json();
    elements.endpointStatus.textContent = data.status;
    elements.statusDot.classList.add(data.status === "InService" ? "online" : "offline");
    elements.endpointStatus.title = data.detail || `${data.endpoint_name} · ${data.region}`;
  } catch (error) {
    elements.endpointStatus.textContent = "Unavailable";
    elements.endpointStatus.title = error.message;
    elements.statusDot.classList.add("offline");
  }
}

function renderActions(actions) {
  elements.actionGrid.replaceChildren(
    ...actions.map((action) => {
      const article = document.createElement("article");
      article.className = "action-card";
      const step = document.createElement("span");
      step.textContent = action.step;
      const title = document.createElement("h3");
      title.textContent = action.title;
      const detail = document.createElement("p");
      detail.textContent = action.detail;
      article.append(step, title, detail);
      return article;
    }),
  );
}

function renderResult(data) {
  const prediction = data.prediction;
  const decision = data.business_decision;
  const summary = data.request_summary;
  const high = prediction.priority_review_flag;

  elements.empty.hidden = true;
  elements.results.hidden = false;
  elements.chip.textContent = `${decision.risk_band} RISK`;
  elements.chip.className = `risk-chip ${high ? "high" : "standard"}`;
  elements.score.textContent = prediction.risk_score.toFixed(4);
  elements.threshold.textContent = prediction.risk_threshold.toFixed(4);
  elements.scoreFill.style.width = `${Math.min(100, Math.max(0, prediction.risk_score * 100))}%`;
  elements.thresholdMarker.style.left = `${Math.min(100, Math.max(0, prediction.risk_threshold * 100))}%`;
  elements.predictedClass.textContent = `${prediction.predicted_class} · ${high ? "High risk" : "Standard risk"}`;
  elements.priorityFlag.textContent = high ? "TRUE" : "FALSE";
  elements.modelVersion.textContent = prediction.model_version;
  elements.latency.textContent = `${data.runtime.latency_ms} ms`;

  elements.businessPanel.classList.remove("high-risk", "standard-risk");
  elements.businessPanel.classList.add(high ? "high-risk" : "standard-risk");
  elements.businessHeadline.textContent = decision.headline;
  elements.businessSummary.textContent = decision.summary;
  elements.queueName.textContent = decision.queue;
  renderActions(decision.actions);

  elements.summaryOrder.textContent = summary.order_id;
  elements.summaryDelay.textContent = `${summary.delay_days.toFixed(1)} days`;
  elements.summaryCategory.textContent = summary.category.replaceAll("_", " ");
  elements.summaryRoute.textContent = `${summary.seller_state} → ${summary.customer_state}`;
  elements.summaryValue.textContent = `R$ ${summary.order_value.toFixed(2)}`;
}

async function runInference() {
  clearError();
  let payload;
  try {
    payload = JSON.parse(elements.input.value);
  } catch (error) {
    showError("Invalid JSON", error.message);
    return;
  }

  const original = elements.run.innerHTML;
  elements.run.disabled = true;
  elements.run.textContent = "Invoking SageMaker…";
  try {
    const response = await fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(`${data.error || "Request failed"}: ${data.detail || "Unknown error"}`);
    renderResult(data);
  } catch (error) {
    showError("Live inference failed", error.message);
  } finally {
    elements.run.disabled = false;
    elements.run.innerHTML = original;
    refreshEndpointStatus();
  }
}

elements.loadSample.addEventListener("click", loadSample);
elements.formatJson.addEventListener("click", formatJson);
elements.run.addEventListener("click", runInference);
elements.refreshStatus.addEventListener("click", refreshEndpointStatus);
loadSample();
refreshEndpointStatus();
window.setInterval(refreshEndpointStatus, 30000);
