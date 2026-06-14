// Verbindet sich mit dem Backend und zeigt erkannte Ziffern live an.

const statusEl = document.getElementById("status");
const statusText = document.getElementById("status-text");
const latestEl = document.getElementById("latest");
const sequenceEl = document.getElementById("sequence");
const clearBtn = document.getElementById("clear");

let sequence = "";

clearBtn.addEventListener("click", () => {
  sequence = "";
  sequenceEl.textContent = "";
  latestEl.textContent = "";
});

function showDigit(digit) {
  latestEl.textContent = digit;
  latestEl.classList.remove("rejected");
  latestEl.classList.add("pulse");
  setTimeout(() => latestEl.classList.remove("pulse"), 130);
  sequence += digit;
  sequenceEl.textContent = sequence;
}

function showRejected() {
  latestEl.textContent = "?";
  latestEl.classList.add("rejected");
  setTimeout(() => {
    latestEl.classList.remove("rejected");
    latestEl.textContent = "";
  }, 600);
}

function connect() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${proto}://${location.host}/ws/display`);

  ws.onopen = () => {
    statusEl.classList.add("connected");
    statusText.textContent = "verbunden";
  };

  ws.onclose = () => {
    statusEl.classList.remove("connected");
    statusText.textContent = "getrennt – neuer Versuch…";
    setTimeout(connect, 1500); // automatisch neu verbinden
  };

  ws.onmessage = (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }

    switch (msg.type) {
      case "status":
        statusText.textContent = msg.model_loaded
          ? "verbunden – Modell aktiv"
          : "verbunden – DEBUG (kein Modell, nur Segmentierung)";
        break;
      case "digit":
        showDigit(msg.digit);
        break;
      case "rejected":
        showRejected();
        break;
      case "segment": // DEBUG-Modus: nur Segment erkannt
        latestEl.textContent = "•";
        latestEl.classList.add("pulse");
        setTimeout(() => {
          latestEl.classList.remove("pulse");
          latestEl.textContent = "";
        }, 200);
        break;
    }
  };
}

connect();
