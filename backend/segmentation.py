"""Segmentierung: trennt den fortlaufenden Sensorstrom an den Pausen in
einzelne Schreib-Segmente (= je eine Ziffer).

Kernidee: Die Bewegungsenergie (Norm der Beschleunigung) ist beim Schreiben
hoch und in der Pause nahe null. Eine kleine State-Machine (idle <-> writing)
mit Hysterese und einer Mindest-Pausendauer erkennt die Grenzen.

Benutzung (live):
    seg = Segmenter()
    for sample in stream:
        result = seg.push(sample)   # sample: dict mit t, ax..gz
        if result is not None:
            # result ist np.ndarray (N, 6) -> an Erkennung weitergeben
"""

from collections import deque

import numpy as np

from . import config


def _accel_energy(ax: float, ay: float, az: float) -> float:
    """Bewegungsenergie eines Samples = euklidische Norm der userAcceleration."""
    return float(np.sqrt(ax * ax + ay * ay + az * az))


class Segmenter:
    """Zustandsbehaftete Pausen-Segmentierung fuer den Live-Stream."""

    IDLE = "idle"
    WRITING = "writing"

    def __init__(
        self,
        start_threshold: float = config.ENERGY_START_THRESHOLD,
        stop_threshold: float = config.ENERGY_STOP_THRESHOLD,
        pause_duration_s: float = config.PAUSE_DURATION_S,
        min_duration_s: float = config.MIN_SEGMENT_DURATION_S,
        max_duration_s: float = config.MAX_SEGMENT_DURATION_S,
        smoothing_window: int = config.SMOOTHING_WINDOW,
    ):
        self.start_threshold = start_threshold
        self.stop_threshold = stop_threshold
        self.pause_duration_s = pause_duration_s
        self.min_duration_s = min_duration_s
        self.max_duration_s = max_duration_s
        self._energy_buf = deque(maxlen=max(1, smoothing_window))

        self.state = self.IDLE
        self._segment: list[list[float]] = []   # gesammelte Samples (6 Kanaele)
        self._segment_t: list[float] = []        # zugehoerige Zeitstempel
        self._last_active_t: float | None = None  # letzter Zeitpunkt ueber stop_threshold

    def reset(self) -> None:
        self.state = self.IDLE
        self._segment.clear()
        self._segment_t.clear()
        self._last_active_t = None
        self._energy_buf.clear()

    def _smoothed_energy(self, energy: float) -> float:
        self._energy_buf.append(energy)
        return float(np.mean(self._energy_buf))

    def push(self, sample: dict) -> np.ndarray | None:
        """Naechstes Sample einspeisen. Gibt ein fertiges Segment (N,6) zurueck,
        sobald eine Pause ein Schreib-Segment beendet, sonst None."""
        t = float(sample["t"])
        row = [float(sample[c]) for c in config.CHANNELS]
        energy = self._smoothed_energy(_accel_energy(row[0], row[1], row[2]))

        if self.state == self.IDLE:
            if energy > self.start_threshold:
                # Schreiben beginnt
                self.state = self.WRITING
                self._segment = [row]
                self._segment_t = [t]
                self._last_active_t = t
            return None

        # state == WRITING
        self._segment.append(row)
        self._segment_t.append(t)
        if energy > self.stop_threshold:
            self._last_active_t = t

        # zu lang -> abbrechen und auswerten
        duration = t - self._segment_t[0]
        if duration > self.max_duration_s:
            return self._finish()

        # lange genug ruhig -> Pause erkannt
        if self._last_active_t is not None and (t - self._last_active_t) >= self.pause_duration_s:
            return self._finish()

        return None

    def _finish(self) -> np.ndarray | None:
        """Aktuelles Segment abschliessen, ruhiges Ende abschneiden, validieren."""
        seg = np.asarray(self._segment, dtype=np.float32)
        ts = np.asarray(self._segment_t, dtype=np.float64)
        last_active = self._last_active_t
        self.state = self.IDLE
        self._segment = []
        self._segment_t = []
        self._energy_buf.clear()
        self._last_active_t = None

        if last_active is None:   # defensiv; im WRITING-Zustand immer gesetzt
            return None

        # Trailing-Ruhe (die Pause selbst) abschneiden: bis zum letzten aktiven Sample
        keep = ts <= last_active + 1e-6
        seg = seg[keep]
        ts = ts[keep]
        if len(seg) < 2:
            return None

        duration = ts[-1] - ts[0]
        if duration < self.min_duration_s:
            return None   # zu kurz -> Zucken/Versehen verwerfen
        return seg


def segment_recording(samples: list[dict], **kwargs) -> list[np.ndarray]:
    """Offline-Variante: eine komplette Aufnahme in Segmente zerlegen.

    Nuetzlich fuer Unit-Tests und Batch-Verarbeitung von CSV-Aufnahmen.
    """
    seg = Segmenter(**kwargs)
    out: list[np.ndarray] = []
    for s in samples:
        result = seg.push(s)
        if result is not None:
            out.append(result)
    # ggf. laufendes Segment am Ende durch eine kuenstliche Pause beenden
    if seg.state == Segmenter.WRITING and seg._segment_t:
        last_t = seg._segment_t[-1]
        flush = dict(zip(config.CHANNELS, [0.0] * config.NUM_CHANNELS))
        flush["t"] = last_t + seg.pause_duration_s + 1.0
        result = seg.push(flush)
        if result is not None:
            out.append(result)
    return out
