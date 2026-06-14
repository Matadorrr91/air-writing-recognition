"""Data Augmentation: erzeugt aus jedem echten Segment mehrere plausible
Varianten. Das vergroessert den Datensatz und macht das Netz robuster gegen
kleine Unterschiede in Tempo, Groesse und Handhaltung.

Operiert auf rohen Segmenten (N, 6) *vor* dem Resampling.
Kanal-Reihenfolge: [ax, ay, az, gx, gy, gz].
"""

import numpy as np


def jitter(seg: np.ndarray, sigma: float, rng: np.random.Generator) -> np.ndarray:
    """Gaussches Sensorrauschen addieren."""
    return seg + rng.normal(0.0, sigma, size=seg.shape).astype(np.float32)


def scale(seg: np.ndarray, sigma: float, rng: np.random.Generator) -> np.ndarray:
    """Globale Amplituden-Skalierung (groesser/kleiner geschrieben)."""
    factor = float(rng.normal(1.0, sigma))
    return (seg * factor).astype(np.float32)


def time_warp(seg: np.ndarray, sigma: float, rng: np.random.Generator) -> np.ndarray:
    """Tempo variieren: Segment auf leicht andere Laenge interpolieren."""
    n = seg.shape[0]
    factor = float(np.clip(rng.normal(1.0, sigma), 0.7, 1.4))
    new_n = max(2, int(round(n * factor)))
    src = np.linspace(0.0, 1.0, num=n)
    dst = np.linspace(0.0, 1.0, num=new_n)
    out = np.empty((new_n, seg.shape[1]), dtype=np.float32)
    for ch in range(seg.shape[1]):
        out[:, ch] = np.interp(dst, src, seg[:, ch])
    return out


def _small_rotation(sigma_rad: float, rng: np.random.Generator) -> np.ndarray:
    """Zufaellige kleine 3D-Rotationsmatrix (Roll/Pitch/Yaw)."""
    rx, ry, rz = rng.normal(0.0, sigma_rad, size=3)
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return (Rz @ Ry @ Rx).astype(np.float32)


def rotate(seg: np.ndarray, sigma_rad: float, rng: np.random.Generator) -> np.ndarray:
    """Leicht veraenderte Handhaltung simulieren: dieselbe Rotation auf den
    Beschleunigungs- und den Drehraten-Vektor anwenden."""
    R = _small_rotation(sigma_rad, rng)
    out = seg.copy()
    out[:, 0:3] = seg[:, 0:3] @ R.T
    out[:, 3:6] = seg[:, 3:6] @ R.T
    return out


def augment_segment(seg: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Zufaellige Kombination der Transformationen anwenden."""
    out = seg.astype(np.float32)
    out = time_warp(out, sigma=0.1, rng=rng)
    out = rotate(out, sigma_rad=0.12, rng=rng)     # ~7 Grad Streuung
    out = scale(out, sigma=0.1, rng=rng)
    out = jitter(out, sigma=0.01, rng=rng)
    return out


def augment_dataset(
    segments: list[np.ndarray],
    labels: list[int],
    factor: int = 5,
    seed: int = 0,
) -> tuple[list[np.ndarray], list[int]]:
    """Originale behalten und je `factor`-1 zusaetzliche Varianten erzeugen.

    Gibt (augmentierte Segmente, zugehoerige Labels) zurueck.
    """
    rng = np.random.default_rng(seed)
    out_segs: list[np.ndarray] = []
    out_labels: list[int] = []
    for seg, lab in zip(segments, labels):
        out_segs.append(seg.astype(np.float32))
        out_labels.append(lab)
        for _ in range(max(0, factor - 1)):
            out_segs.append(augment_segment(seg, rng))
            out_labels.append(lab)
    return out_segs, out_labels
