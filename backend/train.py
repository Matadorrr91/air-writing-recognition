"""Training + Evaluation des 1D-CNN.

Aufruf (im aktivierten venv, aus dem Projektordner):
    python -m backend.train                      # Hold-out einer Person (auto)
    python -m backend.train --test-person max    # bestimmte Person als Test
    python -m backend.train --random-split        # zufaelliger 80/20-Split
    python -m backend.train --epochs 60 --augment-factor 6

Ausgabe: Test-Accuracy + Confusion-Matrix. Speichert models/model.pt und
models/norm_stats.npz (Normalisierung muss bei der Live-Inferenz identisch sein).
"""

import argparse

import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import accuracy_score, confusion_matrix

from . import config, data, preprocessing
from .augment import augment_dataset
from .model import AirWritingCNN


def _to_tensor(segments, labels, mean, std):
    """Liste roher Segmente -> (X, y) Tensoren. X: (B, C, T)."""
    xs = [preprocessing.preprocess(s, mean, std).T for s in segments]   # je (C, T)
    X = torch.tensor(np.stack(xs), dtype=torch.float32)
    y = torch.tensor(np.asarray(labels), dtype=torch.long)
    return X, y


def _split_train_val(n, seed, val_frac=0.15):
    rng = np.random.default_rng(seed)
    idx = rng.permutation(n)
    n_val = max(1, int(n * val_frac))
    return idx[n_val:], idx[:n_val]


def train(args):
    samples = data.load_all()
    print(data.summary(samples))
    if len(samples) < 20:
        print("\n[!] Zu wenige Segmente zum Trainieren. Erst mit collect.py sammeln.")
        return

    persons = sorted({s.person for s in samples})

    # --- Train/Test-Aufteilung -------------------------------------------
    if args.random_split or len(persons) < 2:
        if not args.random_split:
            print("\n[i] Nur eine Person -> zufaelliger Split statt Hold-out.")
        rng = np.random.default_rng(args.seed)
        idx = rng.permutation(len(samples))
        n_test = max(1, int(len(samples) * 0.2))
        test_idx, train_idx = set(idx[:n_test].tolist()), set(idx[n_test:].tolist())
        train_s = [s for i, s in enumerate(samples) if i in train_idx]
        test_s = [s for i, s in enumerate(samples) if i in test_idx]
        split_desc = "zufaelliger 80/20-Split"
    else:
        test_person = args.test_person or persons[-1]
        train_s = [s for s in samples if s.person != test_person]
        test_s = [s for s in samples if s.person == test_person]
        split_desc = f"Hold-out Person '{test_person}' (Cross-Person)"
    print(f"\nSplit: {split_desc}  ->  Train={len(train_s)}  Test={len(test_s)}")

    train_segs = [s.x for s in train_s]
    train_labels = [s.label for s in train_s]

    # --- Normalisierungsstatistik NUR aus Trainingsdaten -----------------
    mean, std = preprocessing.compute_norm_stats(train_segs)

    # --- Train/Val-Split VOR der Augmentation -----------------------------
    # Sonst landen augmentierte Varianten desselben Originals in Train UND
    # Val, und das Early-Stopping-Signal waere zu optimistisch.
    tr_idx, val_idx = _split_train_val(len(train_segs), args.seed)
    val_segs = [train_segs[i] for i in val_idx]
    val_labels = [train_labels[i] for i in val_idx]
    tr_segs = [train_segs[i] for i in tr_idx]
    tr_labels = [train_labels[i] for i in tr_idx]

    # --- Augmentation (nur der Trainingsanteil) ---------------------------
    aug_segs, aug_labels = augment_dataset(tr_segs, tr_labels, factor=args.augment_factor, seed=args.seed)
    print(f"Training nach Augmentation: {len(aug_segs)} Segmente (Faktor {args.augment_factor}), Val: {len(val_segs)} Originale.")

    X_tr, y_tr = _to_tensor(aug_segs, aug_labels, mean, std)
    X_val, y_val = _to_tensor(val_segs, val_labels, mean, std)

    # --- Training mit Early Stopping -------------------------------------
    torch.manual_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AirWritingCNN().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-4)
    loss_fn = nn.CrossEntropyLoss()

    X_tr, y_tr, X_val, y_val = X_tr.to(device), y_tr.to(device), X_val.to(device), y_val.to(device)
    best_val = float("inf")
    best_state = None
    patience, since_best = args.patience, 0
    batch = 64

    for epoch in range(1, args.epochs + 1):
        model.train()
        perm = torch.randperm(len(X_tr))
        total = 0.0
        for i in range(0, len(X_tr), batch):
            bi = perm[i:i + batch]
            opt.zero_grad()
            out = model(X_tr[bi])
            loss = loss_fn(out, y_tr[bi])
            loss.backward()
            opt.step()
            total += loss.item() * len(bi)
        train_loss = total / len(X_tr)

        model.eval()
        with torch.no_grad():
            out_val = model(X_val)
            val_loss = loss_fn(out_val, y_val).item()
            val_acc = (out_val.argmax(1) == y_val).float().mean().item()
        print(f"Epoche {epoch:3d}  train_loss={train_loss:.4f}  val_loss={val_loss:.4f}  val_acc={val_acc:.3f}")

        if val_loss < best_val - 1e-4:
            best_val, best_state, since_best = val_loss, {k: v.cpu().clone() for k, v in model.state_dict().items()}, 0
        else:
            since_best += 1
            if since_best >= patience:
                print(f"Early Stopping nach {epoch} Epochen.")
                break

    if best_state is not None:
        model.load_state_dict(best_state)

    # --- Evaluation auf Test ---------------------------------------------
    model.eval()
    if test_s:
        X_te, y_te = _to_tensor([s.x for s in test_s], [s.label for s in test_s], mean, std)
        with torch.no_grad():
            pred = model(X_te.to(device)).argmax(1).cpu().numpy()
        y_true = y_te.numpy()
        acc = accuracy_score(y_true, pred)
        cm = confusion_matrix(y_true, pred, labels=list(range(config.NUM_CLASSES)))
        print(f"\n=== Test-Accuracy: {acc:.3f} ({split_desc}) ===")
        print("Confusion-Matrix (Zeile=wahr, Spalte=vorhergesagt):")
        header = "     " + " ".join(f"{d:3d}" for d in range(config.NUM_CLASSES))
        print(header)
        for d in range(config.NUM_CLASSES):
            print(f"  {d}: " + " ".join(f"{cm[d, j]:3d}" for j in range(config.NUM_CLASSES)))

    # --- Speichern --------------------------------------------------------
    config.MODELS_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), config.MODEL_PATH)
    preprocessing.save_norm_stats(mean, std)
    print(f"\nGespeichert: {config.MODEL_PATH}  und  {config.NORM_STATS_PATH}")


def main():
    p = argparse.ArgumentParser(description="1D-CNN fuer Air-Writing-Ziffern trainieren.")
    p.add_argument("--epochs", type=int, default=80)
    p.add_argument("--patience", type=int, default=12, help="Early-Stopping-Geduld")
    p.add_argument("--augment-factor", type=int, default=5, help="Vervielfachung der Trainingsdaten")
    p.add_argument("--test-person", type=str, default=None, help="Diese Person als Test (Hold-out)")
    p.add_argument("--random-split", action="store_true", help="Zufaelliger 80/20-Split statt Hold-out")
    p.add_argument("--seed", type=int, default=0)
    train(p.parse_args())


if __name__ == "__main__":
    main()
