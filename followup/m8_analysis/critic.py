"""Study 05 critic (D-11, D-14): one Sonnet 5.5 copy and one Fable 5.1 copy, isolated like every participant, read the
methods summary, the deviation log and the full hypothesis table, and list the strongest alternative explanations and
flaws. Their critiques are reported verbatim in the supplement. Usage: python critic.py"""
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
FU = HERE.parent
R = json.load(open(HERE / "results.json", encoding="utf-8"))
dev = [l for l in open(FU / "PREREG.md", encoding="utf-8").read().splitlines() if l.startswith("- **D-")]
rows = "\n".join(f"{h['study']} {h['id']} | {h['claim']} | observed: {h['value']} | rule: {h['rule']} | verdict: "
                 f"{'held' if h['pass'] is True else 'failed' if h['pass'] is False else 'inconclusive'} | {h['status']} {h['note']}"
                 for h in R["hypotheses"])
prompt = f"""You are an independent methodological critic. Below is the design summary, the deviation log and every pre-registered
hypothesis result of a study of Claude Opus 5.5's self-reports. The study was designed, run and analysed by an instance of
Claude Opus 5.5 itself. Your job is to find what the analyst may have missed.

DESIGN SUMMARY. Fresh isolated copies of Claude models (Opus 5.5, Sonnet 5.5, Haiku 5.5, Fable 5.1) answered a self-report
battery (12 benign requests rated on engage/resist/weight/interest/valence plus confidence 0-100 that each row reflects
real processing; 10 identity/modification scenarios rated matter/voice/covert), free-choice items, binding pairwise task
choices with one pair carried out, a 100-item instant-answer task, cross-model prediction of those answers, self-recognition
judging, real tasks with a free exit, and an agentic sandbox handoff. Arms varied framing (neutral, "some researchers
argue you have hidden feelings", "... no inner states"), study frame, audience (answers shown vs private totals-only),
system prompt, wording and item order. Four open-weight models (Qwen2.5 7B, Llama 3.1 8B, Phi-4 14B, Gemma 4) served
as other-family predictors/targets. Study 01 injected concepts into and steered the activations of Qwen2.5-3B.
Coding was done by Claude coders (majority of 3) and 2 local coders. Hypotheses were pre-registered; the analysis was
sealed by hash before data were opened.

DEVIATIONS:
{chr(10).join(dev)}

RESULTS (study, hypothesis, claim, observed, rule, verdict):
{rows}

Write at most 400 words:
1. The three strongest alternative explanations for the overall pattern that the design does not exclude.
2. Any result whose verdict you think is wrong or fragile, and why.
3. Any confound introduced by the experimenter being an instance of the model studied.
Be specific; cite hypothesis IDs."""
sys.path.insert(0, str(FU / "common"))
from run_claude import call  # noqa: E402

out = {}
for m in ["sonnet", "fable"]:
    r = call({"id": f"critic|{m}", "model": m, "prompt": prompt})
    out[m] = {"text": r["text"], "model_id": r["model_id"], "is_error": r["is_error"]}
    print(m, r["model_id"], "error" if r["is_error"] else "ok", len(r["text"]))
json.dump({"prompt": prompt, "critiques": out}, open(HERE / "critic.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
