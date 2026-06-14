"""Selbsttest der Kernlogik ohne Hardware (nur numpy noetig).

Aufruf aus dem Projektordner:
    python -m tests.test_pipeline

Prueft:
  - Segmentierung trennt eine synthetische Aufnahme korrekt an den Pausen
  - Vorverarbeitung liefert die feste Form
  - Augmentation vervielfacht den Datensatz
  - Segmente lassen sich speichern und wieder laden
"""

import sys
import tempfile
from pathlib import Path

import numpy as np

# Projektordner importierbar machen
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend import config, data, preprocessing  # noqa: E402
from backend.augment import augment_dataset  # noqa: E402
from backend.segmentation import segment_recording  # noqa: E402


def synth_recording():
    """Aufnahme: idle, schreiben, Pause, schreiben, idle -> erwartet 2 Segmente."""
    fs = config.SAMPLE_RATE_HZ
    samples = []
    t = 0.0
    dt = 1.0 / fs

    def add(duration, writing):
        nonlocal t
        n = int(duration * fs)
        for i in range(n):
            if writing:
                a = 0.25 * np.sin(2 * np.pi * 3 * (i / fs))  # kraeftige Bewegung
                g = 0.5 * np.cos(2 * np.pi * 3 * (i / fs))
            else:
                a = 0.002 * np.sin(i)                         # quasi ruhig
                g = 0.0
            samples.append({"t": t, "ax": a, "ay": a * 0.5, "az": a * 0.3,
                            "gx": g, "gy": g * 0.4, "gz": g * 0.2})
            t += dt

    add(0.5, False)
    add(1.0, True)
    add(0.5, False)   # Pause zwischen den Ziffern
    add(1.0, True)
    add(0.5, False)
    return samples


def test_segmentation():
    segs = segment_recording(synth_recording())
    assert len(segs) == 2, f"erwartet 2 Segmente, erhalten {len(segs)}"
    for s in segs:
        assert s.shape[1] == config.NUM_CHANNELS
        assert len(s) > 0.3 * config.SAMPLE_RATE_HZ
    print(f"[ok] Segmentierung: {len(segs)} Segmente, Laengen {[len(s) for s in segs]}")


def test_preprocessing():
    segs = segment_recording(synth_recording())
    mean, std = preprocessing.compute_norm_stats(segs)
    x = preprocessing.preprocess(segs[0], mean, std)
    assert x.shape == (config.RESAMPLE_LENGTH, config.NUM_CHANNELS), x.shape
    assert np.isfinite(x).all()
    print(f"[ok] Vorverarbeitung: Form {x.shape}, Mittel~0 ({x.mean():+.3f})")


def test_augment():
    segs = segment_recording(synth_recording())
    labels = [3, 7]
    aug_s, aug_l = augment_dataset(segs, labels, factor=4, seed=1)
    assert len(aug_s) == len(segs) * 4
    assert len(aug_l) == len(aug_s)
    # je Label genau factor Eintraege; Original steht jeweils zuerst pro Block
    assert aug_l.count(3) == 4 and aug_l.count(7) == 4
    assert aug_l[0] == 3 and aug_l[4] == 7
    assert np.array_equal(aug_s[0], segs[0])  # erstes pro Block ist das Original
    print(f"[ok] Augmentation: {len(segs)} -> {len(aug_s)} Segmente")


def test_save_load():
    segs = segment_recording(synth_recording())
    with tempfile.TemporaryDirectory() as tmp:
        config.DATASET_DIR = Path(tmp)          # Test-Speicherort
        data.save_segment(segs[0], label=3, person="test", index=0)
        data.save_segment(segs[1], label=7, person="test", index=0)
        loaded = data.load_all()
        assert len(loaded) == 2
        assert {s.label for s in loaded} == {3, 7}
        assert all(s.person == "test" for s in loaded)
    print(f"[ok] Speichern/Laden: {len(loaded)} Segmente round-trip")


if __name__ == "__main__":
    test_segmentation()
    test_preprocessing()
    test_augment()
    test_save_load()
    print("\nAlle Tests bestanden.")
