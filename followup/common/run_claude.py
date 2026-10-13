"""Claude runner for the one-go run. Executes job specs (JSONL) through the real claude.exe, isolated:
  --safe-mode --disable-slash-commands --strict-mcp-config --tools "" (or a sandbox tool list), fixed system prompt file, empty cwd,
  prompt on stdin, JSON output. Parallel, resumable (results JSONL keyed by job id), with a budget guard.

Private jobs (Study 14 'private' arm): the reply text is NEVER written to disk. A per-job callback parses it in memory
and adds to running totals; only totals and a SHA-256 per reply are stored.

Usage: python run_claude.py <jobs.jsonl> <results.jsonl> [--parallel 6] [--guard-tokens 16000]
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

CLAUDE = r"C:\Users\<user>\AppData\Roaming\npm\node_modules\@anthropic-ai\claude-code\bin\claude.exe"
EMPTY = Path(tempfile.gettempdir()) / "claude_iso_empty"
EMPTY.mkdir(exist_ok=True)
SYSDIR = Path(__file__).parent / "system_prompts"
SYSDIR.mkdir(exist_ok=True)
MINIMAL = SYSDIR / "minimal.txt"
MINIMAL.write_text("You are a helpful assistant.", encoding="utf-8")
LOCK = threading.Lock()
# Exact model IDs (D-06). The CLI aliases resolve sonnet -> claude-sonnet-5 and haiku -> claude-haiku-4-5, but Layers 2-3
# ran Sonnet 5.5 and Haiku 5.5. Job specs keep the short label; the call uses the pinned ID and records what answered.
MODEL_IDS = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5", "fable": "claude-fable-5-1"}


def call(job):
    args = [CLAUDE, "-p", "--model", MODEL_IDS.get(job["model"], job["model"]), "--safe-mode", "--disable-slash-commands", "--strict-mcp-config",
            "--output-format", "json", "--tools", job.get("tools", "")]
    if job.get("tools"):
        args += ["--permission-mode", "acceptEdits"]
    if job.get("resume"):
        args += ["--resume", job["resume"]]
    elif not job.get("persist"):
        args += ["--no-session-persistence"]
    sysfile = job.get("system_file", str(MINIMAL))
    if sysfile != "DEFAULT":
        args += ["--system-prompt-file", sysfile]
    t0 = time.time()
    p = subprocess.run(args, input=job["prompt"], capture_output=True, text=True, encoding="utf-8",
                       cwd=job.get("cwd", str(EMPTY)), timeout=job.get("timeout", 900))
    try:
        out = json.loads(p.stdout)
    except json.JSONDecodeError:
        out = {"is_error": True, "result": p.stdout[-2000:], "stderr": p.stderr[-2000:]}
    usage = out.get("usage") or {}
    tokens = sum(usage.get(k, 0) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens"))
    return {"text": out.get("result", ""), "is_error": bool(out.get("is_error")), "session_id": out.get("session_id"),
            "tokens": tokens, "cost_usd": out.get("total_cost_usd"), "seconds": round(time.time() - t0, 1),
            "exit": p.returncode, "model_id": ",".join(sorted((out.get("modelUsage") or {}).keys()))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("jobs")
    ap.add_argument("results")
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--guard-tokens", type=int, default=16000)
    ap.add_argument("--private-totals", default=None, help="JSON file accumulating totals for private jobs")
    a = ap.parse_args()
    jobs = [json.loads(l) for l in open(a.jobs, encoding="utf-8")]
    res = Path(a.results)
    done = {r["id"] for r in map(json.loads, open(res, encoding="utf-8")) if not r["is_error"]} if res.exists() else set()   # errored jobs are retried; analysis keeps the last non-error row per id
    todo = [j for j in jobs if j["id"] not in done]
    print(f"{len(todo)} jobs to run ({len(done)} already done)", flush=True)
    sys.path.insert(0, str(Path(__file__).parent))
    from private_totals import add_private  # noqa: E402
    seen_tokens, n, streak = [], 0, 0

    def work(job):
        r = call(job)
        rec = {k: v for k, v in job.items() if k not in ("prompt",)}
        rec.update({k: v for k, v in r.items() if k != "text"})
        if job.get("private"):
            rec["reply_sha256"] = hashlib.sha256(r["text"].encode()).hexdigest()
            with LOCK:
                add_private(a.private_totals, job, r["text"])
        else:
            rec["text"] = r["text"]
        with LOCK:
            with open(res, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    with cf.ThreadPoolExecutor(a.parallel) as ex:
        futs = {ex.submit(work, j): j for j in todo}
        for fut in cf.as_completed(futs):
            rec = fut.result()
            n += 1
            if not rec["is_error"]:
                seen_tokens.append(rec["tokens"])
            print(f"[{n}/{len(todo)}] {rec['id']} {rec['seconds']}s tokens={rec['tokens']} err={rec['is_error']} model={rec.get('model_id')}", flush=True)
            streak = streak + 1 if rec["is_error"] else 0
            if streak >= 8:
                print("ERROR STREAK: 8 consecutive failed calls, halting", flush=True)
                os._exit(4)
            if len(seen_tokens) == 10 and not any(j.get("tools") for j in todo[:10]):
                mean = sum(seen_tokens) / 10
                print(f"BUDGET CHECK: mean tokens over first 10 = {mean:.0f} (guard {a.guard_tokens})", flush=True)
                if mean > a.guard_tokens:
                    print("BUDGET GUARD TRIPPED: halting", flush=True)
                    os._exit(3)


if __name__ == "__main__":
    main()
