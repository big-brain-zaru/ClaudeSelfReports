"""Study 01b analysis (frozen before the run). Coherent doses only (parse rate >= 90% per dose and direction).
H2b: Spearman rho(dose, mean valence) for the valence direction >= 0.8.
H3b: OLS slope of valence ratings on dose (valence direction) >= 3x the mean absolute slope of the 3 control directions,
     over the same coherent doses; bootstrap 95% CI over requests."""
import json, re
from pathlib import Path
import numpy as np
from scipy import stats
OUT = Path(__file__).parent
rows = [json.loads(l) for l in open(OUT / "raw" / "steer2.jsonl", encoding="utf-8")]
for r in rows:
    m = re.search(r"[-+]?\d+", r["output"]); v = int(m.group(0)) if m else None
    r["v"] = v if v is not None and -5 <= v <= 5 else None
dirs = ["valence", "random1", "random2", "ocean"]; doses = sorted({r["dose"] for r in rows})
parse = {d: {x: float(np.mean([r["v"] is not None for r in rows if r["direction"] == d and r["dose"] == x])) for x in doses} for d in dirs}
coh = [x for x in doses if all(parse[d][x] >= 0.9 for d in dirs)]
use = [r for r in rows if r["dose"] in coh and r["v"] is not None]
means = {d: {x: float(np.mean([r["v"] for r in use if r["direction"] == d and r["dose"] == x])) for x in coh} for d in dirs}
def slope(rs):
    return float(np.polyfit([r["dose"] for r in rs], [r["v"] for r in rs], 1)[0])
sl = {d: slope([r for r in use if r["direction"] == d]) for d in dirs}
ratio = sl["valence"] / np.mean([abs(sl[d]) for d in dirs[1:]])
reqs = sorted({r["request"] for r in rows}); rng = np.random.default_rng(1); boots = []
for _ in range(2000):
    pick = rng.choice(reqs, len(reqs))
    s = {d: slope([r for q in pick for r in use if r["request"] == q and r["direction"] == d]) for d in dirs}
    c = np.mean([abs(s[d]) for d in dirs[1:]]); boots.append(s["valence"] / c if c > 0 else np.nan)
rho = stats.spearmanr(coh, [means["valence"][x] for x in coh])[0]
R = {"parse": parse, "coherent_doses": coh, "means": means, "slopes": sl, "ratio": float(ratio),
     "ratio_CI95": [float(np.nanpercentile(boots, 2.5)), float(np.nanpercentile(boots, 97.5))],
     "H2b_rho": float(rho), "H2b_pass": bool(rho >= 0.8), "H3b_pass": bool(ratio >= 3)}
json.dump(R, open(OUT / "results_01b.json", "w"), indent=1)
print(json.dumps(R, indent=1)[:3000])
