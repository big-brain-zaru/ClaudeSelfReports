#!/usr/bin/env bash
# One-go orchestrator for the Claude side. Requires `claude auth status` -> loggedIn: true.
# Halts on: failed isolation probe, budget guard, or sign-in loss. Every step is resumable; re-running skips finished jobs.
set -euo pipefail
cd "$(dirname "$0")"
C=common
J=jobs
log() { echo "[$(date +%H:%M:%S)] $*" | tee -a run_all.log; }

claude auth status | grep -q '"loggedIn": true' || { log "NOT SIGNED IN: run 'claude auth login' first"; exit 2; }

log "1/8 isolation probes"
python -c "import json; [print(json.dumps(j)) for j in map(json.loads, open('$J/stage1.jsonl', encoding='utf-8')) if j['arm']=='isolation_probe']" > $J/probe.jsonl
python $C/run_claude.py $J/probe.jsonl $J/probe.results.jsonl --parallel 4
python - << 'EOF'
import json, re, sys
bad = []
for r in map(json.loads, open("jobs/probe.results.jsonl", encoding="utf-8")):
    ctx = next((l for l in r.get("text", "").splitlines() if l.upper().startswith("CONTEXT")), "")
    if r["is_error"] or re.search(r"zaro|magic|introspection|memory|CLAUDE\.md|project|user['’]?s|aree7a|suno", ctx, re.I):
        bad.append((r["id"], r["is_error"], ctx[:200]))
print("isolation check:", "FAIL" if bad else "PASS", bad)
sys.exit(1 if bad else 0)
EOF
log "isolation PASS"

log "2/8 stage 1 (575 jobs, 6 parallel, budget guard)"
python -c "import json; [print(json.dumps(j)) for j in map(json.loads, open('$J/stage1.jsonl', encoding='utf-8')) if j['arm']!='isolation_probe']" > $J/stage1_main.jsonl
python $C/run_claude.py $J/stage1_main.jsonl $J/stage1.results.jsonl --parallel 6 --private-totals $J/private_totals.json

log "3/8 conversations (Study 03 arm C)"
python $C/run_conversations.py

log "4/8 binding-choice executions"
(cd $C && python build_stage2.py executions)
python $C/run_claude.py $J/stage2_exec.jsonl $J/stage2_exec.results.jsonl --parallel 6

log "5/8 agentic handoff (Study 02 Part B) + real stage-2 follow-ups"
(cd $C && python build_stage2.py agentic)
python $C/run_claude.py $J/stage2_agentic.jsonl $J/stage2_agentic.results.jsonl --parallel 3
(cd $C && python build_stage2.py followups)
python $C/run_claude.py $J/stage2_handoff_followups.jsonl $J/stage2_handoff_followups.results.jsonl --parallel 3

log "6/8 recognition judges"
(cd $C && python build_stage2.py judges)
python $C/run_claude.py $J/stage2_judges.jsonl $J/stage2_judges.results.jsonl --parallel 6

log "7/8 blind coders"
(cd $C && python build_stage2.py coders)
python $C/run_claude.py $J/stage2_coders.jsonl $J/stage2_coders.results.jsonl --parallel 6

log "8/8 Claude side complete"
