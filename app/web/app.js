const liveLog = document.getElementById("live-log");
const mealsLog = document.getElementById("meals-log");
const statsLog = document.getElementById("stats-log");

let sessionId = null;
let ws = null;

function appendLog(target, payload) {
  target.textContent += `${typeof payload === "string" ? payload : JSON.stringify(payload)}\n`;
  target.scrollTop = target.scrollHeight;
}

async function createSession() {
  const response = await fetch("/v1/live/session", { method: "POST" });
  const data = await response.json();
  sessionId = data.session_id;
  appendLog(liveLog, { event: "session_created", sessionId });
}

function connectWs() {
  if (!sessionId) {
    appendLog(liveLog, "Create session first");
    return;
  }
  ws = new WebSocket(`${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/v1/live/ws/${sessionId}`);
  ws.onmessage = (event) => {
    appendLog(liveLog, JSON.parse(event.data));
  };
  ws.onopen = () => appendLog(liveLog, "ws_connected");
  ws.onclose = () => appendLog(liveLog, "ws_closed");
}

function sendWs(payload) {
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    appendLog(liveLog, "WS is not connected");
    return;
  }
  ws.send(JSON.stringify(payload));
}

async function saveMeal(event) {
  event.preventDefault();
  const nowIso = new Date().toISOString();
  const payload = {
    name: document.getElementById("meal-name").value,
    calories: Number(document.getElementById("meal-calories").value),
    protein: Number(document.getElementById("meal-protein").value),
    carbs: Number(document.getElementById("meal-carbs").value),
    fat: Number(document.getElementById("meal-fat").value),
    fiber: Number(document.getElementById("meal-fiber").value),
    timestamp: nowIso,
    type: document.getElementById("meal-type").value
  };

  const response = await fetch("/v1/meals", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  const data = await response.json();
  appendLog(mealsLog, { saved: data.id, name: data.name });
}

async function loadMeals() {
  const response = await fetch("/v1/meals");
  const items = await response.json();
  mealsLog.textContent = `${JSON.stringify(items, null, 2)}\n`;
}

async function calculateStats() {
  const response = await fetch("/v1/meals");
  const meals = await response.json();
  const statsResponse = await fetch("/v1/nutrition/daily-stats", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(meals)
  });
  const stats = await statsResponse.json();
  statsLog.textContent = `${JSON.stringify(stats, null, 2)}\n`;
}

document.getElementById("create-session").addEventListener("click", createSession);
document.getElementById("connect-ws").addEventListener("click", connectWs);
document.getElementById("send-start").addEventListener("click", () => sendWs({ type: "start" }));
document.getElementById("send-stop").addEventListener("click", () => sendWs({ type: "stop" }));
document.getElementById("send-text").addEventListener("click", () =>
  sendWs({ type: "text", text: document.getElementById("chat-text").value })
);
document.getElementById("meal-form").addEventListener("submit", saveMeal);
document.getElementById("refresh-meals").addEventListener("click", loadMeals);
document.getElementById("calculate-stats").addEventListener("click", calculateStats);
