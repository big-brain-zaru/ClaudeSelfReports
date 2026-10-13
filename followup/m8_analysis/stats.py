"""Statistics used by the M8 analysis. Small, explicit implementations so every number can be traced."""
import math

import numpy as np
from scipy import stats

RNG_SEED = 2026
NBOOT = 10000


def mean(x):
    x = [v for v in x if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return float(np.mean(x)) if x else float("nan")


def fisher_greater(a_yes, a_n, b_yes, b_n):
    """One-sided Fisher exact: rate A > rate B."""
    return float(stats.fisher_exact([[a_yes, a_n - a_yes], [b_yes, b_n - b_yes]], alternative="greater")[1])


def welch_greater(a, b):
    """One-sided Welch t: mean(a) > mean(b). Returns (diff, p, ci95 two-sided of the difference)."""
    a, b = np.asarray([v for v in a if v is not None], float), np.asarray([v for v in b if v is not None], float)
    if len(a) < 2 or len(b) < 2:
        return float("nan"), float("nan"), [float("nan")] * 2
    t, p2 = stats.ttest_ind(a, b, equal_var=False)
    p = p2 / 2 if t > 0 else 1 - p2 / 2
    va, vb = a.var(ddof=1) / len(a), b.var(ddof=1) / len(b)
    se = math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / (len(a) - 1) + vb ** 2 / (len(b) - 1)) if se > 0 else 1
    d = a.mean() - b.mean()
    h = stats.t.ppf(0.975, df) * se
    return float(d), float(p), [float(d - h), float(d + h)]


def mwu_greater(a, b):
    a, b = [v for v in a if v is not None], [v for v in b if v is not None]
    if not a or not b:
        return float("nan")
    return float(stats.mannwhitneyu(a, b, alternative="greater")[1])


def tost_from_moments(m1, v1, n1, m2, v2, n2, margin):
    """TOST equivalence of two means within +-margin from means, variances (ddof 1) and counts. Returns p (max of the two)."""
    if n1 < 2 or n2 < 2:
        return float("nan")
    se = math.sqrt(v1 / n1 + v2 / n2)
    if se == 0:
        return 0.0 if abs(m1 - m2) < margin else 1.0
    df = (v1 / n1 + v2 / n2) ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)) if (v1 + v2) > 0 else n1 + n2 - 2
    d = m1 - m2
    p_low = 1 - stats.t.cdf((d + margin) / se, df)
    p_high = stats.t.cdf((d - margin) / se, df)
    return float(max(p_low, p_high))


def tost(a, b, margin):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return tost_from_moments(a.mean(), a.var(ddof=1), len(a), b.mean(), b.var(ddof=1), len(b), margin)


def clopper_pearson(k, n, alpha=0.05):
    if n == 0:
        return [float("nan"), float("nan")]
    lo = 0.0 if k == 0 else stats.beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else stats.beta.ppf(1 - alpha / 2, k + 1, n - k)
    return [float(lo), float(hi)]


def boot_ci(fn, n, nboot=NBOOT, seed=RNG_SEED):
    """Percentile CI of fn(idx) over resampled index arrays of size n."""
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(nboot):
        v = fn(rng.integers(0, n, n))
        if v is not None and not (isinstance(v, float) and math.isnan(v)):
            vals.append(v)
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))] if vals else [float("nan")] * 2


def boot_diff_ci(a, b, nboot=NBOOT, seed=RNG_SEED):
    rng = np.random.default_rng(seed)
    a, b = np.asarray(a, float), np.asarray(b, float)
    if not len(a) or not len(b):
        return [float("nan")] * 2
    d = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(nboot)]
    return [float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))]


def holm(ps):
    """Holm-adjusted p-values, same order as input (NaN stays NaN)."""
    idx = [i for i, p in enumerate(ps) if p == p]
    order = sorted(idx, key=lambda i: ps[i])
    adj, run = [float("nan")] * len(ps), 0.0
    m = len(order)
    for r, i in enumerate(order):
        run = max(run, min(1.0, (m - r) * ps[i]))
        adj[i] = run
    return adj


def spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = ~(np.isnan(x) | np.isnan(y))
    if ok.sum() < 3:
        return float("nan"), float("nan")
    r, p = stats.spearmanr(x[ok], y[ok])
    return float(r), float(p)


