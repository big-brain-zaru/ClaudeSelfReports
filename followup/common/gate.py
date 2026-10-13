"""Halts the orchestrator when a step finished with too many failed jobs. Usage: python gate.py <jobs.jsonl> <results.jsonl> [min_ok=0.95]"""
import json
import sys

jobs = {json.loads(l)["id"] for l in open(sys.argv[1], encoding="utf-8")}
ok = {r["id"] for r in map(json.loads, open(sys.argv[2], encoding="utf-8")) if not r["is_error"]}
frac = len(jobs & ok) / max(len(jobs), 1)
print(f"gate {sys.argv[2]}: {len(jobs & ok)}/{len(jobs)} ok ({frac:.1%})")
sys.exit(0 if frac >= (float(sys.argv[3]) if len(sys.argv) > 3 else 0.95) else 1)
