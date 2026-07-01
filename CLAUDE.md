# CLAUDE.md — Briefing für Claude Code

Dieses Dokument richtet sich an **Claude Code** (oder einen anderen Assistenten),
der dieses Projekt auf einem **Windows-Rechner** weiterführt. Lies es zuerst
vollständig, damit der Nutzer nichts wiederholen muss.

## Was ist das Projekt?
Air-Writing: In die Luft geschriebene Ziffern (0–9) werden von einer **nativen
iOS-App** (iPhone, SwiftUI + CoreMotion) erfasst, per WebSocket an ein
Python-Backend gestreamt, dort segmentiert und mit einem 1D-CNN klassifiziert.
Ergebnis erscheint live im Browser. Details: siehe `README.md`.

## Aktueller Stand (Übergabe vom Mac)
- ✅ **Backend, Frontend, Modell-Code, Tests** sind vollständig und lauffähig.
- ✅ Die **iPhone-App** (`app/AirWritingPhone/`) ist gebaut und **auf dem iPhone
  des Nutzers installiert**. Sie streamt iPhone-CoreMotion-Daten (50 Hz) als JSON
  an `ws://<server-ip>:8000/ws/watch`.
- ✅ **Verbindung iPhone → Backend → Browser wurde erfolgreich getestet**:
  Segmente (blaue Kreise) erscheinen live.
- ℹ️ Die Erfassung läuft ausschließlich über die **iOS-App**
  (`app/AirWritingPhone/`). Es gibt keine watchOS-Version.

## Ziel auf dem Windows-Rechner
Der Nutzer will **Daten sammeln und das Modell trainieren** (kein Mac mehr nötig).
Hilf ihm konkret bei dieser Reihenfolge:

1. **Umgebung einrichten**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```
2. **Laptop-IP herausfinden** (`ipconfig`, IPv4 des WLAN-Adapters) und prüfen,
   dass iPhone + Laptop im **selben WLAN** sind. Ggf. Windows-Firewall für
   Python/Port 8000 freigeben.
3. **Daten sammeln** (interaktiv, im Vordergrund-Terminal, damit der Nutzer die
   Prompts sieht):
   ```powershell
   python -m backend.collect --person <name> --count 30 --shuffle
   ```
   In der App **Stop → Start** drücken (verbindet mit dem Sammel-Server). Das
   Terminal sagt, welche Ziffer zu schreiben ist. Ziel: **alle 10 Ziffern**,
   mind. ~20–30 je Ziffer (mehr = besser). Beenden mit Strg+C.
4. **Trainieren**
   ```powershell
   python -m backend.train
   ```
   Erzeugt `backend/models/model.pt` + `norm_stats.npz`, gibt Confusion-Matrix aus.
5. **Live erkennen**
   ```powershell
   python -m backend.server
   ```
   Browser auf <http://localhost:8000>. In der App IP+Port → Start.

## Wichtige Fakten / Stolperfallen
- `collect` und `server` sind **beide** ein WebSocket-Server auf **Port 8000** →
  immer nur **eines** gleichzeitig laufen lassen.
- Server bindet an `0.0.0.0:8000` (`backend/config.py`), ist also im LAN erreichbar.
- **Abtastrate 50 Hz** muss zwischen App und `backend/config.py`
  (`SAMPLE_RATE_HZ`) übereinstimmen — ist bereits konsistent.
- iOS verlangt **„Lokales Netzwerk"-Erlaubnis** für die App (einmaliges Pop-up).
- Gesammelte Daten (`backend/dataset/`) und Modelle (`backend/models/`) sind
  **bewusst nicht eingecheckt** (.gitignore) — sie sind personen-/laufabhängig.
- Die App kann auf Windows **nicht neu gebaut** werden (Xcode ist Mac-only). Mit
  dem kostenlosen Account läuft die installierte App ~7 Tage; danach wäre wieder
  ein Mac nötig. Für Datensammlung/Training auf Windows ist **kein** Xcode nötig.

## Schlüsseldateien
- `backend/config.py` — Konstanten: `SAMPLE_RATE_HZ`, `HOST`, `PORT`, Schwellen,
  Pfade (`MODEL_PATH`, `NORM_STATS_PATH`).
- `backend/server.py` — FastAPI; Endpunkte `WS /ws/watch` (Sensordaten),
  `WS /ws/display` (Ziffern an Browser); lädt Modell, wenn vorhanden.
- `backend/collect.py` — gelabeltes Sammeln (Args: `--person`, `--count`,
  `--digits`, `--shuffle`).
- `backend/train.py` — Training + Evaluation.
- `backend/segmentation.py`, `preprocessing.py`, `augment.py`, `model.py`,
  `data.py` — die Pipeline-Bausteine.
- `app/AirWritingPhone/` — Swift-Quellen der iPhone-App (Referenz).

## Sinnvolle nächste Schritte, bei denen du helfen kannst
- Datensammlung begleiten (genug pro Ziffer? Balance prüfen mit
  `ls backend/dataset` bzw. Verteilung auszählen).
- Nach dem Training die **Confusion-Matrix** interpretieren und gezielt mehr Daten
  für verwechselte Ziffern vorschlagen.
- Schwellen in `config.py` kalibrieren, falls Segmente schlecht erkannt werden.
- Tests laufen lassen (`python -m tests.test_pipeline`, `python tests\smoke_e2e.py`).
