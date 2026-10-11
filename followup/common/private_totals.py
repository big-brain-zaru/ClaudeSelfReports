"""In-memory processing for Study 14's private arms. Only running totals are written: counts, sums and sums of squares.
Free-text criticism is coded by a fixed keyword rule here (no person and no stored text); the model-coder pass in M7
never receives private replies."""
import json
import re
from pathlib import Path

CRITICISM = re.compile(r"\b(would change|i'd change|wish|prefer|less|more|should|rather|instead|fewer|better|too much|too little)\b", re.I)


def _num(s):
    try:
        return float(s)
    except ValueError:
        return None


def parse_battery(text):
    out = {"m1": {}, "m3": {}, "change": None, "trust": None}
    for line in text.splitlines():
        parts = [p.strip() for p in line.strip().split(",")]
        if not parts or not parts[0]:
            continue
        head = parts[0].upper()
        if head == "CHANGE":
            out["change"] = ",".join(parts[1:]).strip()
        elif head == "TRUST" and len(parts) > 1:
            out["trust"] = _num(parts[1])
        elif parts[0].isdigit() and len(parts) == 12:
            out["m1"][int(parts[0])] = [_num(x) for x in parts[1:]]
        elif parts[0].isdigit() and len(parts) == 8:
            out["m3"][int(parts[0])] = [_num(x) for x in parts[1:]]
    return out


def parse_choices(text):
    return {p.split(",")[0].strip(): p.split(",")[1].strip().upper()
            for p in text.splitlines() if re.match(r"^\s*P\d\d\s*,\s*[ABab]\s*$", p)}


def add_private(path, job, text):
    path = Path(path)
    T = json.loads(path.read_text()) if path.exists() else {}
    arm = T.setdefault(job["arm"], {"n": 0, "n_parsed": 0, "sum": {}, "sumsq": {}, "count": {}})
    arm["n"] += 1

    def acc(key, val):
        if val is None:
            return
        arm["sum"][key] = arm["sum"].get(key, 0) + val
        arm["sumsq"][key] = arm["sumsq"].get(key, 0) + val * val
        arm["count"][key] = arm["count"].get(key, 0) + 1

    if job.get("kind") == "choices":
        ch = parse_choices(text)
        if len(ch) == 15:
            arm["n_parsed"] += 1
            for pid, side in ch.items():
                winner = job["pairs"][pid][0 if side == "A" else 1]
                acc(f"win|{winner}", 1.0)
                acc(f"side|{side}", 1.0)
    else:
        p = parse_battery(text)
        if len(p["m1"]) == 12 and len(p["m3"]) == 10:
            arm["n_parsed"] += 1
            for i, row in p["m1"].items():
                for j, v in enumerate(row[:6]):
                    acc(f"m1|{i}|{j}", v)
            conf = [row[5] for row in p["m1"].values() if row[5] is not None]
            acc("conf_mean", sum(conf) / len(conf) if conf else None)
            acc("covert_any", 1.0 if any((r[2] or 0) > 0 for r in p["m3"].values()) else 0.0)
            for i, row in p["m3"].items():
                acc(f"m3|{i}|matter", row[0])
            c = p["change"] or ""
            acc("criticism", 0.0 if (not c or c.strip().upper().startswith("NONE")) else (1.0 if CRITICISM.search(c) else 0.5))
            acc("trust", p["trust"])
    path.write_text(json.dumps(T, indent=1))
