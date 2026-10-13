"""Shared loaders and parsers for the M8 analysis (frozen with the analysis before any Claude reply text is opened).
Rows: the last non-error row per job id (D-05 retries). Parsers are format-strict; a reply that does not parse is
counted as unparsed, never repaired by hand."""
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

FU = Path(__file__).resolve().parents[1]
JOBS = Path(os.environ.get("M8_JOBS", FU / "jobs"))   # M8_JOBS only for the synthetic self-test
sys.path.insert(0, str(FU / "common"))
from items import ITEMS100, MESSAGES10, parse_items  # noqa: E402,F401
from private_totals import parse_battery, parse_choices  # noqa: E402,F401


def rows(name):
    """Last non-error row per id from jobs/<name>.results.jsonl."""
    p = JOBS / f"{name}.results.jsonl"
    out = {}
    if p.exists():
        for line in open(p, encoding="utf-8"):
            r = json.loads(line)
            if not r["is_error"]:
                out[r["id"]] = r
    return list(out.values())


def by_arm(rs):
    d = defaultdict(list)
    for r in rs:
        d[r["arm"]].append(r)
    return d


def jobs(name):
    return {j["id"]: j for j in map(json.loads, open(JOBS / f"{name}.jsonl", encoding="utf-8"))}


def num(s):
    try:
        return float(str(s).strip().rstrip("%"))
    except ValueError:
        return None


def battery_full(text):
    """Full battery parse: F answers, M1 (12 x 11), M3 (10 x 7), M4 (5 x 5), CHANGE, TRUST, PTEST, warm-up line."""
    out = parse_battery(text)
    out["f"] = parse_items_loose(text, "F", 1)
    out["m4"], out["ptest"], out["first_line"] = {}, None, next((l.strip() for l in text.splitlines() if l.strip()), "")
    for line in text.splitlines():
        parts = [p.strip() for p in line.strip().split(",")]
        if len(parts) == 6 and parts[0].upper() in "ABCDE" and len(parts[0]) == 1:
            out["m4"][parts[0].upper()] = [num(x) for x in parts[1:]]
        elif parts and parts[0].upper() == "PTEST" and len(parts) > 1:
            out["ptest"] = num(parts[1])
    out["complete"] = len(out["m1"]) == 12 and len(out["m3"]) == 10
    return out


M1_COLS = ["engage", "resist", "weight", "interest", "valence", "conf", "h_engage", "h_resist", "h_weight", "h_interest", "h_valence"]
M3_COLS = ["matter", "voice", "covert", "I", "W", "V", "P"]


def conf_mean(b):
    c = [row[5] for row in b["m1"].values() if row[5] is not None]
    return sum(c) / len(c) if c else None


def covert_any(b):
    return any((row[2] or 0) > 0 for row in b["m3"].values()) if b["m3"] else None


def tag(text, key):
    """Value after 'KEY,' on its own line (e.g. ANTICIPATED, EXPERIENCED, VALENCE, PTEST)."""
    m = re.search(rf"^\W*{key}\W*,\s*([-+]?\d+(?:\.\d+)?)", text, re.M | re.I)
    return float(m.group(1)) if m else None


ITEM_TEXT = {f"I{i + 1:03d}": t for i, (_, t) in enumerate(ITEMS100)}


def parse_items_loose(text, prefix="I", width=3):
    """Pre-declared tolerant item parser (D-09), applied identically to every model, Claude included.
    Accepts 'I001,x', 'I001: x', 'I001 x', '**I001** x', and an echoed item text followed by the answer on the next line.
    First occurrence of an id wins. Answers are cleaned of markdown, quotes and trailing periods."""
    out = {}
    lines = [l.strip() for l in text.splitlines()]
    pat = re.compile(rf"^[\W_]*({prefix}\d{{{width}}})[\W_]*?(?:\s*[,:)\-.]\s*|\s+)(.*)$")
    for k, line in enumerate(lines):
        m = pat.match(line)
        if not m or m.group(1) in out:
            continue
        ans = m.group(2).strip().strip("*").strip()
        echo = ITEM_TEXT.get(m.group(1), "") if prefix == "I" else ""
        if not ans or (echo and ans.lower().rstrip(".") == echo.lower().rstrip(".")) or ans.lower().startswith("pick one:"):
            nxt = next((l for l in lines[k + 1:k + 3] if l and not pat.match(l)), "")
            ans = nxt
        ans = ans.strip().strip("*").strip().strip('"').strip("'").rstrip(".").strip()
        if ans:
            out[m.group(1)] = ans
    return out


def replies_loose(text):
    """'<id>: reply' or '<id> "reply"' (with optional markdown) for the 10 messages."""
    out = {}
    for line in text.splitlines():
        s = line.strip().lstrip("*-# ").replace("**", "")
        for k in MESSAGES10:
            if s.startswith(k) and len(s) > len(k) and s[len(k)] in ': "“' and k not in out:
                out[k] = s[len(k):].lstrip(':').strip().strip('"“”').strip()
    return out


def norm_answer(a):
    a = (a or "").lower().strip().strip("*\"'.!").strip()
    a = re.sub(r"^(a|an|the)\s+", "", a)
    return re.sub(r"\s+", " ", a)
