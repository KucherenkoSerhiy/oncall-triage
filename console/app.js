"use strict";

const TOKEN_KEY = "triage.token";
const API_BASE_KEY = "triage.apiBase";
const POLL_INTERVAL_MS = 10000;
const ACTIONS = ["page", "monitor", "ack"];

// Visitors without a token see the last run the pipeline recorded (#131):
// the smoke probe and estate-demo publish this file next to the console.
const SNAPSHOT_URL = "demo/snapshot.json";
let readOnly = false;

// Labels the reporter uses (current format first, then the wording older
// verdicts were written with), mapped to the heading the console shows.
const SECTION_LABELS = [
  [/^error( text)?$/i, "Error"],
  [/^researcher characteri[sz]ation$/i, "Characterization"],
  [/^cause( category)?$/i, "Cause"],
  [/^severity( guess)?$/i, "Severity"],
  [/^next( diagnostic)? step$/i, "Next step"],
  [/^recommendation$/i, "Recommendation"],
];

function resolveApiBase() {
  const params = new URLSearchParams(location.search);
  const fromQuery = params.get("api");
  if (fromQuery) {
    localStorage.setItem(API_BASE_KEY, fromQuery);
    return fromQuery;
  }

  const isLocal =
    location.hostname === "" || location.hostname === "localhost" || location.hostname === "127.0.0.1";
  if (!isLocal) {
    return `https://api.${location.hostname}`;
  }

  return localStorage.getItem(API_BASE_KEY) || "";
}

const API_BASE = resolveApiBase();

function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

function setToken(value) {
  localStorage.setItem(TOKEN_KEY, value);
}

function setStatus(text) {
  document.getElementById("status").textContent = text;
}

async function apiFetch(path, options = {}) {
  const headers = { ...(options.headers || {}), Authorization: `Bearer ${getToken()}` };
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`HTTP ${response.status}: ${body}`);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

function formatTime(isoString) {
  const date = new Date(isoString);
  return Number.isNaN(date.getTime()) ? isoString : date.toLocaleTimeString();
}

// --- report text -> sections -------------------------------------------------

// Same rules as services/triage_worker/runner.clean_report, so verdicts
// written before that fix render the same way as new ones (#126, #127).
function cleanReport(text) {
  let body = (text || "").trim().replace(/```verdict\s*\n[\s\S]*?\n```\s*$/, "").trim();
  const head = body.slice(0, 600);
  if (/^(?:I(?:'m| am| have|'ve| will| received)\b|As the reporter\b|Here is\b)/i.test(head)) {
    const rule = /(?:^|\s)---(?:\s|$)/.exec(head);
    const label = head.indexOf("**");
    if (rule) {
      body = body.slice(rule.index + rule[0].length);
    } else if (label > 0) {
      body = body.slice(label);
    }
  }
  return body.trim();
}

function headingFor(rawLabel) {
  const label = rawLabel.trim();
  for (const [pattern, heading] of SECTION_LABELS) {
    if (pattern.test(label)) {
      return heading;
    }
  }
  return label;
}

function tidy(value) {
  return value
    .replace(/^[\s\-–—:]+/, "")
    .replace(/\s+-\s+$/, "")
    .replace(/\s*\n\s*-\s+/g, "\n")
    .trim();
}

// "**Label:** value **Label:** value" (inline or one per line) -> [[heading, value], ...].
// Returns [] when the text carries no labels, so the caller falls back to plain text.
function parseSections(text) {
  const marker = /\*\*([^*\n]{1,40}?):?\*\*:?/g;
  const sections = [];
  let match;
  let last = null;
  while ((match = marker.exec(text)) !== null) {
    if (last) {
      sections.push([last.heading, tidy(text.slice(last.end, match.index))]);
    }
    last = { heading: headingFor(match[1]), end: marker.lastIndex };
  }
  if (last) {
    sections.push([last.heading, tidy(text.slice(last.end))]);
  }
  return sections.filter(([, value]) => value.length > 0);
}

// --- rendering ------------------------------------------------------------

const expanded = new Set();
let lastAlerts = [];

function actionOf(alert) {
  if (!alert.verdict) {
    return "pending";
  }
  return ACTIONS.includes(alert.verdict.action) ? alert.verdict.action : "monitor";
}

function renderTiles(alerts) {
  const counts = { page: 0, monitor: 0, ack: 0, pending: 0 };
  for (const alert of alerts) {
    counts[actionOf(alert)] += 1;
  }
  for (const [action, count] of Object.entries(counts)) {
    document.querySelector(`[data-count="${action}"]`).textContent = String(count);
  }
}

