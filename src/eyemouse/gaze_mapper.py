"""Learns eye/head features -> screen position from the 9-dot calibration.

Model: degree-2 polynomial regression with ridge regularisation (a tiny
linear-in-parameters network). With only 9 calibration targets this is far
more stable than a deep net, and it fits in milliseconds.
Output is NORMALISED screen coords (0..1, 0..1) so it is DPI independent.
"""
import json
from itertools import combinations_with_replacement
from pathlib import Path

import numpy as np

CALIB_FILE = Path(__file__).resolve().parents[2] / "calibration.json"


def _poly2(x):
    """[1, x1..xn, all pairwise products incl. squares]"""
    cols = [np.ones(len(x))] + [x[:, i] for i in range(x.shape[1])]
    cols += [x[:, i] * x[:, j] for i, j in combinations_with_replacement(range(x.shape[1]), 2)]
    return np.stack(cols, axis=1)


class GazeMapper:
    def __init__(self, ridge: float = 0.05):
        self.ridge = ridge
        self.mean = self.std = self.coef = None

    @property
    def ready(self):
        return self.coef is not None

    def _fit_raw(self, X, Y):
        mean, std = X.mean(0), X.std(0) + 1e-6
        A = _poly2((X - mean) / std)
        reg = self.ridge * np.eye(A.shape[1])
        reg[0, 0] = 0  # no penalty on the intercept
        coef = np.linalg.solve(A.T @ A + reg, A.T @ Y)
        return mean, std, coef

    def fit(self, X, Y, groups):
        """X: (n,4) features, Y: (n,2) normalised targets, groups: target id per sample.
        Returns mean leave-one-target-out error (normalised units) = honest accuracy."""
        X, Y, groups = np.asarray(X), np.asarray(Y), np.asarray(groups)
        errs = []
        for g in np.unique(groups):
            tr, te = groups != g, groups == g
            m, s, c = self._fit_raw(X[tr], Y[tr])
            pred = _poly2((X[te] - m) / s) @ c
            errs.append(np.linalg.norm(pred.mean(0) - Y[te][0]))
        self.mean, self.std, self.coef = self._fit_raw(X, Y)
        return float(np.mean(errs))

    def predict(self, feats):
        """Return normalised (x, y), clipped to the screen."""
        p = _poly2(((np.asarray(feats) - self.mean) / self.std)[None])[0] @ self.coef
        return np.clip(p, 0.0, 1.0)

    def save(self, path=CALIB_FILE):
        Path(path).write_text(json.dumps({
            "mean": self.mean.tolist(), "std": self.std.tolist(), "coef": self.coef.tolist(),
        }))

    def load(self, path=CALIB_FILE):
        if not Path(path).exists():
            return False
        d = json.loads(Path(path).read_text())
        self.mean, self.std, self.coef = (np.array(d[k]) for k in ("mean", "std", "coef"))
        return True
