# iOS-App — Build-Anleitung (nur auf einem Mac mit Xcode)

Die **iOS-App** liegt im Ordner [`AirWritingPhone/`](AirWritingPhone/) und wird
über das Xcode-Projekt `AirWriting.xcodeproj` gebaut (Schema/Target
**AirWritingPhone**).

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
