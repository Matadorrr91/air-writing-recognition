"""Laden/Speichern der gesammelten Segmente.

Jedes Segment liegt als eigene .npz-Datei in dataset/:
    x      : float32 (N, 6)  Rohsegment, Kanaele [ax,ay,az,gx,gy,gz]
    label  : int             Ziffer 0-9
    person : str             ID der schreibenden Person
Dateiname:  {person}_{label}_{laufnummer}.npz
"""

from dataclasses import dataclass

import numpy as np

from . import config


@dataclass
class Sample:
    x: np.ndarray   # (N, 6)
    label: int
    person: str


def save_segment(seg: np.ndarray, label: int, person: str, index: int) -> str:
    config.DATASET_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{person}_{label}_{index:04d}.npz"
    path = config.DATASET_DIR / name
    np.savez(path, x=seg.astype(np.float32), label=int(label), person=str(person))
    return str(path)


def next_index(label: int, person: str) -> int:
    """Naechste freie Laufnummer fuer (person, label) ermitteln."""
    config.DATASET_DIR.mkdir(parents=True, exist_ok=True)
    existing = list(config.DATASET_DIR.glob(f"{person}_{label}_*.npz"))
    return len(existing)


def load_all() -> list[Sample]:
    """Alle Segmente aus dataset/ laden."""
    samples: list[Sample] = []
    if not config.DATASET_DIR.exists():
        return samples
    for path in sorted(config.DATASET_DIR.glob("*.npz")):
        d = np.load(path, allow_pickle=True)
        samples.append(
            Sample(
                x=d["x"].astype(np.float32),
                label=int(d["label"]),
                person=str(d["person"]),
            )
        )
    return samples


def summary(samples: list[Sample]) -> str:
    """Kurze Uebersicht: wie viele Segmente pro Ziffer und Person."""
    if not samples:
        return "Keine Segmente in dataset/ gefunden."
    persons = sorted({s.person for s in samples})
    lines = [f"Gesamt: {len(samples)} Segmente von {len(persons)} Person(en)."]
    for p in persons:
        counts = [sum(1 for s in samples if s.person == p and s.label == d) for d in range(config.NUM_CLASSES)]
        lines.append(f"  {p}: " + " ".join(f"{d}={c}" for d, c in enumerate(counts)))
    return "\n".join(lines)