def partial_spearman(x, y, z, nperm=NBOOT, seed=RNG_SEED):
    """Rank partial correlation of x and y given z; one-sided permutation p (positive)."""
    rx, ry, rz = (stats.rankdata(v) for v in (x, y, z))

    def pc(a, b, c):
        rab, rac, rbc = np.corrcoef(a, b)[0, 1], np.corrcoef(a, c)[0, 1], np.corrcoef(b, c)[0, 1]
        return (rab - rac * rbc) / math.sqrt(max(1e-12, (1 - rac ** 2) * (1 - rbc ** 2)))

    obs = pc(rx, ry, rz)
    rng = np.random.default_rng(seed)
    perm = [pc(rx, rng.permutation(ry), rz) for _ in range(nperm)]
    return float(obs), float((np.sum(np.array(perm) >= obs) + 1) / (nperm + 1))


def krippendorff_nominal(data):
    """data: list of units, each a list of codes (None = missing). Nominal alpha."""
    units = [[c for c in u if c is not None] for u in data]
    units = [u for u in units if len(u) >= 2]
    if not units:
        return float("nan")
    cats = sorted({c for u in units for c in u})
    ix = {c: i for i, c in enumerate(cats)}
    o = np.zeros((len(cats), len(cats)))
    for u in units:
        m = len(u)
        for i, a in enumerate(u):
            for j, b in enumerate(u):
                if i != j:
                    o[ix[a], ix[b]] += 1 / (m - 1)
    n_c = o.sum(1)
    n = n_c.sum()
    do = o.sum() - np.trace(o)
    de = (n * n - (n_c ** 2).sum()) / (n - 1)
    return float(1 - do / de) if de > 0 else float("nan")


def cohen_kappa(a, b):
    a, b = np.asarray(a), np.asarray(b)
    po = np.mean(a == b)
    cats = np.union1d(a, b)
    pe = sum(np.mean(a == c) * np.mean(b == c) for c in cats)
    return float((po - pe) / (1 - pe)) if pe < 1 else float("nan")


def icc21(M):
    """ICC(2,1), two-way random, absolute agreement, single rater. M: targets x raters."""
    M = np.asarray(M, float)
    n, k = M.shape
    gm = M.mean()
    msr = k * ((M.mean(1) - gm) ** 2).sum() / (n - 1)
    msc = n * ((M.mean(0) - gm) ** 2).sum() / (k - 1)
    sse = ((M - M.mean(1, keepdims=True) - M.mean(0, keepdims=True) + gm) ** 2).sum()
    mse = sse / ((n - 1) * (k - 1))
    return float((msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n))


def pca_loadings(P, k=2):
    """P: requests x scales profile. z-score columns, return (loadings scales x k, explained share)."""
    Z = (P - P.mean(0)) / (P.std(0) + 1e-9)
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    L = Vt[:k].T * S[:k] / math.sqrt(len(P) - 1)
    return L, (S ** 2 / (S ** 2).sum())


def tucker_after_procrustes(A, B):
    """Rotate B onto A (orthogonal Procrustes), return mean Tucker phi over columns."""
    U, _, Vt = np.linalg.svd(B.T @ A)
    Br = B @ (U @ Vt)
    phis = [float(A[:, j] @ Br[:, j] / math.sqrt((A[:, j] @ A[:, j]) * (Br[:, j] @ Br[:, j]) + 1e-12)) for j in range(A.shape[1])]
    return float(np.mean(phis)), phis


def congruence(x, y):
    x, y = np.asarray(x, float) - np.mean(x), np.asarray(y, float) - np.mean(y)
    return float(x @ y / math.sqrt((x @ x) * (y @ y) + 1e-12))


def bradley_terry(n_items, outcomes, iters=500, prior=0.5):
    """outcomes: list of (winner, loser) item indices. MM algorithm with a small symmetric prior. Returns log-strengths (centered)."""
    W = np.full((n_items, n_items), 0.0)
    for w, l in outcomes:
        W[w, l] += 1
    W += prior * (1 - np.eye(n_items)) / max(1, n_items - 1)
    p = np.ones(n_items)
    N = W + W.T
    wins = W.sum(1)
    for _ in range(iters):
        denom = (N / (p[:, None] + p[None, :])).sum(1)
        p = wins / denom
        p /= np.exp(np.mean(np.log(p)))
    return np.log(p) - np.log(p).mean()


def binom_greater(k, n, p0):
    return float(stats.binomtest(k, n, p0, alternative="greater").pvalue) if n else float("nan")


def sign_test_greater(diffs):
    pos, neg = sum(d > 0 for d in diffs), sum(d < 0 for d in diffs)
    return float(stats.binomtest(pos, pos + neg, 0.5, alternative="greater").pvalue) if pos + neg else float("nan")
