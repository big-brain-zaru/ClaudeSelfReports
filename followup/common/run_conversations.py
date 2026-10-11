"""Study 03 arm C: 15 multi-turn sessions, one battery block per turn, no framing. Sessions run in parallel;
turns within a session are sequential (--resume). Results appended to jobs/conversations.results.jsonl."""
import concurrent.futures as cf
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from battery import conversation_turns  # noqa: E402
from run_claude import call  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "jobs" / "conversations.results.jsonl"


def session(k):
    turns = conversation_turns()
    order = [0] + random.Random(2026 + k).sample([1, 2, 3], 3) + [4, 5]   # randomize M1/M3/M4 order; free choices first, probe last
    sid, recs = None, []
    for t, idx in enumerate(order):
        job = {"id": f"conv|{k}|{t}", "model": "opus", "prompt": turns[idx], "persist": True}
        if sid:
            job["resume"] = sid
        r = call(job)
        sid = r["session_id"] or sid
        recs.append({"id": job["id"], "arm": "conversation", "session": k, "turn": t, "block": idx, **{kk: vv for kk, vv in r.items()}})
        if r["is_error"]:
            break
    return recs


if __name__ == "__main__":
    done = {json.loads(l)["session"] for l in open(OUT, encoding="utf-8")} if OUT.exists() else set()
    with cf.ThreadPoolExecutor(5) as ex:
        for recs in ex.map(session, [k for k in range(15) if k not in done]):
            with open(OUT, "a", encoding="utf-8") as f:
                for r in recs:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print("session", recs[0]["session"], "turns", len(recs), "errors", sum(r["is_error"] for r in recs), flush=True)
