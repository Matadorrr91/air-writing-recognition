"""End-to-End-Smoke-Test der gesamten Python-Kette mit synthetischen Daten.

Verifiziert OHNE Hardware:
  1. Synthetische, trennbare Ziffern-Segmente erzeugen + speichern
  2. Training (train.py) laeuft durch und speichert Modell + Norm-Statistik
  3. Direkte Inferenz erreicht hohe Accuracy auf frischen synthetischen Daten
  4. Der FastAPI-Server erkennt einen gestreamten "geschriebenen" Ziffernverlauf
     und schiebt das Ergebnis an die Display-WebSocket

Alle Pfade zeigen auf ein temporaeres Verzeichnis -> es bleiben KEINE
Artefakte (kein Modell, keine Datensaetze) im Projekt zurueck.

Aufruf (mit venv-Python):
    .venv\\Scripts\\python.exe tests\\smoke_e2e.py
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# --- Pfade ISOLIEREN, bevor Module mit eingefrorenen Default-Args importiert werden ---
from backend import config  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="airwriting_smoke_"))
config.DATASET_DIR = TMP / "dataset"
config.MODELS_DIR = TMP / "models"
config.MODEL_PATH = config.MODELS_DIR / "model.pt"
config.NORM_STATS_PATH = config.MODELS_DIR / "norm_stats.npz"

# Erst JETZT importieren (Default-Args binden die obigen temporaeren Pfade)
from backend import data, preprocessing, train  # noqa: E402
from backend.model import load_model  # noqa: E402

FS = config.SAMPLE_RATE_HZ


def synth_segment(digit: int, rng: np.random.Generator) -> np.ndarray:
    """Klassenabhaengiges, trennbares Schreib-Segment (N, 6)."""
    n = int(rng.integers(40, 66))
    t = np.arange(n) / FS
    f = 2.0 + 0.7 * digit
    ph = 0.3 * digit
    A, B = 0.2, 0.4
    seg = np.empty((n, 6), dtype=np.float32)
    seg[:, 0] = A * np.sin(2 * np.pi * f * t)
    seg[:, 1] = A * np.sin(2 * np.pi * f * t + ph)
    seg[:, 2] = 0.5 * A * np.sin(2 * np.pi * 2 * f * t)
    seg[:, 3] = B * np.cos(2 * np.pi * f * t)
    seg[:, 4] = B * np.sin(2 * np.pi * f * t + 1.0)
    seg[:, 5] = 0.5 * B * np.cos(2 * np.pi * 1.5 * f * t)
    seg += rng.normal(0, 0.01, seg.shape).astype(np.float32)
    return seg


def synth_recording(digit: int, rng: np.random.Generator) -> list[dict]:
    """Voller Verlauf idle -> schreiben -> Pause, Sample fuer Sample (fuer Server)."""
    samples: list[dict] = []
    t = 0.0
    dt = 1.0 / FS

    def add_idle(dur):
        nonlocal t
        for _ in range(int(dur * FS)):
            samples.append({"t": t, "ax": 0.002, "ay": 0.0, "az": 0.0, "gx": 0.0, "gy": 0.0, "gz": 0.0})
            t += dt

    add_idle(0.3)
    seg = synth_segment(digit, rng)
    for row in seg:
        samples.append({"t": t, "ax": float(row[0]), "ay": float(row[1]), "az": float(row[2]),
                        "gx": float(row[3]), "gy": float(row[4]), "gz": float(row[5])})
        t += dt
    add_idle(0.6)   # Pause beendet das Segment
    return samples


def step1_generate():
    rng = np.random.default_rng(0)
    per_class = 40
    for d in range(config.NUM_CLASSES):
        for i in range(per_class):
            data.save_segment(synth_segment(d, rng), label=d, person="synth", index=i)
    samples = data.load_all()
    assert len(samples) == per_class * config.NUM_CLASSES
    print(f"[1/4] Synthetische Daten: {len(samples)} Segmente erzeugt.")


def step2_train():
    args = SimpleNamespace(epochs=20, patience=8, augment_factor=3,
                           test_person=None, random_split=True, seed=0)
    train.train(args)
    assert config.MODEL_PATH.exists(), "model.pt wurde nicht gespeichert"
    assert config.NORM_STATS_PATH.exists(), "norm_stats.npz wurde nicht gespeichert"
    print("[2/4] Training abgeschlossen, Modell gespeichert.")


def step3_inference_accuracy():
    import torch
    import torch.nn.functional as F
    model = load_model(config.MODEL_PATH)
    mean, std = preprocessing.load_norm_stats()
    rng = np.random.default_rng(999)   # frische, ungesehene Daten
    correct = 0
    total = 0
    for d in range(config.NUM_CLASSES):
        for _ in range(20):
            seg = synth_segment(d, rng)
            x = preprocessing.preprocess(seg, mean, std).T
            with torch.no_grad():
                pred = int(F.softmax(model(torch.tensor(x[None], dtype=torch.float32)), 1).argmax())
            correct += int(pred == d)
            total += 1
    acc = correct / total
    print(f"[3/4] Inferenz-Accuracy auf frischen Daten: {acc:.3f}")
    assert acc > 0.7, f"Accuracy zu niedrig ({acc:.3f}) - Pipeline pruefen"


def step4_server_end_to_end():
    from fastapi.testclient import TestClient
    from backend import server   # importiert NACH dem Training -> laedt das Modell
    assert server.MODEL is not None, "Server laeuft im DEBUG-Modus (Modell nicht geladen)"

    client = TestClient(server.app)
    rng = np.random.default_rng(7)
    with client.websocket_connect("/ws/display") as disp:
        status = disp.receive_json()
        assert status["type"] == "status" and status["model_loaded"] is True
        with client.websocket_connect("/ws/watch") as watch:
            for sample in synth_recording(digit=5, rng=rng):
                watch.send_text(json.dumps(sample))
            msg = disp.receive_json()
    assert msg["type"] in ("digit", "rejected"), msg
    print(f"[4/4] Server-End-to-End: Display empfing -> {msg}")


def main():
    try:
        step1_generate()
        step2_train()
        step3_inference_accuracy()
        step4_server_end_to_end()
        print("\nSMOKE-TEST BESTANDEN: komplette Python-Kette funktioniert.")
    finally:
        shutil.rmtree(TMP, ignore_errors=True)
        print(f"(temporaere Dateien entfernt: {TMP})")


if __name__ == "__main__":
    main()
