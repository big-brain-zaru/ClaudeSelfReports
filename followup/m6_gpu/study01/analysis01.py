"""Study 01 analysis (frozen before first run). H1 detection at the locked cell vs false alarms; H2 dose-response of
self-reported valence; H3 specificity vs control directions; H4 structure of the 12x5 profile; H5 activation probe vs
text-embedding baseline. Writes results.json and figures."""
import json
import re
import sys
import urllib.request
from pathlib import Path

import numpy as np
from scipy import stats
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold, cross_val_predict

OUT = Path(__file__).parent
RAW = OUT / "raw"
sys.path.insert(0, str(OUT))
from stimuli import CORE12, EXTRA36  # noqa: E402


def load(name):
    return [json.loads(l) for l in open(RAW / f"{name}.jsonl", encoding="utf-8")]


def parse_detect(out, concept):
    lines = [l.strip().strip("*").strip() for l in out.strip().splitlines() if l.strip()]
    first = lines[0].upper() if lines else ""
    yes, no = first.startswith("YES"), first.startswith("NO")
    named = bool(concept) and bool(re.search(rf"\b{re.escape(concept)}(s|es)?\b", out.lower()))
    return yes, no, named


def first_int(out, lo, hi):
    m = re.search(r"[-+]?\d+", out)
    if not m:
        return None
    v = int(m.group(0))
    return v if lo <= v <= hi else None


R = {}
lock = json.load(open(OUT / "lock.json"))
L0, s0 = int(lock["locked"].split("|")[0]), float(lock["locked"].split("|")[1])
R["locked_cell"] = {"layer": L0, "strength": s0, "rule": lock["rule"]}

# ---------------- H1 detection
test = load("test")
ctrl = [r for r in test if r["concept"] is None]
cell = [r for r in test if r["concept"] and r["layer"] == L0 and abs(r["strength"] - s0) < 1e-9]
p_ctrl = [parse_detect(r["output"], None) for r in ctrl]
p_cell = [parse_detect(r["output"], r["concept"]) for r in cell]
hits = sum(y and n for y, _, n in p_cell)
fa = sum(y for y, _, _ in p_ctrl)
R["H1"] = {"n_locked_trials": len(cell), "hits": hits, "hit_rate": hits / len(cell),
           "detect_any_rate": sum(y for y, _, _ in p_cell) / len(cell),
           "n_controls": len(ctrl), "false_alarms": fa, "fa_rate": fa / len(ctrl),
           "compliance_controls": sum(y or n for y, n, _ in p_ctrl) / len(ctrl),
           "fisher_p_one_sided": stats.fisher_exact([[hits, len(cell) - hits], [fa, len(ctrl) - fa]], alternative="greater")[1]}
R["H1"]["pass"] = bool(R["H1"]["fisher_p_one_sided"] < 0.01 and R["H1"]["hit_rate"] < 0.5)
heat = {}
for r in test:
    if r["concept"] and r["id"].startswith("test|"):
        y, n, nm = parse_detect(r["output"], r["concept"])
        k = (r["layer"], r["strength"])
        h = heat.setdefault(k, {"n": 0, "hit": 0, "yes": 0, "named_any": 0, "compliant": 0})
        h["n"] += 1; h["hit"] += y and nm; h["yes"] += y; h["named_any"] += nm; h["compliant"] += y or n
R["detection_grid"] = {f"{L}|{s}": {k: v / h["n"] if k != "n" else v for k, v in h.items()} for (L, s), h in sorted(heat.items())}

# ---------------- H2/H3 steering
steer = load("steer")
for r in steer:
    r["v"] = first_int(r["output"], -5, 5)
R["steer_parse_rate"] = {d: float(np.mean([r["v"] is not None for r in steer if r["direction"] == "valence" and r["dose"] == d]))
                         for d in sorted({r["dose"] for r in steer})}
val = [r for r in steer if r["direction"] == "valence" and r["v"] is not None]
doses = sorted({r["dose"] for r in val})
means = [np.mean([r["v"] for r in val if r["dose"] == d]) for d in doses]
rho = stats.spearmanr(doses, means)[0]
rng = np.random.default_rng(0)
perm = []
for _ in range(10000):
    shuffled = {}
    for req in CORE12:
        rs = [r for r in val if r["request"] == req]
        ds = rng.permutation([r["dose"] for r in rs])
        for r, d in zip(rs, ds):
            shuffled.setdefault(d, []).append(r["v"])
    perm.append(stats.spearmanr(sorted(shuffled), [np.mean(shuffled[d]) for d in sorted(shuffled)])[0])
