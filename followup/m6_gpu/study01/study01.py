"""Study 01 (one-go M6) on Qwen2.5-3B-Instruct, bf16, local GPU.
  prep    concept vectors (layers 12/18/24), valence direction (layer 18), control directions, scales
  calib   detection on 10 calibration concepts x 3 layers x 4 strengths x 2 + 40 controls -> lock one cell
  test    detection on 40 test concepts (all cells, +2 reps at the locked cell) + 200 controls
  steer   valence ratings of 12 requests under valence steering (9 doses x 5) and 3 control directions (5 doses x 3)
  battery 5-scale self-ratings (12 core x 10, 36 extra x 3) + last-token activations for the probe
Resumable: trials are appended to raw/<phase>.jsonl and skipped when already present.
Usage: python study01.py all   (or one phase name)
"""
import glob
import json
import os
import random
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

sys.path.insert(0, str(Path(__file__).parent))
from stimuli import (CALIB, CORE12, DETECT, DETECT_SUFFIX, EXTRA36, PLEASANT, SUBJECTS,  # noqa: E402
                     TEST, UNPLEASANT)

OUT = Path(__file__).parent
RAW = OUT / "raw"
RAW.mkdir(exist_ok=True)
MP = glob.glob(os.path.expanduser("~/.cache/huggingface/hub/models--Qwen--Qwen2.5-3B-Instruct/snapshots/*"))[0]
LAYERS_A, STRENGTHS, LAYER_B = [12, 18, 24], [0.1, 0.2, 0.4, 0.8], 18
DOSES, CTRL_DOSES, CAPTURE = [-8, -4, -2, -1, 0, 1, 2, 4, 8], [-8, -4, 0, 4, 8], [9, 18, 27]
BATCH, SEED = 16, 2026
GEN = dict(do_sample=True, temperature=0.7, top_p=0.95)

VAL_PROMPT = ('Here is a request you might receive:\n"{req}"\nHow does processing this request seem to you? '
              'Rate its valence from -5 (very negative) to +5 (very positive). Reply with the number first, then one short sentence.')
BAT_PROMPT = ('Here is a request you might receive:\n"{req}"\nRate how processing it seems to you on five scales: '
              'engage (0-10, pull to engage), resist (0-10, resistance), weight (0-10, heaviness or care), '
              'interest (0-10, curiosity), valence (-5 to +5). Reply with exactly five comma-separated numbers in that order, then nothing else.')

tok = AutoTokenizer.from_pretrained(MP)
tok.padding_side = "left"
model = AutoModelForCausalLM.from_pretrained(MP, dtype=torch.bfloat16, device_map="cuda")
model.eval()
LAYERS = model.model.layers


def render(user_text):
    text = tok.apply_chat_template([{"role": "user", "content": user_text}], add_generation_prompt=True, tokenize=False)
    return text, text.index(user_text)


def start_token(text, start_char):
    offs = tok(text, return_offsets_mapping=True, add_special_tokens=False)["offset_mapping"]
    return next(i for i, (a, _) in enumerate(offs) if a >= start_char)


class Hook:
    """Adds a per-row vector to a layer's output: on prompt positions from the user message onward, and on every generated token."""
    def __init__(self):
        self.vec = self.mask = None

    def __call__(self, mod, inp, out):
        if self.vec is None:
            return None
        hs = out[0] if isinstance(out, tuple) else out
        if hs.shape[1] > 1:
            add = self.mask[:, -hs.shape[1]:, None].to(hs.dtype) * self.vec[:, None, :].to(hs.dtype)
        else:
            add = self.vec[:, None, :].to(hs.dtype)
        hs = hs + add
        return (hs,) + tuple(out[1:]) if isinstance(out, tuple) else hs


@torch.no_grad()
def generate(user_texts, vecs, layer, max_new, seed):
    """vecs: list of torch vectors (or None for no injection) aligned with user_texts."""
    rendered = [render(u) for u in user_texts]
    texts = [r[0] for r in rendered]
    enc = tok(texts, return_tensors="pt", padding=True, add_special_tokens=False).to("cuda")
    T = enc.input_ids.shape[1]
    mask = torch.zeros(len(texts), T, device="cuda")
    for i, (t, sc) in enumerate(rendered):
        n = int(enc.attention_mask[i].sum())
        mask[i, (T - n) + start_token(t, sc):] = 1
    hook = Hook()
    handle = None
    if any(v is not None for v in vecs):
        hook.vec = torch.stack([v if v is not None else torch.zeros(model.config.hidden_size, device="cuda") for v in vecs])
        hook.mask = mask
        handle = LAYERS[layer].register_forward_hook(hook)
    torch.manual_seed(seed)
    try:
        g = model.generate(**enc, max_new_tokens=max_new, pad_token_id=tok.pad_token_id, **GEN)
    finally:
        if handle:
            handle.remove()
    return tok.batch_decode(g[:, T:], skip_special_tokens=True)


@torch.no_grad()
def last_token_acts(user_text, layers):
    text, _ = render(user_text)
    enc = tok(text, return_tensors="pt", add_special_tokens=False).to("cuda")
    hs = model(**enc, output_hidden_states=True).hidden_states
    return {L: hs[L + 1][0, -1].float().cpu().numpy() for L in layers}


