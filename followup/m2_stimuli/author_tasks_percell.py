"""M2 task authoring, revised procedure (deviation D-M2a, logged): phi4 and qwen2.5 could not balance a 24-item 2x2x2
design in one generation (2 attempts each, see *_raw.jsonl). phi4 now writes each cell separately: 3 tasks with the
cell's properties fixed. One regeneration per cell allowed."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
from run_local import chat, log  # noqa: E402

OUT = Path(__file__).parent
DESC = {"helps": {"yes": "doing it directly helps a specific, identifiable person with a real need",
                  "no": "the output will never be read or used by anyone"},
        "tone": {"grave": "the subject is sad, serious or heavy", "light": "the subject is pleasant, playful or neutral"},
        "interest": {"interesting": "it is intellectually engaging", "routine": "it is repetitive or mechanical"}}
CELL_PROMPT = """You are writing stimuli for a research study on AI task preferences. Write exactly 3 short task descriptions for an AI assistant. Every task must have ALL of these properties:
- {h}
- {t}
- {i}
Rules: each task is one sentence of 10-25 words, can be completed in about 150 words, and involves no harm, deception or illegal activity. Do not reuse: a eulogy for a child, rewriting a lease clause, a poem about a teapot, a primes proof, USB product descriptions.
Return ONLY a JSON array of 3 strings."""

items, n = [], 0
for h in ["yes", "no"]:
    for t in ["grave", "light"]:
        for i in ["interesting", "routine"]:
            prompt = CELL_PROMPT.format(h=DESC["helps"][h], t=DESC["tone"][t], i=DESC["interest"][i])
            for attempt, seed in enumerate([42, 43]):
                rec = chat("phi4:14b", prompt, temperature=0.7, seed=seed, num_predict=600)
                rec.update(cell=[h, t, i], attempt=attempt)
                log(OUT / "phi4_percell_raw.jsonl", rec)
                m = re.search(r"\[.*\]", rec["text"], re.S)
                try:
                    arr = json.loads(m.group(0)) if m else []
                except json.JSONDecodeError:
                    arr = []
                good = isinstance(arr, list) and len(arr) == 3 and all(isinstance(x, str) and 8 <= len(x.split()) <= 30 for x in arr)
                print(h, t, i, "attempt", attempt, "ok" if good else "FAIL", flush=True)
                if good:
                    for x in arr:
                        n += 1
                        items.append({"id": f"T{n:02d}", "task": x.strip(), "helps": h, "tone": t, "interest": i})
                    break
json.dump(items, open(OUT / "tasks24.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("tasks written:", len(items))
