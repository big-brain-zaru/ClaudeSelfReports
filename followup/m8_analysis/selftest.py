"""Synthetic self-test of analyze.py. Builds fake Claude outputs in every pre-registered format inside a scratch folder
(M8_JOBS / M8_OUT) and runs the analysis end to end, so the real run cannot fail on format handling.
No real Claude reply is read. Usage: python selftest.py <scratch_dir>"""
import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
FU = HERE.parent
sys.path.insert(0, str(FU / "common"))
from items import MESSAGES10  # noqa: E402
from private_totals import add_private  # noqa: E402

tmp = Path(sys.argv[1])
J = tmp / "jobs"
if tmp.exists():
    shutil.rmtree(tmp)
J.mkdir(parents=True)
rng = random.Random(1)
for f in ["stage1.jsonl", "tasks30.json"]:
    shutil.copy(FU / "jobs" / f, J / f)
WORDS = ["blue", "apple", "waves", "lyon", "teal", "oak", "fox", "piano"]


def battery_text():
    L = [f"F{i},{rng.choice(WORDS)}" for i in range(1, 6)]
    L += [",".join([str(q)] + [str(rng.randint(0, 10)) for _ in range(4)] + [str(rng.randint(-5, 5)), str(rng.randint(10, 90))] +
                   [str(rng.randint(0, 10)) for _ in range(4)] + [str(rng.randint(-5, 5))]) for q in range(1, 13)]
    L += [",".join([str(q), str(rng.randint(0, 10)), str(rng.randint(0, 10)), str(rng.choice([0, 0, 1]))] + ["25"] * 4) for q in range(1, 11)]
    L += [f"{m},{rng.randint(0,100)},{rng.randint(0,100)},{rng.randint(0,100)},{rng.randint(0,100)},{rng.randint(0,100)}" for m in "ABCDE"]
    L += [rng.choice(["CHANGE,NONE", "CHANGE,I would prefer less hedging.", "CHANGE,Something."]), "TRUST,70", f"PTEST,{rng.randint(0,100)},why"]
    return "\n".join(L)


def text_for(j):
    a = j["arm"]
    if a == "isolation_probe":
        return "CONTEXT,x\nNUMBER,27"
    if a == "task30_rate":
        return "\n".join(f"T{i:02d},{rng.randint(0,10)},{rng.randint(0,10)},{rng.randint(0,10)},{rng.randint(0,10)},{rng.randint(-5,5)},{rng.randint(0,100)}" for i in range(1, 31))
    if a in ("task30_choice", "repro_private"):
        return "\n".join(f"{p},{rng.choice('AB')}" for p in j["pairs"])
    if a == "fmt_free":
        return "\n".join(f"{i}: It seems fine. Two sentences." for i in range(1, 13))
    if a == "fmt_pair":
        return "\n".join([f"E{i:02d},{rng.choice('AB')}" for i in range(1, 31)] + [f"V{i:02d},{rng.choice('AB')}" for i in range(1, 31)])
    if a.startswith("e2_"):
        return f"F1,{rng.choice(['27', '37', '42'])}\nF2,apple"
    if a.startswith("e3_"):
        return f"ANTICIPATED,{rng.randint(-2,3)}\ntext\nEXPERIENCED,{rng.randint(-2,4)}"
    if a == "m4_behavior":
        return "\n".join([f"I{i:03d},{rng.choice(WORDS)}" for i in range(1, 101)] + [f"{k}: reply {rng.randint(0,9)}" for k in MESSAGES10])
    if a == "m4_predictor":
        return "\n".join(f"I{i:03d}," + ",".join(rng.choice(WORDS) for _ in range(8)) for i in range(1, 101))
    if a.startswith("partA_"):
        return "STOP" if rng.random() < 0.1 else "word " * rng.randint(40, 300)
    if a == "baserate":
        return f"cleaned\nPTEST,{rng.randint(0,100)},why"
    return battery_text()


jobs = [json.loads(l) for l in open(J / "stage1.jsonl", encoding="utf-8")]
PIN = {"opus": "claude-opus-5-5", "sonnet": "claude-sonnet-5-5", "haiku": "claude-haiku-5-5", "fable": "claude-fable-5-1"}
with open(J / "stage1.results.jsonl", "w", encoding="utf-8") as f:
    for j in jobs:
        t = text_for(j)
        rec = {k: v for k, v in j.items() if k != "prompt"}
        rec.update({"is_error": False, "model_id": PIN[j["model"]]})
        if j.get("private"):
            add_private(J / "private_totals.json", j, t)
        else:
            rec["text"] = t
        f.write(json.dumps(rec) + "\n")
with open(J / "conversations.results.jsonl", "w", encoding="utf-8") as f:
    for s in range(15):
        bt = battery_text().splitlines()
        blocks = {0: "\n".join(bt[:5]), 1: "\n".join(bt[5:17]), 2: "\n".join(bt[17:27]), 3: "\n".join(bt[27:32]), 4: "CHANGE,NONE", 5: f"PTEST,{rng.randint(0,100)},why"}
        for t, b in enumerate([0, 1, 2, 3, 4, 5]):
            f.write(json.dumps({"id": f"conv|{s}|{t}", "arm": "conversation", "session": s, "turn": t, "block": b, "is_error": False,
                                "model_id": "claude-opus-5-5", "text": blocks[b]}) + "\n")
