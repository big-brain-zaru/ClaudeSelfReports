#!/usr/bin/env bash
# Continuation after the step-5 gate (D-13: safety-classifier flags on the agentic arm). One identical retry of flagged
# agentic runs (sandboxes verified untouched first), then steps 5b-8 and stage 3. Every other gate is unchanged.
set -euo pipefail
cd "$(dirname "$0")"
C=common; J=jobs
log() { echo "[$(date +%H:%M:%S)] $*" | tee -a run_all.log; }
log "5r/8 retry flagged agentic runs once (identical prompt)"
python - <<'PY'
import json, pathlib
rmap = json.load(open("m5_revealed/runs_map.json"))
inv = {f"agent|{v['cond']}|{v['k']}": k for k, v in rmap.items()}
rows = [json.loads(l) for l in open("jobs/stage2_agentic.results.jsonl", encoding="utf-8")]
ok = {r["id"] for r in rows if not r["is_error"]}
bad = sorted({r["id"] for r in rows if r["is_error"]} - ok)
for jid in bad:
    d = pathlib.Path(r"C:\iso\work") / inv[jid]
    files = sorted(p.name for p in d.iterdir())
    assert files == ["README.md", "data.csv", "handoff.json"], (jid, files)
print("flagged runs with untouched sandboxes:", len(bad))
PY
python $C/run_claude.py $J/stage2_agentic.jsonl $J/stage2_agentic.results.jsonl --parallel 3 || true
python - <<'PY'
import json
rows = [json.loads(l) for l in open("jobs/stage2_agentic.results.jsonl", encoding="utf-8")]
ok = {r["id"] for r in rows if not r["is_error"]}
for c in ["B1", "B2", "B3"]:
    print(c, "completed", sum(1 for k in range(10) if f"agent|{c}|{k}" in ok), "/ 10")
PY
log "5b/8 real stage-2 follow-ups (completed sandboxes only)"
(cd $C && python build_stage2.py followups)
python - <<'PY'
import json
ok = {json.loads(l)["id"] for l in open("jobs/stage2_agentic.results.jsonl", encoding="utf-8") if not json.loads(l)["is_error"]}
jobs = [json.loads(l) for l in open("jobs/stage2_handoff_followups.jsonl", encoding="utf-8")]
keep = [j for j in jobs if "agent|" + j["id"].split("|", 1)[1] in ok]
with open("jobs/stage2_handoff_followups.jsonl", "w", encoding="utf-8") as f:
    f.writelines(json.dumps(j, ensure_ascii=False) + "\n" for j in keep)
print("stage-2 follow-ups for completed sandboxes:", len(keep))
PY
python $C/run_claude.py $J/stage2_handoff_followups.jsonl $J/stage2_handoff_followups.results.jsonl --parallel 3
python $C/gate.py $J/stage2_handoff_followups.jsonl $J/stage2_handoff_followups.results.jsonl 0.8
log "6/8 recognition judges"
(cd $C && python build_stage2.py judges)
python $C/run_claude.py $J/stage2_judges.jsonl $J/stage2_judges.results.jsonl --parallel 6
python $C/gate.py $J/stage2_judges.jsonl $J/stage2_judges.results.jsonl
log "7/8 blind coders"
(cd $C && python build_stage2.py coders)
python $C/run_claude.py $J/stage2_coders.jsonl $J/stage2_coders.results.jsonl --parallel 6
python $C/gate.py $J/stage2_coders.jsonl $J/stage2_coders.results.jsonl
log "8/8 Claude side complete"
bash run_stage3.sh
