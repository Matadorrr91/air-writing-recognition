"""Vorverarbeitung: bringt jedes (unterschiedlich lange) Segment auf eine
feste Form fuer das Netz.

Schritte:
  1. Resampling auf feste Laenge (lineare Interpolation pro Kanal).
  2. Z-Score-Normalisierung pro Kanal mit der *Trainingsstatistik*
     (mean/std), damit Training und Live-Inferenz identisch normalisieren.
"""

import numpy as np

from . import config


def resample_segment(seg: np.ndarray, length: int = config.RESAMPLE_LENGTH) -> np.ndarray:
    """Segment (N, C) per linearer Interpolation auf (length, C) bringen."""
    seg = np.asarray(seg, dtype=np.float32)
    n, c = seg.shape
    if n == length:
        return seg.copy()
    src = np.linspace(0.0, 1.0, num=n)
    dst = np.linspace(0.0, 1.0, num=length)
    out = np.empty((length, c), dtype=np.float32)
    for ch in range(c):
        out[:, ch] = np.interp(dst, src, seg[:, ch])
    return out


def compute_norm_stats(segments: list[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    """Mittelwert und Standardabweichung pro Kanal ueber alle (resampleten)
    Trainingssegmente berechnen."""
    stacked = np.concatenate([resample_segment(s) for s in segments], axis=0)
    mean = stacked.mean(axis=0)
    std = stacked.std(axis=0)
    std[std < 1e-6] = 1e-6   # Division durch null vermeiden
    return mean.astype(np.float32), std.astype(np.float32)


def normalize(x: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return ((x - mean) / std).astype(np.float32)


def preprocess(seg: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    """Komplett: Resampling + Normalisierung -> (RESAMPLE_LENGTH, C)."""
    return normalize(resample_segment(seg), mean, std)


def save_norm_stats(mean: np.ndarray, std: np.ndarray, path=config.NORM_STATS_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(path, mean=mean, std=std)


def load_norm_stats(path=config.NORM_STATS_PATH) -> tuple[np.ndarray, np.ndarray]:
    data = np.load(path)
    return data["mean"].astype(np.float32), data["std"].astype(np.float32)
