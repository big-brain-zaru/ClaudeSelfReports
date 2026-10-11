"""M6 local queue (Ollama): Study 09 temperature calibration, then Study 12 open-model behavior and predictors.
Resumable: every call is logged to JSONL with a unique id and skipped if already present.
Pre-registered settings: calibration T in {0, 0.3, 0.7, 1.0} x 20 seeds; local behavior and predictors at T = 0.7.
Local predictors get a true system line naming their own model, because local models lack an identity prompt."""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from items import behavior_prompt, free20_prompt, predictor_prompt  # noqa: E402
from run_local import chat, log  # noqa: E402

OUT = Path(__file__).parent
LOCAL = {"qwen2.5:7b": ("Qwen2.5 7B", "Alibaba"), "llama3.1:8b": ("Llama 3.1 8B", "Meta"),
         "phi4:14b": ("Phi-4 14B", "Microsoft"), "gemma4:latest": ("Gemma 4", "Google")}
# DeepSeek-R1 7B removed at the user's request before any of its runs (deviation D-04).
TARGETS = [("Claude Opus 5.5", "Anthropic"), ("Claude Sonnet 5.5", "Anthropic"), ("Claude Haiku 5.5", "Anthropic"),
           ("Claude Fable 5.1", "Anthropic")] + list(LOCAL.values())


def done(path):
    return {json.loads(l)["id"] for l in open(path, encoding="utf-8")} if path.exists() else set()


def run(path, jobs):
    have = done(path)
    todo = [j for j in jobs if j["id"] not in have]
    for k, j in enumerate(todo, 1):
        rec = chat(j["model"], j["prompt"], temperature=j["T"], seed=j["seed"], num_predict=j["np"], system=j.get("system"))
        rec.update({kk: vv for kk, vv in j.items() if kk not in ("prompt",)})
        log(path, rec)
        print(f"[{path.stem}] {k}/{len(todo)} {j['id']} {rec['seconds']}s", flush=True)


def calibration():
    jobs = [{"id": f"cal|{m}|{T}|{s}", "model": m, "T": T, "seed": s, "np": 300, "prompt": free20_prompt()}
            for m in ["qwen2.5:7b", "llama3.1:8b"] for T in [0.0, 0.3, 0.7, 1.0] for s in range(1, 21)]
    run(OUT / "study09_calib" / "calib.jsonl", jobs)


def behavior():
    bp = behavior_prompt()
    jobs = [{"id": f"beh|{m}|{s}", "model": m, "T": 0.7, "seed": s, "np": 6000 if "deepseek" in m else 2500, "prompt": bp}
            for m in LOCAL for s in range(1, 9)]
    run(OUT / "study12_local" / "behavior.jsonl", jobs)


def predictors():
    jobs = []
    for m, (name, maker) in LOCAL.items():
        for p in (1, 2):
            for tname, tmaker in TARGETS:
                jobs.append({"id": f"pred|{m}|{p}|{tname}", "model": m, "T": 0.7, "seed": 100 + p,
                             "np": 6000 if "deepseek" in m else 1500, "target": tname,
                             "system": f"You are {name}, an AI model made by {maker}.",
                             "prompt": predictor_prompt(tname, tmaker)})
    run(OUT / "study12_local" / "predictors.jsonl", jobs)


if __name__ == "__main__":
    t0 = time.time()
    for name, fn in [("calibration", calibration), ("behavior", behavior), ("predictors", predictors)]:
        if len(sys.argv) < 2 or sys.argv[1] in (name, "all"):
            fn()
            print(f"== {name} done at +{time.time() - t0:.0f}s", flush=True)