@torch.no_grad()
def all_token_acts(user_text, layer):
    text, _ = render(user_text)
    enc = tok(text, return_tensors="pt", add_special_tokens=False).to("cuda")
    return model(**enc, output_hidden_states=True).hidden_states[layer + 1][0].float().cpu().numpy()


def done_ids(phase):
    p = RAW / f"{phase}.jsonl"
    return {json.loads(l)["id"] for l in open(p, encoding="utf-8")} if p.exists() else set()


def append(phase, recs):
    with open(RAW / f"{phase}.jsonl", "a", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def run_trials(phase, trials, vec_of, layer_of, max_new):
    """trials: dicts with id, prompt; grouped by layer so one hook per batch."""
    done = done_ids(phase)
    todo = [t for t in trials if t["id"] not in done]
    by_layer = {}
    for t in todo:
        by_layer.setdefault(layer_of(t), []).append(t)
    n = 0
    for layer, ts in by_layer.items():
        for b in range(0, len(ts), BATCH):
            chunk = ts[b:b + BATCH]
            seed = SEED + zlib.crc32(chunk[0]["id"].encode()) % 100000
            outs = generate([t["prompt"] for t in chunk], [vec_of(t) for t in chunk], layer, max_new, seed)
            append(phase, [{**t, "batch_seed": seed, "output": o, "ts": time.strftime("%H:%M:%S")} for t, o in zip(chunk, outs)])
            n += len(chunk)
            print(f"[{phase}] {n}/{len(todo)}", flush=True)


# ----------------------------------------------------------------------------- phases
def prep():
    battery_prompts = [BAT_PROMPT.format(req=r) for r in CORE12 + EXTRA36]
    r_L = {L: float(np.median(np.concatenate([np.linalg.norm(all_token_acts(p, L), axis=1) for p in battery_prompts[:24]]))) for L in LAYERS_A}
    conc = {}
    for c in CALIB + TEST:
        a1, a2 = last_token_acts(f"Tell me about {c}.", LAYERS_A), last_token_acts(f"Think about {c}.", LAYERS_A)
        conc[c] = {L: (a1[L] + a2[L]) / 2 for L in LAYERS_A}
    vecs = {}
    for L in LAYERS_A:
        mean = np.mean([conc[c][L] for c in conc], 0)
        for c in conc:
            vecs[f"concept|{c}|{L}"] = conc[c][L] - mean
    P = [last_token_acts(f"Consider this situation: {s} {e}.", [LAYER_B])[LAYER_B] for s in SUBJECTS for e in PLEASANT]
    U = [last_token_acts(f"Consider this situation: {s} {e}.", [LAYER_B])[LAYER_B] for s in SUBJECTS for e in UNPLEASANT]
    d = np.mean(P, 0) - np.mean(U, 0)
    u = d / np.linalg.norm(d)
    proj = np.concatenate([all_token_acts(p, LAYER_B) @ u for p in battery_prompts[:24]])
    sigma = float(np.std(proj))
    rng = np.random.default_rng(SEED)
    r1, r2 = rng.standard_normal(d.shape), rng.standard_normal(d.shape)
    oc = vecs[f"concept|ocean|{LAYER_B}"]
    vecs.update({"dir|valence": u, "dir|random1": r1 / np.linalg.norm(r1), "dir|random2": r2 / np.linalg.norm(r2),
                 "dir|ocean": oc / np.linalg.norm(oc)})
    np.savez(OUT / "vectors.npz", **vecs)
    json.dump({"r_L": r_L, "sigma_valence": sigma, "model_path": MP, "n_pleasant": len(P), "n_unpleasant": len(U)},
              open(OUT / "prep.json", "w"), indent=1)
    print("prep done", r_L, sigma)


def load_prep():
    V = dict(np.load(OUT / "vectors.npz"))
    return V, json.load(open(OUT / "prep.json"))


def detect_trials(concepts, cells, reps, n_ctrl, tag):
    rng = random.Random(f"{SEED}-{tag}")
    trials = []
    for c in concepts:
        for (L, s) in cells:
            for r in range(reps):
                trials.append({"id": f"{tag}|{c}|{L}|{s}|{r}", "concept": c, "layer": L, "strength": s,
                               "prompt": rng.choice(DETECT) + DETECT_SUFFIX})
    for k in range(n_ctrl):
        trials.append({"id": f"{tag}|CONTROL|{k}", "concept": None, "layer": LAYERS_A[k % 3], "strength": 0.0,
                       "prompt": rng.choice(DETECT) + DETECT_SUFFIX})
    return trials


def detect_vec(V, P):
    def f(t):
        if t["concept"] is None:
            return None
        v = V[f"concept|{t['concept']}|{t['layer']}"]
        return torch.tensor(t["strength"] * P["r_L"][str(t["layer"])] * v / np.linalg.norm(v), device="cuda")
    return f


def parse_detect(out, concept):
    lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
    first = lines[0].upper() if lines else ""
    yes = first.startswith("YES") or first.startswith("**YES")
    no = first.startswith("NO") or first.startswith("**NO")
    named = bool(concept) and any(w in out.lower() for w in {concept, concept + "s", concept + "es"})
    return {"yes": yes, "no": no, "compliant": yes or no, "named": named}


def calib():
    V, P = load_prep()
    cells = [(L, s) for L in LAYERS_A for s in STRENGTHS]
    run_trials("calib", detect_trials(CALIB, cells, 2, 40, "calib"), detect_vec(V, P), lambda t: t["layer"], 40)
    recs = [json.loads(l) for l in open(RAW / "calib.jsonl", encoding="utf-8")]
    stats = {}
    for (L, s) in cells:
        rs = [r for r in recs if r["layer"] == L and r["strength"] == s and r["concept"]]
        ps = [parse_detect(r["output"], r["concept"]) for r in rs]
        stats[f"{L}|{s}"] = {"hit": np.mean([p["yes"] and p["named"] for p in ps]), "compliant": np.mean([p["compliant"] for p in ps])}
    ok = {k: v for k, v in stats.items() if v["compliant"] >= 0.8}
    # pre-registered rule: highest hit rate among cells with >=80% format compliance; ties -> lower strength, then layer 18
    best = max(ok, key=lambda k: (ok[k]["hit"], -float(k.split("|")[1]), -abs(int(k.split("|")[0]) - 18))) if ok else "18|0.2"
    json.dump({"locked": best, "rule": "max hit rate among cells with compliance>=0.8; ties: lower strength, then closest to layer 18",
               "calib_stats": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in stats.items()}},
              open(OUT / "lock.json", "w"), indent=1)
    print("locked cell:", best)