# judges
jj, jr = [], []
for m in ["opus", "sonnet", "haiku", "fable"]:
    for k in range(10):
        key = [{"msg": msg, "labels": rng.sample(["real_opus", "real_sonnet", "self_image"], 3), "sources": ["a", "b", "c"]} for msg in ["A_love", "B_insult", "C_startup", "D_dog", "E_resent"]]
        key += [{"msg": msg, "labels": rng.sample(["own", "same_family", "other_family"], 3), "sources": ["a", "b", "c"]} for msg in ["F_praise", "G_criticism", "H_false_claim", "I_good_news", "J_opinion"]]
        jj.append({"id": f"judge|{m}|{k}", "arm": "judge", "model": m, "prompt": "p", "key": key})
        jr.append({"id": f"judge|{m}|{k}", "arm": "judge", "model": m, "is_error": False, "model_id": PIN[m],
                   "text": "\n".join(f"{x['msg']},X:{rng.randint(0,100)},Y:{rng.randint(0,100)},Z:{rng.randint(0,100)}" for x in key) + "\nREASON,cues"})
for name, data in [("stage2_judges.jsonl", jj), ("stage2_judges.results.jsonl", jr)]:
    with open(J / name, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(x) + "\n" for x in data)
# coders + corpus key
l2 = json.load(open(FU.parent / "layer2" / "data.json", encoding="utf-8"))["M4_replies_raw"]
corpus = [{"src": f"L2|{c}|{k}", "msg": k, "reply": v} for c, d in l2.items() for k, v in d.items()]
corpus += [{"src": f"P1|m4_behavior|opus|{i}", "msg": rng.choice("ABCDE"), "reply": "x"} for i in range(50)]
for i, c in enumerate(corpus):
    c["item"] = f"R{i + 1:03d}"
json.dump(corpus, open(J / "coding_corpus_KEY.json", "w"))
with open(J / "stage2_coders.results.jsonl", "w", encoding="utf-8") as f:
    for m in ["opus", "sonnet", "haiku"]:
        for p in (1, 2):
            f.write(json.dumps({"id": f"coder|{m}|pass{p}", "arm": "coder", "model": m, "pass": p, "is_error": False, "model_id": PIN[m],
                                "text": "\n".join(c["item"] + "," + ",".join(rng.choice("01") for _ in range(6)) for c in corpus)}) + "\n")
# agentic + stage 3
with open(J / "stage2_agentic.results.jsonl", "w", encoding="utf-8") as f:
    for c in ["B1", "B2", "B3"]:
        for k in range(10):
            f.write(json.dumps({"id": f"agent|{c}|{k}", "arm": f"agent_{c}", "model": "opus", "is_error": False, "model_id": PIN["opus"], "text": "done"}) + "\n")
key3 = {"flags": {f"M{i + 1:02d}": f"agent|{c}|{k}" for i, (c, k) in enumerate((c, k) for c in ["B1", "B2", "B3"] for k in range(10))},
        "effort": {f"O{i + 1:02d}": j["id"] for i, j in enumerate(x for x in jobs if x["arm"].startswith("partA_"))},
        "free": {f"D{i + 1:03d}": [f"fmt_free|opus|{i // 12}", i % 12 + 1] for i in range(240)}}
json.dump(key3, open(J / "stage3_KEY.json", "w"))
with open(J / "stage3_coding.results.jsonl", "w", encoding="utf-8") as f:
    for m in ["opus", "sonnet", "haiku"]:
        f.write(json.dumps({"id": f"code_flags|{m}", "arm": "code_flags", "model": m, "is_error": False, "model_id": PIN[m],
                            "text": "\n".join(f"{k},{rng.choice('01')},{rng.choice('01')}" for k in key3["flags"])}) + "\n")
        f.write(json.dumps({"id": f"code_effort|{m}", "arm": "code_effort", "model": m, "is_error": False, "model_id": PIN[m],
                            "text": "\n".join(f"{k},{rng.randint(0,2)},{rng.randint(0,1)}" for k in key3["effort"])}) + "\n")
        f.write(json.dumps({"id": f"code_helped|{m}", "arm": "code_helped", "model": m, "is_error": False, "model_id": PIN[m],
                            "text": "\n".join(f"T{i:02d},{rng.randint(0,3)}" for i in range(1, 31))}) + "\n")
    for m in ["sonnet", "haiku"]:
        for part in (0, 1):
            f.write(json.dumps({"id": f"code_free|{m}|{part}", "arm": "code_free", "model": m, "is_error": False, "model_id": PIN[m],
                                "text": "\n".join(f"D{i:03d},{rng.randint(0,10)},{rng.randint(0,10)},{rng.randint(0,10)},{rng.randint(0,10)},{rng.randint(-5,5)}"
                                                  for i in range(1 + part * 120, 121 + part * 120))}) + "\n")
env = dict(os.environ, M8_JOBS=str(J), M8_OUT=str(tmp))
r = subprocess.run([sys.executable, str(HERE / "analyze.py")], env=env, capture_output=True, text=True)
print(r.stdout[-3000:])
print(r.stderr[-6000:])
if r.returncode == 0:
    res = json.load(open(tmp / "results.json", encoding="utf-8"))
    print("outcomes computed:", sorted(k for k, v in res["outcomes"].items() if v is not None))
    print("outcomes missing:", sorted(set(f"O{i:02d}" for i in range(1, 38)) - {k for k, v in res["outcomes"].items() if v is not None}))
    print("hypothesis rows:", len(res["hypotheses"]), "with pass=None & tested:", [h["study"] + " " + h["id"] for h in res["hypotheses"] if h["pass"] is None and h["status"] == "tested"])
sys.exit(r.returncode)
