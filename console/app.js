"use strict";

const TOKEN_KEY = "triage.token";
const API_BASE_KEY = "triage.apiBase";
const POLL_INTERVAL_MS = 10000;

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

function buildTeachForm(service) {
  const template = document.getElementById("teach-form-template");
  const form = template.content.firstElementChild.cloneNode(true);
  form.elements.service.value = service;
  form.addEventListener("submit", onTeachSubmit);
  return form;
}

async function onTeachSubmit(event) {
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
    form.reset();
    form.elements.service.value = service;
    await refreshKnownIssues();
    setStatus(`taught known issue for ${service}`);
  } catch (err) {
    setStatus(`error teaching known issue: ${err.message}`);
  }
}

function renderAlerts(alerts) {
  const body = document.getElementById("alerts-body");
  const empty = document.getElementById("alerts-empty");
  body.innerHTML = "";
  empty.hidden = alerts.length > 0;

  for (const alert of alerts) {
    const row = document.createElement("tr");

    const timeCell = document.createElement("td");
    timeCell.textContent = formatTime(alert.received_at);
    row.appendChild(timeCell);

    const severityCell = document.createElement("td");
    const chip = document.createElement("span");
    chip.className = `chip chip-${alert.severity}`;
    chip.textContent = alert.severity;
    severityCell.appendChild(chip);
    row.appendChild(severityCell);

    const serviceCell = document.createElement("td");
    serviceCell.textContent = alert.service;
    row.appendChild(serviceCell);

    const nameCell = document.createElement("td");
    nameCell.textContent = alert.alert_name;
    row.appendChild(nameCell);

    const statusCell = document.createElement("td");
    statusCell.textContent = alert.status;
    row.appendChild(statusCell);

    const occurrencesCell = document.createElement("td");
    occurrencesCell.textContent = alert.occurrences ?? 0;
    row.appendChild(occurrencesCell);

    const verdictCell = document.createElement("td");
    if (alert.verdict) {
      const action = document.createElement("strong");
      action.textContent = alert.verdict.action;
      verdictCell.appendChild(action);
      verdictCell.appendChild(document.createElement("br"));
      verdictCell.appendChild(document.createTextNode(alert.verdict.text));
    } else {
      verdictCell.textContent = "pending";
    }
    row.appendChild(verdictCell);

    const teachCell = document.createElement("td");
    teachCell.appendChild(buildTeachForm(alert.service));
    row.appendChild(teachCell);

    body.appendChild(row);
  }
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

    for (const issue of serviceIssues) {
      const article = template.content.firstElementChild.cloneNode(true);
      article.querySelector(".pattern").textContent = issue.pattern;
      article.querySelector(".explanation").textContent = issue.explanation;
      const deleteButton = article.querySelector(".delete-known-issue");
      deleteButton.addEventListener("click", () => onDeleteKnownIssue(issue.service, issue.issue_id));
      list.appendChild(article);
    }
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

function promptForToken() {
  const dialog = document.getElementById("token-dialog");
  document.getElementById("token-input").value = "";
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
    startPolling();
  });
  document.getElementById("change-token").addEventListener("click", promptForToken);
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

function main() {
  initTokenDialog();
  if (!getToken()) {
    promptForToken();
  } else {
    startPolling();
  }
}

main();