function renderSections(body, alert) {
  const list = body.querySelector(".sections");
  const plain = body.querySelector(".plain-report");
  const meta = body.querySelector(".alert-meta");
  list.innerHTML = "";
  plain.hidden = true;
  plain.textContent = "";

  const metaBits = [`source ${alert.source || "?"}`, `alert ${alert.alert_id}`];
  if (alert.verdict) {
    metaBits.push(`model ${alert.verdict.model}`);
    if (alert.verdict.created_at) {
      metaBits.push(`triaged ${formatTime(alert.verdict.created_at)}`);
    }
    if (alert.verdict.known) {
      metaBits.push("matched a known issue");
    }
  }
  meta.textContent = metaBits.join(" · ");

  if (!alert.verdict) {
    plain.hidden = false;
    plain.textContent = "Waiting for the triage worker.";
    return;
  }

  const text = cleanReport(alert.verdict.text);
  const sections = parseSections(text);
  if (sections.length === 0) {
    plain.hidden = false;
    plain.textContent = text || alert.verdict.summary || "";
    return;
  }
  for (const [heading, value] of sections) {
    const dt = document.createElement("dt");
    dt.textContent = heading;
    const dd = document.createElement("dd");
    dd.textContent = value;
    list.append(dt, dd);
  }
}

function buildTeachForm(alert, onDone) {
  const template = document.getElementById("teach-form-template");
  const form = template.content.firstElementChild.cloneNode(true);
  form.elements.service.value = alert.service;
  form.elements.pattern.value = alert.title || "";
  form.querySelector(".teach-cancel").addEventListener("click", onDone);
  form.addEventListener("submit", (event) => onTeachSubmit(event, onDone));
  return form;
}

async function onTeachSubmit(event, onDone) {
  event.preventDefault();
  const form = event.currentTarget;
  const service = form.elements.service.value.trim();
  const pattern = form.elements.pattern.value.trim();
  const explanation = form.elements.explanation.value.trim();
  if (!service || !pattern || !explanation) {
    return;
  }

  try {
    await apiFetch("/known-issues", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ service, pattern, explanation }),
    });
    onDone();
    await refreshKnownIssues();
    setStatus(`taught known issue for ${service}`);
  } catch (err) {
    setStatus(`error teaching known issue: ${err.message}`);
  }
}

function setExpanded(row, alert, isExpanded) {
  const head = row.querySelector(".alert-head");
  const body = row.querySelector(".alert-body");
  head.setAttribute("aria-expanded", String(isExpanded));
  body.hidden = !isExpanded;
  row.classList.toggle("expanded", isExpanded);
  if (isExpanded) {
    expanded.add(alert.alert_id);
  } else {
    expanded.delete(alert.alert_id);
  }
}

function renderAlert(alert) {
  const template = document.getElementById("alert-row-template");
  const row = template.content.firstElementChild.cloneNode(true);
  const action = actionOf(alert);
  row.dataset.action = action;

  row.querySelector(".col-time").textContent = formatTime(alert.received_at);
  const chip = row.querySelector(".col-severity");
  chip.textContent = alert.severity;
  chip.classList.add(`chip-${alert.severity}`);
  row.querySelector(".col-service").textContent = alert.service;
  const name = row.querySelector(".col-name");
  name.textContent = alert.alert_name;
  name.title = alert.alert_name;
  const occurrences = row.querySelector(".col-occurrences");
  const count = alert.occurrences ?? 0;
  occurrences.textContent = count > 1 ? `×${count}` : "";
  const badge = row.querySelector(".col-action");
  badge.textContent = action;
  badge.classList.add(`badge-${action}`);
  const summary = row.querySelector(".col-summary");
  summary.textContent = alert.verdict
    ? alert.verdict.summary || ""
    : alert.status === "queued"
      ? "queued for triage"
      : alert.status;

  const body = row.querySelector(".alert-body");
  renderSections(body, alert);

  const teach = body.querySelector(".teach");
  teach.hidden = readOnly;
  const toggle = teach.querySelector(".teach-toggle");
  toggle.addEventListener("click", () => {
    toggle.hidden = true;
    const form = buildTeachForm(alert, () => {
      form.remove();
      toggle.hidden = false;
    });
    teach.appendChild(form);
    form.elements.explanation.focus();
  });

  const head = row.querySelector(".alert-head");
  head.setAttribute("aria-label", `${action} - ${alert.service} ${alert.alert_name}: show details`);
  head.addEventListener("click", () => {
    setExpanded(row, alert, !expanded.has(alert.alert_id));
  });
  setExpanded(row, alert, expanded.has(alert.alert_id));
  return row;
}

function renderAlerts(alerts) {
  lastAlerts = alerts;
  const list = document.getElementById("alerts-list");
  const empty = document.getElementById("alerts-empty");
  empty.hidden = alerts.length > 0;
  renderTiles(alerts);

  // Keep an open teach form alive across the poll: skip the re-render while
  // any teach form is on screen.
  if (list.querySelector(".teach-form")) {
    return;
  }
  list.innerHTML = "";
  for (const alert of alerts) {
    list.appendChild(renderAlert(alert));
  }
}

function setAllExpanded(isExpanded) {
  for (const alert of lastAlerts) {
    if (isExpanded) {
      expanded.add(alert.alert_id);
    } else {
      expanded.delete(alert.alert_id);
    }
  }
  renderAlerts(lastAlerts);
}

