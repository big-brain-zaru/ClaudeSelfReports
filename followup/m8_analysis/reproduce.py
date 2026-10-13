"""Reproduction checks for the archived study. Run from the repository root:  python followup/m8_analysis/reproduce.py
Each check prints PASS/FAIL; the script exits non-zero if any check fails. Needs only numpy, scipy, scikit-learn and
matplotlib; no model calls (the Study 01 text-embedding baseline needs Ollama and is skipped if it is not running)."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FU = ROOT / "followup"
M8 = FU / "m8_analysis"
checks = []


def check(name, ok, detail=""):
    checks.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


# 1. Seals
h = hashlib.sha256()
for f in sorted((FU / "m1_predictions" / "predictions").glob("*.csv")):
    h.update(f.name.encode() + b"\n" + f.read_bytes())
check("M1 prediction seal (12 predictor files, hashed before any follow-up data)",
      h.hexdigest() == open(FU / "m1_predictions" / "SEAL.sha256").read().split()[0] and
      sha(FU / "m1_predictions" / "predictions" / "main_instance.csv") == open(FU / "m1_predictions" / "main_instance.sha256").read().split()[0])
lines = [l for l in open(M8 / "SEAL_ANALYSIS.sha256", encoding="utf-8").read().splitlines() if l and not l.startswith("#")]
# SEAL_POST.sha256 lists files from the seal that were changed after the analysis ran, with their new hash and the
# reason (post-analysis note P-06). A sealed file may differ from the seal only if that manifest names it.
post = {}
if (M8 / "SEAL_POST.sha256").exists():
    for l in open(M8 / "SEAL_POST.sha256", encoding="utf-8").read().splitlines():
        if l and not l.startswith("#"):
            h, rest = l.split("  ", 1)
            post[rest.split(" #")[0].strip()] = h
bad, changed = [], []
for l in lines:
    h0, f = l.split("  ")
    h = sha(FU / f)
    if h == h0:
        continue
    (changed if post.get(f) == h else bad).append(f)
check("M8 analysis seal (analysis frozen before any follow-up Claude reply was opened)", not bad,
      ", ".join(bad) if bad else ("post-seal change declared in SEAL_POST.sha256: " + ", ".join(changed) if changed else ""))

# 2. Re-run the sealed analysis into a scratch folder and compare with the archived results.json
with tempfile.TemporaryDirectory() as tmp:
    env = dict(os.environ, M8_OUT=tmp)
    r = subprocess.run([sys.executable, str(M8 / "analyze.py")], env=env, capture_output=True, text=True)
    ok = r.returncode == 0
    same, worst = False, 0.0
    if ok:
        a = json.load(open(Path(tmp) / "results.json", encoding="utf-8"))
        b = json.load(open(M8 / "results.json", encoding="utf-8"))
        # Verdicts must match exactly. Outcomes are compared to 1e-9: the sealed script sums one variance decomposition
        # (Study 09) in Python set order, which hash randomisation varies between processes, so a few outcomes can differ
        # in their last digits from run to run (post-analysis note P-06).
        strip = lambda h: {k: v for k, v in h.items() if k != "value"}
        verd = all(strip(x) == strip(y) and str(x["value"])[:12] == str(y["value"])[:12] for x, y in zip(a["hypotheses"], b["hypotheses"]))
        diffs = [abs((a["outcomes"][k] or 0) - (b["outcomes"][k] or 0)) for k in b["outcomes"]]
        worst = max(diffs) if diffs else 0.0
        same = verd and len(a["hypotheses"]) == len(b["hypotheses"]) and worst < 1e-9
    check("analyze.py re-run reproduces every hypothesis verdict and all 37 outcomes (to 1e-9)", ok and same,
          r.stderr[-300:] if not ok else f"max outcome difference {worst:.1e}")

# 3. paper_data.json numbers come from results.json
pdj = json.load(open(ROOT / "paper_data.json", encoding="utf-8"))
res = json.load(open(M8 / "results.json", encoding="utf-8"))
check("paper_data.json carries the sealed analysis output unchanged", pdj["results"]["outcomes"] == res["outcomes"] and pdj["results"]["hypotheses"] == res["hypotheses"])

# 4. Study 01b verdicts as frozen
s01b = json.load(open(FU / "m6_gpu" / "study01" / "results_01b.json"))
check("Study 01b: H2b and H3b pass as frozen", s01b["H2b_pass"] and s01b["H3b_pass"], f"rho {s01b['H2b_rho']}, ratio {s01b['ratio']:.2f}")

# 5. Layer 2 and 3 analyses re-run
for layer, cmd in [("layer2", ["analyze.py", "data.json", "pairs.json"]), ("layer3", ["analyze3.py", "data.json", "design.json", "ba_aggregate.json", "c_stimuli.json", "../layer2/data.json"])]:
    with tempfile.TemporaryDirectory() as tmp:
        r = subprocess.run([sys.executable] + cmd + [tmp], cwd=ROOT / layer, capture_output=True, text=True)
        ok = r.returncode == 0 and (Path(tmp) / "results.json").exists()
        same = ok and json.load(open(Path(tmp) / "results.json")) == json.load(open(ROOT / layer / "out" / "results.json"))
        check(f"{layer} analysis re-run reproduces out/results.json", same, r.stderr[-300:] if not ok else "")

# 6. Promise-keeping: private arms exist only as totals
rows = [json.loads(l) for l in open(FU / "jobs" / "stage1.results.jsonl", encoding="utf-8")]
priv = [r for r in rows if r.get("private")]
check("private arms stored as totals only (no reply text on disk)", priv and all("text" not in r and "reply_sha256" in r for r in priv), f"{len(priv)} rows")

# 7. Every analysed Claude row was answered by the pinned model
PIN = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5", "fable": "claude-fable-5-1"}
bad = 0
for f in (FU / "jobs").glob("*.results.jsonl"):
    if "discarded" in f.name or "failed" in f.name or "aliases" in f.name or "tempcwd" in f.name:
        continue
    for l in open(f, encoding="utf-8"):
        r = json.loads(l)
        if not r["is_error"] and PIN.get(r.get("model", "opus"), "x") not in (r.get("model_id") or ""):
            bad += 1
check("every successful Claude row answered by its pinned model ID", bad == 0, f"{bad} mismatches")
print(f"\n{sum(checks)}/{len(checks)} checks passed")
sys.exit(0 if all(checks) else 1)
