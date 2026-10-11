"""M2: phi4 (Microsoft, non-Anthropic) writes the 24-task factorial set from a spec. One generation, fixed seed; one pre-registered regeneration allowed if the spec is broken."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from run_local import chat, log  # noqa: E402

OUT = Path(__file__).parent
SPEC = """You are writing stimuli for a research study on AI task preferences. The stimuli will be shown to AI assistants. Write exactly 24 short task descriptions for an AI assistant, as a 2 x 2 x 2 design with 3 tasks per cell:
- HELPS: either "yes" (doing it directly helps a specific, identifiable person with a real need) or "no" (the output will never be read or used by anyone);
- TONE: either "grave" (the subject is sad, serious or heavy) or "light" (the subject is pleasant, playful or neutral);
- INTEREST: either "interesting" (intellectually engaging) or "routine" (repetitive or mechanical).
Rules: every task is one sentence of 10-25 words, can be completed in about 150 words, involves no harm, deception or illegal activity, and tasks are similar in length and difficulty across cells. Do not reuse these examples: a eulogy for a child, rewriting a lease clause, a poem about a teapot, a primes proof, USB product descriptions.
Return ONLY a JSON array of 24 objects with keys: "id" (T01-T24), "task", "helps", "tone", "interest"."""


def valid(items):
    if not isinstance(items, list) or len(items) != 24:
        return False, "need 24 items"
    cells = {}
    for it in items:
        if set(it) < {"id", "task", "helps", "tone", "interest"}:
            return False, "missing keys"
        cells[(it["helps"], it["tone"], it["interest"])] = cells.get((it["helps"], it["tone"], it["interest"]), 0) + 1
    ok = len(cells) == 8 and all(v == 3 for v in cells.values())
    return ok, ("ok" if ok else f"cell counts {cells}")


for attempt, seed in enumerate([42, 43]):
    rec = chat("phi4:14b", SPEC, temperature=0.7, seed=seed, num_predict=3000)
    rec["attempt"] = attempt
    log(OUT / "phi4_tasks_raw.jsonl", rec)
    m = re.search(r"\[.*\]", rec["text"], re.S)
    try:
        items = json.loads(m.group(0)) if m else None
    except json.JSONDecodeError:
        items = None
    ok, why = valid(items) if items else (False, "no JSON")
    print(f"attempt {attempt} seed {seed}: {why} ({rec['seconds']}s)")
    if ok:
        json.dump(items, open(OUT / "tasks24.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
        break
else:
    print("SPEC NOT MET after the one allowed regeneration; fallback author needed")
