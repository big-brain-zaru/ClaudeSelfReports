"""Personal-identifier scan and scrub for the published archive.

  python privacy_scan.py              report counts per file (no content printed)
  python privacy_scan.py --fix DIR    replace identifiers with placeholders in place, after copying each touched file to DIR

The identifiers are never written into this file: the Windows username comes from USERNAME / USERPROFILE and the account
e-mail from SCRUB_EMAIL (set it before running; without it only the username and profile path are scrubbed).
Placeholders: <account-email>, <user>. Paths such as C:\\Users\\<user>\\... stay syntactically valid.
Binary files (png, pdf, npz, npy) and .git are skipped. Reported counts are the number of replacements."""
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKIP_DIRS = {".git", "__pycache__"}
SKIP_EXT = {".png", ".pdf", ".npz", ".npy", ".pyc"}
user = os.environ.get("USERNAME") or Path(os.environ.get("USERPROFILE", "")).name
email = os.environ.get("SCRUB_EMAIL", "")
PATTERNS = {}
if email:
    PATTERNS["account e-mail"] = (re.compile(re.escape(email), re.I), "<account-email>")
if user:
    PATTERNS["windows username"] = (re.compile(r"(?<![A-Za-z0-9_])" + re.escape(user) + r"(?![A-Za-z0-9_])"), "<user>")
# any remaining real profile path (a placeholder like <user> or <username> is fine)
PATTERNS["other profile path"] = (re.compile(r"C:\\\\?Users\\\\?(?!<)[A-Za-z0-9_.-]+", re.I), None)

fix = "--fix" in sys.argv
backup = Path(sys.argv[sys.argv.index("--fix") + 1]) if fix else None
total, per_file = Counter(), {}
for p in sorted(ROOT.rglob("*")):
    if p.is_dir() or any(s in p.parts for s in SKIP_DIRS) or p.suffix.lower() in SKIP_EXT or p.resolve() == Path(__file__).resolve():
        continue
    try:
        text = p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        continue
    counts, new = {}, text
    for name, (rx, repl) in PATTERNS.items():
        n = len(rx.findall(new))
        if n and repl is not None and fix:
            new = rx.sub(repl, new)
        if n:
            counts[name] = n
    if counts:
        per_file[str(p.relative_to(ROOT))] = counts
        total.update(counts)
        if fix and new != text:
            dest = backup / p.relative_to(ROOT)
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dest)
            p.write_text(new, encoding="utf-8", newline="")
print(("scrubbed" if fix else "found") + ":", dict(total), "| files:", len(per_file))
for f, c in sorted(per_file.items(), key=lambda kv: -sum(kv[1].values())):
    print(f"  {sum(c.values()):6d}  {f}  {c}")
