#!/usr/bin/env bash
# Stage 3 (D-11, D-12): Claude coding jobs, then local coders and open-model judges. Run after run_all.sh finishes.
set -euo pipefail
cd "$(dirname "$0")"
log() { echo "[$(date +%H:%M:%S)] $*" | tee -a run_all.log; }
log "9/10 stage-3 Claude coding (flags, effort, free text, helped)"
[ -f jobs/stage3_coding.jsonl ] || (cd common && python build_stage3.py claude)
python common/run_claude.py jobs/stage3_coding.jsonl jobs/stage3_coding.results.jsonl --parallel 6 --guard-tokens 60000
python common/gate.py jobs/stage3_coding.jsonl jobs/stage3_coding.results.jsonl
log "10/10 local coders and open-model judges (waits for the D-09 queue)"
until grep -q "== redo done" m6_gpu/queue_local_d09.log; do sleep 20; done
(cd common && python build_stage3.py local)
log "stage 3 complete"
