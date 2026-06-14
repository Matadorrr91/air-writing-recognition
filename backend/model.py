"""1D-CNN zur Ziffernerkennung.

Eingabe:  (Batch, Kanaele=6, Zeit=RESAMPLE_LENGTH)
Ausgabe:  (Batch, 10) Logits -> Softmax ueber die Ziffern 0-9.

Bewusst klein gehalten: laeuft problemlos auf der CPU und braucht weniger
Daten als ein grosses Netz.
"""

import torch
import torch.nn as nn

from . import config


class AirWritingCNN(nn.Module):
    def __init__(self, num_channels: int = config.NUM_CHANNELS, num_classes: int = config.NUM_CLASSES):
        super().__init__()

        def block(in_ch: int, out_ch: int) -> nn.Sequential:
            return nn.Sequential(
                nn.Conv1d(in_ch, out_ch, kernel_size=5, padding=2),
                nn.BatchNorm1d(out_ch),
                nn.ReLU(),
                nn.MaxPool1d(2),
            )

        self.features = nn.Sequential(
            block(num_channels, 64),
            block(64, 128),
            block(128, 128),
        )
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        self.classifier = nn.Sequential(
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (B, C, T)
        x = self.features(x)
        x = self.global_pool(x).squeeze(-1)   # (B, 128)
        return self.classifier(x)


def load_model(path=config.MODEL_PATH, device: str = "cpu") -> AirWritingCNN:
    """Trainiertes Modell fuer die Inferenz laden."""
    model = AirWritingCNN()
    state = torch.load(path, map_location=device, weights_only=True)
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    return model
