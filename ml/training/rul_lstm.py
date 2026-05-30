"""The RUL-prediction LSTM architecture, factored out for inference reuse.

Notebook 07 defines this class inline (its own cell 25) because at training
time there is nothing else that needs it. The backend does: to load
`models/rul_model/model.pt`'s saved `state_dict` it needs the exact same
class definition the checkpoint was trained with, so it lives here rather
than being copy-pasted into the inference service. The architecture below is
identical to the notebook's -- same layer types, same shapes, same forward
pass -- so a saved checkpoint's `state_dict` loads into either one.
"""

from __future__ import annotations

import torch
from torch import nn


class RULLSTM(nn.Module):
    def __init__(
        self, n_features: int, hidden: int = 64, layers: int = 2, dropout: float = 0.2
    ) -> None:
        super().__init__()
        self.config = {
            "n_features": n_features,
            "hidden": hidden,
            "layers": layers,
            "dropout": dropout,
        }
        self.lstm = nn.LSTM(
            n_features, hidden, num_layers=layers, batch_first=True, dropout=dropout
        )
        self.head = nn.Sequential(
            nn.Linear(hidden, 32), nn.ReLU(), nn.Dropout(dropout), nn.Linear(32, 1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        out, _ = self.lstm(x)
        return self.head(out[:, -1, :]).squeeze(-1)

    @classmethod
    def from_config(cls, config: dict) -> "RULLSTM":
        return cls(**config)