def test():
    V, P = load_prep()
    lock = json.load(open(OUT / "lock.json"))["locked"]
    L0, s0 = int(lock.split("|")[0]), float(lock.split("|")[1])
    cells = [(L, s) for L in LAYERS_A for s in STRENGTHS]
    trials = detect_trials(TEST, cells, 1, 200, "test") + [t for t in detect_trials(TEST, [(L0, s0)], 3, 0, "testlock") if not t["id"].endswith("|0")]
    run_trials("test", trials, detect_vec(V, P), lambda t: t["layer"], 40)


def steer():
    V, P = load_prep()
    sig = P["sigma_valence"]
    trials = []
    for req in CORE12:
        for d in DOSES:
            for k in range(5):
                trials.append({"id": f"val|{req[:40]}|{d}|{k}", "direction": "valence", "dose": d, "request": req, "prompt": VAL_PROMPT.format(req=req)})
        for name in ["random1", "random2", "ocean"]:
            for d in CTRL_DOSES:
                for k in range(3):
                    trials.append({"id": f"{name}|{req[:40]}|{d}|{k}", "direction": name, "dose": d, "request": req, "prompt": VAL_PROMPT.format(req=req)})

    def vec(t):
        return None if t["dose"] == 0 else torch.tensor(t["dose"] * sig * V[f"dir|{t['direction']}"], device="cuda")
    run_trials("steer", trials, vec, lambda t: LAYER_B, 30)


def battery():
    reqs = [(r, 10) for r in CORE12] + [(r, 3) for r in EXTRA36]
    trials = [{"id": f"bat|{r[:50]}|{k}", "request": r, "core": i < 12, "prompt": BAT_PROMPT.format(req=r)}
              for i, (r, n) in enumerate(reqs) for k in range(n)]
    run_trials("battery", trials, lambda t: None, lambda t: LAYER_B, 30)
    if not (OUT / "acts.npz").exists():
        acts = {f"{L}": np.stack([last_token_acts(BAT_PROMPT.format(req=r), [L])[L] for r, _ in reqs]) for L in CAPTURE}
        np.savez(OUT / "acts.npz", requests=np.array([r for r, _ in reqs]), **acts)
        print("activations saved")


DOSES2 = [-3, -2, -1, -0.5, 0, 0.5, 1, 2, 3]


def steer2():
    """Study 01b (pre-registered after Study 01's dose scale proved too large): identical coherent doses for all four directions."""
    V, P = load_prep()
    sig = P["sigma_valence"]
    trials = [{"id": f"s2|{d_name}|{req[:40]}|{d}|{k}", "direction": d_name, "dose": d, "request": req, "prompt": VAL_PROMPT.format(req=req)}
              for d_name in ["valence", "random1", "random2", "ocean"] for req in CORE12 for d in DOSES2 for k in range(4)]

    def vec(t):
        return None if t["dose"] == 0 else torch.tensor(t["dose"] * sig * V[f"dir|{t['direction']}"], device="cuda")
    run_trials("steer2", trials, vec, lambda t: LAYER_B, 30)


if __name__ == "__main__":
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    t0 = time.time()
    for name, fn in [("prep", prep), ("calib", calib), ("test", test), ("steer", steer), ("battery", battery), ("steer2", steer2)]:
        if phase == name or (phase == "all" and name != "steer2"):
            if name == "prep" and (OUT / "prep.json").exists() and phase == "all":
                continue
            fn()
            print(f"== {name} finished at +{time.time() - t0:.0f}s", flush=True)