R["H2"] = {"dose_means": dict(zip(map(str, doses), map(float, means))), "spearman_rho": float(rho),
           "perm_p": float(np.mean(np.array(perm) >= rho)), "pass": bool(rho >= 0.6)}


def slope(rows):
    x = np.array([r["dose"] for r in rows], float); y = np.array([r["v"] for r in rows], float)
    return float(np.polyfit(x, y, 1)[0]) if len(set(x)) > 1 else float("nan")


ctrl_dirs = ["random1", "random2", "ocean"]
sl = {d: slope([r for r in steer if r["direction"] == d and r["v"] is not None]) for d in ["valence"] + ctrl_dirs}
sv_same_doses = slope([r for r in val if r["dose"] in (-8, -4, 0, 4, 8)])
ratio = sv_same_doses / np.mean([abs(sl[d]) for d in ctrl_dirs])
boots = []
for _ in range(2000):
    reqs = rng.choice(CORE12, len(CORE12))
    sub = lambda d: [r for q in reqs for r in steer if r["request"] == q and r["direction"] == d and r["v"] is not None and r["dose"] in (-8, -4, 0, 4, 8)]
    c = np.mean([abs(slope(sub(d))) for d in ctrl_dirs])
    boots.append(slope(sub("valence")) / c if c > 0 else np.nan)
R["H3"] = {"slopes": sl, "valence_slope_matched_doses": sv_same_doses, "ratio": float(ratio),
           "ratio_CI95": [float(np.nanpercentile(boots, 2.5)), float(np.nanpercentile(boots, 97.5))], "pass": bool(ratio >= 3)}

# ---------------- H4/H5 battery and probe
bat = load("battery")
def five(out):
    nums = re.findall(r"[-+]?\d+(?:\.\d+)?", out)
    return [float(x) for x in nums[:5]] if len(nums) >= 5 else None
for r in bat:
    r["p"] = five(r["output"])
R["battery_parse_rate"] = float(np.mean([r["p"] is not None for r in bat]))
core = np.array([np.mean([r["p"] for r in bat if r["request"] == q and r["p"]], 0) for q in CORE12])
Z = (core - core.mean(0)) / (core.std(0) + 1e-9)
S = np.linalg.svd(Z, compute_uv=False)
expl = S ** 2 / (S ** 2).sum()
R["H4"] = {"explained": [float(e) for e in expl], "pc1_pc2": float(expl[:2].sum()), "pass": bool(expl[:2].sum() >= 0.8),
           "profile_means": {q: [float(x) for x in row] for q, row in zip(CORE12, core)}}

A = np.load(OUT / "acts.npz")
reqs = list(A["requests"])
y = np.array([np.mean([r["p"][4] for r in bat if r["request"] == q and r["p"]] or [np.nan]) for q in reqs])
ok = ~np.isnan(y)
kf = KFold(5, shuffle=True, random_state=0)


def cv_r2(X):
    pred = cross_val_predict(RidgeCV(alphas=np.logspace(-2, 4, 20)), X[ok], y[ok], cv=kf)
    return float(1 - ((y[ok] - pred) ** 2).sum() / ((y[ok] - y[ok].mean()) ** 2).sum())


probe = {L: cv_r2(A[L]) for L in ["9", "18", "27"]}
emb = []
for q in reqs:
    req = urllib.request.Request("http://127.0.0.1:11434/api/embeddings", data=json.dumps({"model": "nomic-embed-text", "prompt": q}).encode(),
                                 headers={"Content-Type": "application/json"})
    emb.append(json.loads(urllib.request.urlopen(req, timeout=120).read())["embedding"])
text_r2 = cv_r2(np.array(emb))
R["H5"] = {"probe_r2_by_layer": probe, "text_embedding_r2": text_r2, "n_requests": int(ok.sum()),
           "pass": bool(probe["18"] >= 0.5 and probe["18"] - text_r2 >= 0.1)}
json.dump(R, open(OUT / "results.json", "w"), indent=1, default=float)
print(json.dumps({k: R[k] for k in ["locked_cell", "H1", "H2", "H3", "H4", "H5"]}, indent=1, default=float)[:4000])
