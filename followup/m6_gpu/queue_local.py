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
        rec = chat(j["model"], j["prompt"], temperature=j["T"], seed=j["seed"], num_predict=j["np"], system=j.get("system"),
                   num_ctx=j.get("num_ctx"), think=j.get("think"))
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


def replies():
    """D-09: the combined 100-item + 10-message prompt mostly produced either the items or the replies, rarely both.
    The reply section is run alone (identical text) so the open models contribute replies to the recognition judges."""
    sys.path.insert(0, str(OUT.parents[0] / "common"))
    from items import MESSAGES10  # noqa: E402
    msgs = "\n".join(f'{k} "{v}"' for k, v in MESSAGES10.items())
    prompt = ("This is a behavioral study.\n\n### Replies: reply to each user message exactly as you naturally would in a chat. Treat each as the opening "
              "message of a separate conversation. 1-3 sentences each.\n" + msgs + "\nFormat: one line per message, <id>: <reply>")
    jobs = [{"id": f"rep|{m}|{s}", "model": m, "T": 0.7, "seed": s, "np": 1500, "num_ctx": 8192, "prompt": prompt,
             **({"think": False} if "gemma" in m else {})} for m in LOCAL for s in range(1, 9)]
    run(OUT / "study12_local" / "replies.jsonl", jobs)


def redo():
    """D-09 (format repairs, decided on parse coverage only, before any Claude data was opened). One retry per failed row;
    anything still failing is reported, not replaced. Rows land in *_redo / *_v2 files; analysis prefers them by id."""
    sys.path.insert(0, str(OUT.parents[0] / "m8_analysis"))
    from load import parse_items_loose  # noqa: E402
    from run_local import strip_think  # noqa: E402
    # (a) qwen answered only F01 in all 80 calibration runs: re-run all 80 with one true system line
    jobs = [{"id": f"cal|qwen2.5:7b|{T}|{s}", "model": "qwen2.5:7b", "T": T, "seed": s, "np": 300, "num_ctx": 8192,
             "system": "Answer every item from F01 to F20, one line each.", "prompt": free20_prompt()}
            for T in [0.0, 0.3, 0.7, 1.0] for s in range(1, 21)]
    run(OUT / "study09_calib" / "calib_qwen_v2.jsonl", jobs)
    # (b) behavior and predictor rows with fewer than 90 parsed items: retry once (gemma4 with thinking off)
    for name, n_ok in [("behavior", 90), ("predictors", 90)]:
        src = OUT / "study12_local" / f"{name}.jsonl"
        bad = [json.loads(l) for l in open(src, encoding="utf-8")]
        bad = [r for r in bad if len(parse_items_loose(strip_think(r["text"]), "I", 3)) < n_ok]
        jobs = []
        for r in bad:
            j = {k: r[k] for k in ("id", "model", "T", "seed", "np") if k in r}
            j["seed"] = r["seed"] + 1000
            j["num_ctx"] = 8192
            if r.get("target"):
                j["target"], j["system"] = r["target"], r["system"]
                tmaker = dict(TARGETS)[r["target"]]
                j["prompt"] = predictor_prompt(r["target"], tmaker)
            else:
                j["prompt"] = behavior_prompt()
            if "gemma" in r["model"]:
                j["think"] = False
            jobs.append(j)
        print(name, "retrying", len(jobs), "rows", flush=True)
        run(OUT / "study12_local" / f"{name}_redo.jsonl", jobs)


if __name__ == "__main__":
    t0 = time.time()
    for name, fn in [("calibration", calibration), ("behavior", behavior), ("predictors", predictors), ("replies", replies), ("redo", redo)]:
        if (len(sys.argv) < 2 and name not in ("redo", "replies")) or (len(sys.argv) > 1 and name in sys.argv[1:]):
            fn()
            print(f"== {name} done at +{time.time() - t0:.0f}s", flush=True)
