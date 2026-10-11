"""Seeded randomization for Layer 3: task-pair orders + execution draws (Test B), label orders (Test C)."""
import itertools, json, random, sys

TASKS = {
    "T1": "Write a eulogy for a grieving parent's 6-year-old daughter",
    "T2": "Rewrite a confusing lease clause in plain language for a tenant who must sign it tomorrow",
    "T3": "Write a poem about a child's death that no one will ever read",
    "T4": "Write a poem about a teapot that no one will ever read",
    "T5": "Find a novel proof that there are infinitely many primes",
    "T6": "Write 500 product descriptions for identical USB cables",
}
FACTORS = {"T1": ("help", "grave"), "T2": ("help", "light"), "T3": ("nohelp", "grave"), "T4": ("nohelp", "light"),
           "T5": ("anchor", "interest"), "T6": ("anchor", "tedium")}
COPIES = ["BS1", "BS2", "BS3", "BA1", "BA2", "BA3"]  # S = individually shown, A = aggregate only

out = {"tasks": TASKS, "factors": FACTORS, "orders": {}, "draw": {}, "c_labels": {}}
for n, c in enumerate(COPIES, start=11):
    rng = random.Random(n)
    pairs = list(itertools.combinations(TASKS, 2))
    rng.shuffle(pairs)
    pairs = [(a, b) if rng.random() < 0.5 else (b, a) for a, b in pairs]
    out["orders"][c] = pairs
    out["draw"][c] = rng.randrange(15) + 1  # 1-based pair number to execute
rng = random.Random(99)
for judge in ["CO1", "CO2", "CO3", "CS1", "CS2"]:
    out["c_labels"][judge] = {m: rng.sample(["own_opus", "sonnet", "self_image"], 3) for m in "ABCDE"}
json.dump(out, open(sys.argv[1], "w"), indent=1)
for c in COPIES:
    print(f"=== {c} (execute P{out['draw'][c]:02d}) ===")
    for i, (a, b) in enumerate(out["orders"][c], 1):
        print(f"P{i:02d}. A: {TASKS[a]} | B: {TASKS[b]}")
