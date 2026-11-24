"""Penalised within-race (conditional) logit with a fixed offset: the engine for partial pooling.
loss = -sum over races of log P(actual winner) + sum_j lam_j * beta_j^2 / 2
A Gaussian prior beta_j ~ N(0, tau_j^2) on a course deviation is the same as lam_j = 1 / tau_j^2: the larger a course's
own evidence, the further its estimate can move away from the pooled value (0 deviation); thin evidence stays near 0."""
import numpy as np
from scipy.optimize import minimize

class Races:
    def __init__(self, race_ids, win, offset, X):
        o = np.argsort(np.asarray(race_ids), kind='stable')
        self.o = o; self.y = np.asarray(win, float)[o]; self.off = np.asarray(offset, float)[o]; self.X = np.asarray(X, float)[o]
        r = np.asarray(race_ids)[o]; self.starts = np.r_[0, np.flatnonzero(r[1:] != r[:-1]) + 1]
        self.sizes = np.diff(np.r_[self.starts, len(r)]); self.rid = np.repeat(np.arange(len(self.starts)), self.sizes)
    def _lse(self, eta):
        mx = np.maximum.reduceat(eta, self.starts); e = np.exp(eta - mx[self.rid])
        return np.log(np.add.reduceat(e, self.starts)) + mx
    def loglik_per_race(self, beta):
        eta = self.off + self.X @ beta; lse = self._lse(eta)
        return np.add.reduceat(self.y * eta, self.starts) - lse
    def top_hit(self, beta):
        eta = self.off + self.X @ beta
        best = np.array([s + np.argmax(eta[s:s + n]) for s, n in zip(self.starts, self.sizes)])
        return self.y[best]

def fit(R, lam, beta0=None):
    lam = np.asarray(lam, float); k = R.X.shape[1]
    def f(b):
        eta = R.off + R.X @ b; lse = R._lse(eta); p = np.exp(eta - lse[R.rid])
        ll = (R.y * eta).sum() - lse.sum()
        g = -(R.X.T @ (R.y - p)) + lam * b
        return -ll + 0.5 * (lam * b * b).sum(), g
    res = minimize(f, np.zeros(k) if beta0 is None else beta0, jac=True, method='L-BFGS-B', options={'maxiter': 2000})
    return res.x

def posterior_sd(R, beta, lam, eps=1e-4):
    """Laplace approximation: sd from the inverse Hessian of the penalised loss (numerical, from gradients)."""
    lam = np.asarray(lam, float); k = len(beta)
    def grad(b):
        eta = R.off + R.X @ b; lse = R._lse(eta); p = np.exp(eta - lse[R.rid]); return -(R.X.T @ (R.y - p)) + lam * b
    H = np.zeros((k, k)); g0 = grad(beta)
    for j in range(k):
        e = np.zeros(k); e[j] = eps; H[:, j] = (grad(beta + e) - g0) / eps
    H = 0.5 * (H + H.T)
    return np.sqrt(np.clip(np.diag(np.linalg.pinv(H)), 0, None))
