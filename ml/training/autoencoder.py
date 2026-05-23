"""Dense autoencoder for semi-supervised anomaly detection on sensor readings.

Trained on known-normal rows only -- the same framing as notebook 05's Isolation
Forest. Reconstruction error is the anomaly score: a row the model cannot
reconstruct is, by construction, unlike anything it saw during training.

Notebook 06 is the only caller. The training loop, the held-out-normal loss
tracking and the reconstruction-error definition all live here so the single-seed
run, the latent-width sweep and the 5-seed variance check can't silently drift
from what eventually gets saved to `models/autoencoder/`.
"""

from __future__ import annotations

import numpy as np
import torch
from sklearn.model_selection import train_test_split
from torch import nn


class SensorAutoencoder(nn.Module):
    """Symmetric dense autoencoder: n_features -> hidden -> latent -> hidden -> n_features."""

    def __init__(self, n_features: int, hidden: int = 16, latent: int = 6) -> None:
        super().__init__()
        self.config = {"n_features": n_features, "hidden": hidden, "latent": latent}
        self.encoder = nn.Sequential(
            nn.Linear(n_features, hidden),
            nn.ReLU(),
            nn.Linear(hidden, latent),
        )
        self.decoder = nn.Sequential(
            nn.Linear(latent, hidden),
            nn.ReLU(),
            nn.Linear(hidden, n_features),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.decoder(self.encoder(x))

    @classmethod
    def from_config(cls, config: dict) -> "SensorAutoencoder":
        """Rebuild an untrained model with the same architecture as a saved one."""
        return cls(config["n_features"], hidden=config["hidden"], latent=config["latent"])


def train_autoencoder(
    Z: np.ndarray,
    hidden: int = 16,
    latent: int = 6,
    epochs: int = 300,
    seed: int = 42,
    holdout_frac: float = 0.15,
    lr: float = 1e-3,
    batch_size: int = 64,
    verbose: bool = False,
) -> tuple[SensorAutoencoder, dict]:
    """Fit a `SensorAutoencoder` on standardised, known-normal rows.

    `Z` is split internally into a training slice and a held-out normal slice
    (`holdout_frac`) so training can be monitored for memorisation without
    touching the labelled validation set: an autoencoder that is memorising
    shows up as training loss that keeps falling while held-out normal loss
    stalls or rises.

    Returns `(model, history)` where `history` has `"train"` and `"holdout"`,
    one MSE per epoch each.
    """
    torch.manual_seed(seed)
    rng = np.random.RandomState(seed)

    Z_train, Z_hold = train_test_split(Z, test_size=holdout_frac, random_state=seed)

    model = SensorAutoencoder(Z.shape[1], hidden=hidden, latent=latent)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    x_train = torch.tensor(Z_train, dtype=torch.float32)
    x_hold = torch.tensor(Z_hold, dtype=torch.float32)
    n = len(x_train)

    history: dict[str, list[float]] = {"train": [], "holdout": []}

    for epoch in range(epochs):
        model.train()
        perm = torch.from_numpy(rng.permutation(n))
        running = 0.0
        for start in range(0, n, batch_size):
            idx = perm[start : start + batch_size]
            batch = x_train[idx]
            optimizer.zero_grad()
            recon = model(batch)
            loss = loss_fn(recon, batch)
            loss.backward()
            optimizer.step()
            running += loss.item() * len(idx)
        train_loss = running / n

        model.eval()
        with torch.no_grad():
            hold_loss = loss_fn(model(x_hold), x_hold).item()

        history["train"].append(train_loss)
        history["holdout"].append(hold_loss)

        if verbose and (epoch % max(1, epochs // 10) == 0 or epoch == epochs - 1):
            print(f"  epoch {epoch:4d}  train {train_loss:.5f}  holdout {hold_loss:.5f}")

    return model, history


def reconstruction_error(
    model: SensorAutoencoder, Z: np.ndarray, per_feature: bool = False
) -> np.ndarray:
    """Squared reconstruction error.

    Mean over features per row by default (the anomaly score); pass
    `per_feature=True` for the un-aggregated (n_rows, n_features) error, used
    for the "which signal is wrong" attribution the Isolation Forest can't
    produce.
    """
    model.eval()
    with torch.no_grad():
        x = torch.tensor(Z, dtype=torch.float32)
        sq_err = (model(x) - x).pow(2).numpy()
    return sq_err if per_feature else sq_err.mean(axis=1)
