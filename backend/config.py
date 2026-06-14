"""Zentrale Konstanten fuer die gesamte Pipeline.

Alle Module (Segmentierung, Vorverarbeitung, Training, Server) lesen hier,
damit Training und Live-Inferenz garantiert dieselben Parameter verwenden.
"""

from pathlib import Path

# --- Pfade ---------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BACKEND_DIR.parent
DATASET_DIR = BACKEND_DIR / "dataset"
MODELS_DIR = BACKEND_DIR / "models"
FRONTEND_DIR = PROJECT_DIR / "frontend"
MODEL_PATH = MODELS_DIR / "model.pt"
NORM_STATS_PATH = MODELS_DIR / "norm_stats.npz"

# --- Sensorik ------------------------------------------------------------
SAMPLE_RATE_HZ = 50          # muss mit der Watch-App uebereinstimmen
CHANNELS = ["ax", "ay", "az", "gx", "gy", "gz"]
NUM_CHANNELS = len(CHANNELS)

# --- Segmentierung (Pausen-Erkennung) ------------------------------------
# Bewegungsenergie = Norm der userAcceleration. Werte empirisch kalibrieren.
ENERGY_START_THRESHOLD = 0.06   # ueber diesem Wert beginnt "Schreiben"
ENERGY_STOP_THRESHOLD = 0.04    # darunter zaehlt als "ruhig" (Hysterese)
PAUSE_DURATION_S = 0.35         # so lange ruhig => Segment beendet
MIN_SEGMENT_DURATION_S = 0.30   # kuerzere Segmente verwerfen (Zucken)
MAX_SEGMENT_DURATION_S = 4.0    # laengere abschneiden/verwerfen
SMOOTHING_WINDOW = 5            # gleitender Mittelwert ueber Energie (Samples)

# --- Vorverarbeitung -----------------------------------------------------
RESAMPLE_LENGTH = 100        # jedes Segment auf so viele Zeitschritte bringen

# --- Modell / Klassen ----------------------------------------------------
NUM_CLASSES = 10             # Ziffern 0-9

# --- Live-Inferenz -------------------------------------------------------
CONFIDENCE_THRESHOLD = 0.6   # darunter: zurueckweisen statt raten

# --- Server --------------------------------------------------------------
HOST = "0.0.0.0"
PORT = 8000
