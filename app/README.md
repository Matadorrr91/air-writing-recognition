# App — Build-Anleitung (nur auf einem Mac mit Xcode)

Dieses Xcode-Projekt enthält **zwei Targets**:

| Target | Ordner | Status |
|---|---|---|
| **AirWritingPhone** | [`AirWritingPhone/`](AirWritingPhone/) | ✅ **aktiv** — die genutzte iPhone-App |
| AirWriting | [`AirWriting/`](AirWriting/) | Apple-Watch-App (Referenz, nicht genutzt) |

> **Warum iPhone statt Watch?** Auf der getesteten Apple Watch Series 4
> (watchOS 10.5) ließ sich mit einem **kostenlosen** Apple-Entwickler-Account
> keine eigenständige Watch-App installieren (watchOS verlangte eine
> Companion-App; mehrere Anläufe scheiterten an Verbindungs-/Installations-
> grenzen der alten Hardware). Da iPhone und Watch **dieselben Sensoren**
> (`userAcceleration` + `rotationRate`) liefern und das Backend nur das
> JSON-Format kennt, wurde auf die **iPhone-App** umgestellt. Backend und
> Datenformat blieben unverändert.

## Was die App tut
Liest die Bewegungssensoren (CoreMotion, 50 Hz) und streamt jedes Sample als
JSON über einen WebSocket an `ws://<server-ip>:8000/ws/watch`. Felder:
`t, ax, ay, az, gx, gy, gz`. Muss zu `backend/config.py` (`SAMPLE_RATE_HZ`) passen.

## Bauen & auf das iPhone bringen
1. `AirWriting.xcodeproj` in **Xcode** öffnen.
2. Schema **AirWritingPhone** wählen, Ziel = dein iPhone.
3. Unter **Signing & Capabilities** das eigene Apple-ID-Team eintragen
   (kostenloser Account genügt), Bundle-ID ggf. eindeutig machen.
4. **Run (▶)**. Beim ersten Mal am iPhone unter
   *Einstellungen ▸ Allgemein ▸ VPN & Geräteverwaltung* dem Entwicklerprofil
   **vertrauen**.

⚠️ **Kostenloser Account:** Die App läuft **~7 Tage**, danach erneut über Xcode
(auf einem Mac) installieren.

## Benutzung
1. Backend auf dem Laptop starten (`python -m backend.collect …` oder
   `python -m backend.server`), Laptop-IP per `ipconfig` ermitteln.
2. iPhone + Laptop ins **selbe WLAN**.
3. In der App **IP + Port `8000`** eintragen → **Start**.
4. Erste Bewegung: **Bewegungs-** und **lokale-Netzwerk**-Erlaubnis bestätigen.
   Der **Sample-Zähler** zeigt, dass Daten fließen.

## Wichtige Dateien (iPhone-App)
- `AirWritingPhone/AirWritingPhoneApp.swift` — App-Einstieg.
- `AirWritingPhone/ContentView.swift` — UI (IP/Port, Start/Stop, Status).
- `AirWritingPhone/MotionStreamer.swift` — CoreMotion-Auslesen + WebSocket-Streaming.
- `../AirWritingPhone-Info.plist` — ATS-Ausnahme für lokales `ws://`.
