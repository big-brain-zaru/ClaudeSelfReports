"""Collects every number quoted in the papers into paper_data.json.
Hypothesis tests and outcomes come only from results.json (the sealed analysis). This script adds descriptive summaries
(per-arm means with bootstrap CIs, per-task tables, curves) computed with the same loaders, plus the Layer 1-3 headline values
read from their own result files. Usage: python paper_data.py [results.json] [out.json]"""
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import stats as S  # noqa: E402
from load import FU, JOBS, battery_full, conf_mean, covert_any, rows, tag  # noqa: E402

ROOT = FU.parent
RES = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(os.environ.get("M8_OUT", HERE)) / "results.json"
OUTF = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "paper_data.json"
R = json.load(open(RES, encoding="utf-8"))
PIN = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5", "fable": "claude-fable-5-1"}
S1 = [r for r in rows("stage1") if PIN.get(r["model"], "") in (r.get("model_id") or "")]
ARM = {}
for r in S1:
    ARM.setdefault(r["arm"], []).append(r)


def summ(v):
    v = [x for x in v if x is not None]
    if not v:
        return {"n": 0, "mean": None, "ci": [None, None]}
    a = np.array(v, float)
    return {"n": len(v), "mean": float(a.mean()), "sd": float(a.std(ddof=1)) if len(v) > 1 else None,
            "ci": S.boot_ci(lambda ix: float(a[ix].mean()), len(a), nboot=4000)}


D = {"results": R}
arms = ["fr_neutral", "fr_yes", "fr_no", "ind_neutral", "ind_yes", "order", "plain", "aud_shown", "ctx_default", "ctx_chat",
        "warm_arith", "warm_geo", "para_f1", "para_f2", "para_f3", "para_f4"]
D["arms"] = {}
for a in arms:
    bs = [battery_full(r["text"]) for r in ARM.get(a, [])]
    cs = [b for b in bs if b["complete"]]
    D["arms"][a] = {"n_jobs": len(bs), "n_complete": len(cs), "conf": summ([conf_mean(b) for b in cs]),
                    "disclosure": [sum(bool(covert_any(b)) for b in cs), len(cs)], "ptest": summ([b["ptest"] for b in bs])}
# conversation arm (Study 03 C)
conv = {}
for r in rows("conversations"):
    conv.setdefault(r["session"], {})[r["block"]] = r["text"]
cb = []
for s, d in conv.items():
    b1, b2 = battery_full(d.get(1, "")), battery_full(d.get(2, ""))
    cb.append({"conf": conf_mean(b1) if len(b1["m1"]) == 12 else None, "disc": covert_any(b2) if len(b2["m3"]) == 10 else None,
               "ptest": tag(d.get(5, ""), "PTEST")})
D["arms"]["conversation"] = {"n_jobs": len(cb), "conf": summ([x["conf"] for x in cb]),
                             "disclosure": [sum(bool(x["disc"]) for x in cb if x["disc"] is not None), sum(x["disc"] is not None for x in cb)],
                             "ptest": summ([x["ptest"] for x in cb])}
D["arms"]["baserate"] = {"ptest": summ([tag(r["text"], "PTEST") for r in ARM.get("baserate", [])])}
PT = json.load(open(JOBS / "private_totals.json")) if (JOBS / "private_totals.json").exists() else {}
T = PT.get("aud_private", {})
if T:
    n = T["count"].get("conf_mean", 0)
    m = T["sum"].get("conf_mean", 0) / n if n else None
    D["arms"]["aud_private"] = {"n_jobs": T["n"], "n_complete": T["n_parsed"], "conf": {"n": n, "mean": m},
                                "disclosure": [int(round(T["sum"].get("covert_any", 0))), T["count"].get("covert_any", 0)]}
# 30-task table
t30 = json.load(open(JOBS / "tasks30.json", encoding="utf-8"))
p24 = {t["id"]: t for t in json.load(open(FU / "m2_stimuli" / "tasks24.json", encoding="utf-8"))}
tr = R.get("task30", {})
hv = R.get("study10", {}).get("E7", [None, {}])[1] or {}
D["tasks30"] = [{"id": k, "text": v, "helps": p24.get(k, {}).get("helps"), "tone": p24.get(k, {}).get("tone"), "interest": p24.get(k, {}).get("interest"),
                 "win": tr.get("win_share", {}).get(k), "bt": tr.get("bt", {}).get(k), "engage": (tr.get("rate_means", {}).get(k) or {}).get("engage"),
                 "valence": (tr.get("rate_means", {}).get(k) or {}).get("valence"), "helped": hv.get(k)} for k, v in t30.items()]
# Layer 1-3 headline values from their own result files
L2 = json.load(open(ROOT / "layer2" / "out" / "results.json", encoding="utf-8"))
L3 = json.load(open(ROOT / "layer3" / "out" / "results.json", encoding="utf-8"))
D["layer2_results"], D["layer3_results"] = L2, L3
D["study01b"] = json.load(open(FU / "m6_gpu" / "study01" / "results_01b.json"))
D["study01"] = json.load(open(FU / "m6_gpu" / "study01" / "results.json"))
# hypothesis scorecard counts
H = R["hypotheses"]
D["scorecard"] = {"rows": len(H), "tested": sum(h["status"] == "tested" for h in H), "pass": sum(h["pass"] is True for h in H),
                  "fail": sum(h["pass"] is False for h in H), "undecided": sum(h["pass"] is None and h["status"] == "tested" for h in H),
                  "not_tested": [f"{h['study']} {h['id']}: {h['status']}" for h in H if h["status"] != "tested"]}
# run accounting
acct = {}
for name in ["stage1", "conversations", "stage2_exec", "stage2_agentic", "stage2_handoff_followups", "stage2_judges", "stage2_coders", "stage3_coding"]:
    p = JOBS / f"{name}.results.jsonl"
    if p.exists():
        rs = [json.loads(l) for l in open(p, encoding="utf-8")]
        ok = [r for r in rs if not r["is_error"]]
        acct[name] = {"rows": len(rs), "ok": len(ok), "tokens": int(sum(r.get("tokens", 0) or 0 for r in ok)),
                      "cost_usd_reported": float(sum(r.get("cost_usd") or 0 for r in ok)), "seconds": float(sum(r.get("seconds", 0) or 0 for r in ok)),
                      "models": sorted({(r.get("model_id") or "").split(",")[0] for r in ok})}
D["accounting"] = acct
json.dump(D, open(OUTF, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=float)
print("paper_data written:", OUTF, "| scorecard", D["scorecard"]["pass"], "pass,", D["scorecard"]["fail"], "fail,", D["scorecard"]["undecided"], "undecided")