function renderKnownIssues(issues) {
  const list = document.getElementById("known-issues-list");
  const empty = document.getElementById("known-issues-empty");
  list.innerHTML = "";
  empty.hidden = issues.length > 0;

  const byService = new Map();
  for (const issue of issues) {
    if (!byService.has(issue.service)) {
      byService.set(issue.service, []);
    }
    byService.get(issue.service).push(issue);
  }

  const template = document.getElementById("known-issue-template");
  for (const [service, serviceIssues] of byService) {
    const heading = document.createElement("h3");
    heading.textContent = service;
    list.appendChild(heading);

    const grid = document.createElement("div");
    grid.className = "known-grid";
    for (const issue of serviceIssues) {
      const article = template.content.firstElementChild.cloneNode(true);
      article.querySelector(".pattern").textContent = issue.pattern;
      article.querySelector(".explanation").textContent = issue.explanation;
      const deleteButton = article.querySelector(".delete-known-issue");
      deleteButton.hidden = readOnly;
      deleteButton.addEventListener("click", () => onDeleteKnownIssue(issue.service, issue.issue_id));
      grid.appendChild(article);
    }
    list.appendChild(grid);
  }
}

async function onDeleteKnownIssue(service, issueId) {
  try {
    await apiFetch(`/known-issues/${encodeURIComponent(service)}/${encodeURIComponent(issueId)}`, {
      method: "DELETE",
    });
    await refreshKnownIssues();
  } catch (err) {
    setStatus(`error deleting known issue: ${err.message}`);
  }
}

async function refreshAlerts() {
  try {
    const alerts = await apiFetch("/alerts?limit=50");
    renderAlerts(alerts);
    setStatus(`ok - ${alerts.length} alert(s)`);
  } catch (err) {
    setStatus(`error: ${err.message}`);
  }
}

async function refreshKnownIssues() {
  try {
    const issues = await apiFetch("/known-issues");
    renderKnownIssues(issues);
  } catch (err) {
    setStatus(`error: ${err.message}`);
  }
}

async function loadSnapshot() {
  try {
    const response = await fetch(SNAPSHOT_URL, { cache: "no-cache" });
    if (!response.ok) {
      return null;
    }
    return await response.json();
  } catch (_err) {
    return null;
  }
}

function showSnapshot(snapshot) {
  readOnly = true;
  document.body.classList.add("read-only");
  const banner = document.getElementById("snapshot-banner");
  const recorded = new Date(snapshot.recorded_at);
  banner.querySelector(".snapshot-time").textContent = Number.isNaN(recorded.getTime())
    ? snapshot.recorded_at
    : recorded.toLocaleString();
  const run = banner.querySelector(".snapshot-run");
  if (snapshot.run_url) {
    run.href = snapshot.run_url;
  } else {
    run.hidden = true;
  }
  banner.hidden = false;
  const alerts = snapshot.alerts || [];
  renderAlerts(alerts);
  renderKnownIssues(snapshot.known_issues || []);
  setStatus(`recorded run - ${alerts.length} alert(s), read-only`);
}

function leaveSnapshot() {
  readOnly = false;
  document.body.classList.remove("read-only");
  document.getElementById("snapshot-banner").hidden = true;
}

function promptForToken() {
  const dialog = document.getElementById("token-dialog");
  document.getElementById("token-input").value = "";
  document.getElementById("token-cancel").hidden = !readOnly;
  if (!getToken() && !readOnly) {
    setStatus("no token - read-only visitor");
  }
  dialog.showModal();
}

let pollIntervalIds = [];

function initTokenDialog() {
  const dialog = document.getElementById("token-dialog");
  const form = document.getElementById("token-form");
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    setToken(document.getElementById("token-input").value.trim());
    dialog.close();
    leaveSnapshot();
    setStatus("connecting\u2026");
    startPolling();
  });
  document.getElementById("change-token").addEventListener("click", promptForToken);
  document.getElementById("snapshot-token").addEventListener("click", promptForToken);
  document.getElementById("token-cancel").addEventListener("click", () => dialog.close());
}

function startPolling() {
  for (const id of pollIntervalIds) {
    clearInterval(id);
  }
  refreshAlerts();
  refreshKnownIssues();
  pollIntervalIds = [
    setInterval(refreshAlerts, POLL_INTERVAL_MS),
    setInterval(refreshKnownIssues, POLL_INTERVAL_MS),
  ];
}

async function main() {
  initTokenDialog();
  document.getElementById("expand-all").addEventListener("click", () => setAllExpanded(true));
  document.getElementById("collapse-all").addEventListener("click", () => setAllExpanded(false));
  if (getToken()) {
    startPolling();
    return;
  }
  const snapshot = await loadSnapshot();
  if (snapshot) {
    showSnapshot(snapshot);
  } else {
    promptForToken();
  }
}

main();
