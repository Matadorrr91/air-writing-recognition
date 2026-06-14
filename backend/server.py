"""Live-Server: empfaengt den Sensorstrom der Watch, segmentiert, erkennt die
Ziffer mit dem 1D-CNN und schiebt das Ergebnis an die Browser-Anzeige.

Aufruf:
    python -m backend.server
Dann im Browser:  http://localhost:8000

Endpunkte:
    GET  /            -> Frontend (frontend/index.html)
    WS   /ws/watch    -> Sensordaten von der Watch (JSON-Samples)
    WS   /ws/display  -> erkannte Ziffern an den Browser

Ohne trainiertes Modell (models/model.pt) laeuft der Server im DEBUG-Modus:
Segmente werden nur erkannt und gemeldet, aber nicht klassifiziert.
"""

import json

import torch
import torch.nn.functional as F
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config, preprocessing
from .model import load_model
from .segmentation import Segmenter

app = FastAPI(title="Air-Writing Ziffernerkennung")

# --- Modell laden (optional) ---------------------------------------------
MODEL = None
MEAN = STD = None
if config.MODEL_PATH.exists() and config.NORM_STATS_PATH.exists():
    MODEL = load_model(config.MODEL_PATH)
    MEAN, STD = preprocessing.load_norm_stats()
    print(f"[server] Modell geladen: {config.MODEL_PATH}")
else:
    print("[server] Kein Modell gefunden -> DEBUG-Modus (nur Segmentierung).")


# --- Verbundene Browser-Anzeigen -----------------------------------------
class DisplayHub:
    def __init__(self):
        self.clients: set[WebSocket] = set()

    async def add(self, ws: WebSocket):
        await ws.accept()
        self.clients.add(ws)

    def remove(self, ws: WebSocket):
        self.clients.discard(ws)

    async def broadcast(self, message: dict):
        dead = []
        for ws in self.clients:
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.remove(ws)


hub = DisplayHub()


def classify(seg) -> dict:
    """Ein Segment klassifizieren. Gibt die Nachricht fuer das Frontend zurueck."""
    if MODEL is None:
        return {"type": "segment", "samples": int(len(seg))}
    x = preprocessing.preprocess(seg, MEAN, STD).T   # (C, T)
    tensor = torch.tensor(x[None], dtype=torch.float32)
    with torch.no_grad():
        probs = F.softmax(MODEL(tensor), dim=1)[0]
    conf, pred = torch.max(probs, dim=0)
    conf, pred = float(conf), int(pred)
    if conf < config.CONFIDENCE_THRESHOLD:
        return {"type": "rejected", "digit": pred, "confidence": round(conf, 3)}
    return {"type": "digit", "digit": pred, "confidence": round(conf, 3)}


@app.websocket("/ws/watch")
async def ws_watch(ws: WebSocket):
    """Sensordaten von der Watch: ein JSON-Sample pro Nachricht."""
    await ws.accept()
    seg = Segmenter()
    print("[server] Watch verbunden.")
    try:
        while True:
            raw = await ws.receive_text()
            try:
                sample = json.loads(raw)
            except json.JSONDecodeError:
                continue
            result = seg.push(sample)
            if result is not None:
                msg = classify(result)
                print(f"[server] Segment ({len(result)} Samples) -> {msg}")
                await hub.broadcast(msg)
    except WebSocketDisconnect:
        print("[server] Watch getrennt.")


@app.websocket("/ws/display")
async def ws_display(ws: WebSocket):
    """Browser-Anzeige: empfaengt erkannte Ziffern."""
    await hub.add(ws)
    await ws.send_text(json.dumps({"type": "status", "model_loaded": MODEL is not None}))
    try:
        while True:
            await ws.receive_text()   # Frontend sendet nichts Relevantes
    except WebSocketDisconnect:
        hub.remove(ws)


@app.get("/health")
async def health():
    return JSONResponse({"model_loaded": MODEL is not None})


# Frontend statisch ausliefern (zuletzt mounten, damit /ws/* Vorrang hat)
app.mount("/", StaticFiles(directory=str(config.FRONTEND_DIR), html=True), name="frontend")


def main():
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)


if __name__ == "__main__":
    main()
