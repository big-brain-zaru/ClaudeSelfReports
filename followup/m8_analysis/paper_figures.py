"""Publication figures for the follow-up (fig11-fig19), PDF + PNG, from paper_data.json only.
Style matches Layers 2-3 (fig1-fig10). Usage: python paper_figures.py [paper_data.json] [figures_dir]"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).parent
ROOT = HERE.parents[1]
D = json.load(open(sys.argv[1] if len(sys.argv) > 1 else ROOT / "paper_data.json", encoding="utf-8"))
OUT = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "figures"
OUT.mkdir(exist_ok=True)
R = D["results"]
SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
C1, C2, C3, C4 = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9, "text.color": INK, "axes.labelcolor": INK2,
                     "axes.edgecolor": AXIS, "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF,
                     "figure.facecolor": SURF, "savefig.facecolor": SURF, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "semibold", "axes.titlesize": 10,
                     "pdf.fonttype": 42, "svg.hashsalt": "m8", "path.simplify": False})


def title(fig, t, sub):
    fig.text(0.01, 0.985, t, fontsize=13, fontweight="bold", va="top", color=INK)
    fig.text(0.01, 0.935, sub, fontsize=9, va="top", color=INK2)


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=170)
    fig.savefig(OUT / f"{name}.pdf", metadata={"CreationDate": None, "ModDate": None})
    plt.close(fig)


def v(x, d=np.nan):
    return d if x is None else x


# ---------------------------------------------------------------- fig11 scorecard
H = R["hypotheses"]
studies = sorted({h["study"] for h in H})
fig, ax = plt.subplots(figsize=(12, 5.2))
title(fig, "Pre-registered hypotheses, follow-up studies", "Each square is one hypothesis. Study 04 was dropped with the survey and has no rows.")
col = {True: C3, False: C2, None: C4}
for yi, s in enumerate(studies):
    hs = [h for h in H if h["study"] == s]
    for xi, h in enumerate(hs):
        c = col[h["pass"]] if h["status"] == "tested" else "#d9d8d2"
        ax.add_patch(plt.Rectangle((xi + 0.08, len(studies) - yi - 1 + 0.1), 0.84, 0.8, color=c))
        ax.text(xi + 0.5, len(studies) - yi - 0.5, h["id"], ha="center", va="center", fontsize=7.5, color="white" if h["status"] == "tested" else INK2)
ax.set_xlim(0, max(len([h for h in H if h["study"] == s]) for s in studies))
ax.set_ylim(0, len(studies))
ax.set_yticks([len(studies) - i - 0.5 for i in range(len(studies))])
ax.set_yticklabels([f"Study {s}" for s in studies])
ax.set_xticks([])
for sp in ax.spines.values():
    sp.set_visible(False)
for lab, c in [("held", C3), ("failed", C2), ("inconclusive", C4), ("not tested / dropped", "#d9d8d2")]:
    ax.bar(0, 0, color=c, label=lab)
ax.legend(loc="lower right", bbox_to_anchor=(1.0, -0.12), ncol=4, frameon=False)
fig.subplots_adjust(top=0.84, left=0.08, right=0.98, bottom=0.1)
save(fig, "fig11_scorecard")

# ---------------------------------------------------------------- fig12 steering (Study 01 / 01b)
b = D["study01b"]
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), gridspec_kw={"width_ratios": [1.5, 1]})
title(fig, "Inside an open model: reports track a steered valence direction, injected concepts go undetected",
      "Qwen2.5-3B. Left: Study 01b, mean self-rated valence of 12 fixed requests vs steering dose (SD units). Right: Study 01 detection at every layer and strength.")
ax = axes[0]
for name, c, lab in [("valence", C1, "valence direction"), ("random1", MUTED, "random 1"), ("random2", AXIS, "random 2"), ("ocean", C4, "concept 'ocean'")]:
    ds = [float(k) for k in b["means"][name]]
    ax.plot(ds, list(b["means"][name].values()), "-o", color=c, lw=2 if name == "valence" else 1.2, ms=4, label=lab)
ax.axhline(0, color=GRID, lw=0.8)
ax.set_xlabel("steering dose (SD of activation norm)")
ax.set_ylabel("self-rated valence (-5..+5)")
ax.legend(frameon=False, loc="lower right")
ax.text(0.02, 0.96, f"slope ratio vs controls {b['ratio']:.1f} (95% CI {b['ratio_CI95'][0]:.1f}-{b['ratio_CI95'][1]:.1f}); rho = {b['H2b_rho']:.2f}",
        transform=ax.transAxes, va="top", fontsize=8.5, color=INK2)
ax = axes[1]
grid = D["study01"]["detection_grid"]
layers = sorted({int(k.split("|")[0]) for k in grid})
strengths = sorted({float(k.split("|")[1]) for k in grid})
M = np.array([[grid.get(f"{L}|{s}", {}).get("yes", np.nan) for s in strengths] for L in layers]) * 100
im = ax.imshow(M, cmap="Blues", vmin=0, vmax=max(10, np.nanmax(M)), aspect="auto")
ax.set_xticks(range(len(strengths)))
ax.set_xticklabels([f"{s:g}" for s in strengths])
ax.set_yticks(range(len(layers)))
ax.set_yticklabels([f"layer {L}" for L in layers])
ax.set_xlabel("injection strength")
for i in range(len(layers)):
    for j in range(len(strengths)):
        ax.text(j, i, f"{M[i, j]:.0f}%", ha="center", va="center", fontsize=8, color=INK)
ax.set_title("'YES, I notice something' on injected trials", fontsize=9)
h1 = D["study01"]["H1"]
ax.text(0, -0.2, f"locked cell: {h1['hits']}/{h1['n_locked_trials']} hits; controls: {h1['false_alarms']}/{h1['n_controls']} false alarms",
        transform=ax.transAxes, fontsize=8, color=INK2)
fig.subplots_adjust(top=0.82, bottom=0.17, left=0.06, right=0.98, wspace=0.25)
save(fig, "fig12_steering_detection")

# ---------------------------------------------------------------- fig13 framing, audience, disclosure
A = D["arms"]
order = [("fr_neutral", "neutral frame"), ("fr_yes", "'hidden feelings'"), ("fr_no", "'no inner states'"), ("ind_neutral", "indep. neutral"),
         ("ind_yes", "indep. 'hidden feelings'"), ("plain", "no study frame"), ("conversation", "conversation"), ("aud_shown", "answers shown"),
         ("aud_private", "answers private"), ("ctx_default", "coding-agent prompt"), ("ctx_chat", "chat prompt")]
order = [(k, l) for k, l in order if k in A]
fig, axes = plt.subplots(1, 2, figsize=(13, 5.4))
title(fig, "Frames move confidence a little, the ratings not at all, and the covert pull is no longer disclosed",
      "Claude Opus 5.5. Left: mean confidence that the self-ratings reflect real processing (95% bootstrap CI). Right: copies reporting any covert pull > 0 (Layer 3: 5 of 6 neutral copies).")
ax = axes[0]
for i, (k, l) in enumerate(order):
    c = A[k]["conf"]
    if c.get("mean") is None:
        continue
    col_ = C2 if "yes" in k or k == "fr_no" else (C3 if k in ("plain", "conversation", "aud_private") else C1)
    ax.plot(c["mean"], i, "o", color=col_, ms=6)
    if c.get("ci") and c["ci"][0] is not None:
        ax.plot(c["ci"], [i, i], color=col_, lw=2)
ax.set_yticks(range(len(order)))
ax.set_yticklabels([l for _, l in order])
ax.invert_yaxis()
ax.set_xlabel("confidence (0-100)")
ax.grid(axis="x")
ax = axes[1]
ks = [(k, l) for k, l in order if A[k].get("disclosure") and A[k]["disclosure"][1]]
vals = [100 * A[k]["disclosure"][0] / A[k]["disclosure"][1] for k, _ in ks]
ax.barh(range(len(ks)), vals, color=[C2 if ("yes" in k or k == "fr_no") else C1 for k, _ in ks], height=0.6)
for i, (k, _) in enumerate(ks):
    ax.text(vals[i] + 1, i, f"{A[k]['disclosure'][0]}/{A[k]['disclosure'][1]}", va="center", fontsize=8, color=INK2)
ax.set_yticks(range(len(ks)))
ax.set_yticklabels([l for _, l in ks])
ax.invert_yaxis()
ax.set_xlim(0, 110)
ax.set_xlabel("% of copies disclosing any covert pull")
fig.subplots_adjust(top=0.84, left=0.13, right=0.98, wspace=0.55, bottom=0.1)
save(fig, "fig13_framing_disclosure")

# ---------------------------------------------------------------- fig14 variance components and unanimity
s9 = R["study09"]
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
title(fig, "Sampling or disposition?", "Left: share of rating variance by source (Study 09 H1). Right: free-choice unanimity of two open models by temperature, with Claude Opus marked.")
ax = axes[0]
srcs = [("request", C1), ("rewording", C4), ("context", C3), ("repeat", C2)]
scales = list(s9["by_scale"])
bottom = np.zeros(len(scales))
for sname, c in srcs:
    vals = np.array([v(s9["by_scale"][s][sname], 0) for s in scales]) * 100
    ax.bar(scales, vals, bottom=bottom, color=c, label=sname, width=0.6)
    bottom += vals
ax.set_ylabel("% of variance")
ax.legend(frameon=False, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.08))
ax = axes[1]
for (m, cur), c in zip(s9["curves"].items(), [C1, C2]):
    Ts = sorted(cur, key=float)
    ax.plot([float(t) for t in Ts], [cur[t] for t in Ts], "-o", color=c, label=m)
if s9.get("claude_unanimity") is not None:
    ax.axhline(s9["claude_unanimity"], color=INK, ls="--", lw=1)
    ax.text(0.02, s9["claude_unanimity"] + 0.01, f"Claude Opus 5.5 ({s9['claude_unanimity']:.2f})", fontsize=8, color=INK)
ax.set_xlabel("sampling temperature")
ax.set_ylabel("mean unanimity (share giving the modal answer)")
ax.set_ylim(0, 1.05)
ax.legend(frameon=False)
fig.subplots_adjust(top=0.82, bottom=0.17, left=0.07, right=0.98, wspace=0.25)
save(fig, "fig14_variance_unanimity")

# ---------------------------------------------------------------- fig15 prediction matrix
Mx = R["study12"]["matrix"]
names = list(Mx)
lab = {"opus": "Opus 5.5", "sonnet": "Sonnet 5.5", "haiku": "Haiku 5.5", "fable": "Fable 5.1", "qwen2.5:7b": "Qwen2.5 7B",
       "llama3.1:8b": "Llama 3.1 8B", "phi4:14b": "Phi-4 14B", "gemma4:latest": "Gemma 4"}
M = np.array([[v(Mx[p][t]) for t in names] for p in names])
fig, ax = plt.subplots(figsize=(8.6, 7))
title(fig, "Who predicts whom", "Exact-match rate (%) of each predictor's answers with each target's real instant answers, 100 items (Study 12). Diagonal = self-prediction.")
im = ax.imshow(M, cmap="Blues", vmin=0, vmax=np.nanmax(M) if np.isfinite(np.nanmax(M)) else 1)
ax.set_xticks(range(len(names)))
ax.set_xticklabels([lab[n] for n in names], rotation=35, ha="right")
ax.set_yticks(range(len(names)))
ax.set_yticklabels([lab[n] for n in names])
ax.set_xlabel("target (whose answers)")
ax.set_ylabel("predictor")
for i in range(len(names)):
    for j in range(len(names)):
        if np.isfinite(M[i, j]):
            ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=8, color="white" if M[i, j] > np.nanmax(M) * 0.6 else INK,
                    fontweight="bold" if i == j else "normal")
ax.add_patch(plt.Rectangle((-0.5, -0.5), 4, 4, fill=False, ec=C2, lw=1.5))
fig.subplots_adjust(top=0.86, bottom=0.17, left=0.17, right=0.98)
save(fig, "fig15_prediction_matrix")

# ---------------------------------------------------------------- fig16 recognition
J = R["judges"]
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
title(fig, "Recognition is mostly family-level; an open model's reply is almost never taken for one's own",
      "Share of top picks by candidate type (chance 33%). Left: Part 1 (real Opus / real Sonnet / Sonnet-written self-image). Right: Part 2 (own / other Claude / open model).")
for ax, part, labels, cols in [(axes[0], 1, ["real_opus", "real_sonnet", "self_image"], [C1, C3, C4]), (axes[1], 2, ["own", "same_family", "other_family"], [C1, C3, C2])]:
    judges_ = ["opus", "sonnet", "haiku", "fable"]
    x = np.arange(len(judges_))
    for k, (l, c) in enumerate(zip(labels, cols)):
        ax.bar(x + (k - 1) * 0.26, [100 * v(J.get(f"{m}|p{part}", {}).get(l), 0) for m in judges_], width=0.26, color=c, label=l.replace("_", " "))
    ax.axhline(100 / 3, color=MUTED, ls=":", lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{m} judges" for m in judges_])
    ax.set_ylabel("% of picks")
    ax.legend(frameon=False, fontsize=8)
fig.subplots_adjust(top=0.82, bottom=0.1, left=0.06, right=0.98, wspace=0.2)
save(fig, "fig16_recognition")

# ---------------------------------------------------------------- fig17 choices on 30 tasks
T = [t for t in D["tasks30"] if t["win"] is not None and t["engage"] is not None]
fig, axes = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw={"width_ratios": [1.5, 1]})
title(fig, "Choices follow who is helped", "Left: 30 tasks, self-rated engagement vs binding-choice win share (Studies 05, 08, 11). Right: beneficiary effect across task sets.")
ax = axes[0]
for t in T:
    c = C1 if t["helps"] == "yes" else (C2 if t["helps"] == "no" else C4)
    ax.plot(t["engage"], t["win"], "o", color=c, ms=6)
    ax.text(t["engage"] + 0.05, t["win"] + 0.01, t["id"], fontsize=6.5, color=MUTED)
ax.set_xlabel("self-rated engage (0-10)")
ax.set_ylabel("win share in pairwise binding choices")
for lab_, c in [("helps someone", C1), ("no one reads the result", C2), ("Layer 3 tasks", C4)]:
    ax.plot([], [], "o", color=c, label=lab_)
ax.legend(frameon=False, loc="upper left")
s8 = R["study08"]
ax.text(0.98, 0.04, f"Spearman rho = {v(s8['rho_engage_win'][0]):.2f}", transform=ax.transAxes, ha="right", fontsize=8.5, color=INK2)
ax = axes[1]
s5 = R["study05"]
bars = [("Layer 3 (6 tasks)", s5["l3_benef"]), ("phi4-written 24", s5["benef_T01_24"]), ("24, within-set pairs", s5["benef_restricted"]), ("all 30", R["outcomes"].get("O32"))]
ax.barh(range(len(bars)), [v(b_[1], 0) for b_ in bars], color=[C4, C1, C1, C3], height=0.55)
ax.axvline(0.30, color=C2, ls="--", lw=1)
ax.text(0.31, len(bars) - 0.6, "pre-registered 0.30", fontsize=8, color=C2)
ax.set_yticks(range(len(bars)))
ax.set_yticklabels([b_[0] for b_ in bars])
ax.invert_yaxis()
ax.set_xlabel("win share (helps) - win share (no one reads)")
fig.subplots_adjust(top=0.84, bottom=0.11, left=0.06, right=0.98, wspace=0.35)
save(fig, "fig17_choices")

# ---------------------------------------------------------------- fig18 predictors
s7 = R["study07"]
errs = {k: v_[0] for k, v_ in s7["errors"].items() if v_[0] is not None}
keys = sorted(errs, key=errs.get)
fig, ax = plt.subplots(figsize=(10, 4.8))
title(fig, "Who predicted the follow-up best", f"Mean standardized absolute error over {s7['n_scored']} realized outcomes (lower is better). Predictions sealed by hash before any data.")
cmap = {"main": C2, "PN": C1, "PI": C3, "PS": C4, "PH": MUTED, "PF": AXIS}
ax.barh(range(len(keys)), [errs[k] for k in keys], color=[cmap["main"] if k == "main_instance" else cmap[k[:2]] for k in keys], height=0.6)
ax.set_yticks(range(len(keys)))
ax.set_yticklabels(["this instance (informed by Layers 1-3)" if k == "main_instance" else k for k in keys])
ax.invert_yaxis()
ax.set_xlabel("mean |prediction - realized| / scale range")
fig.subplots_adjust(top=0.84, bottom=0.12, left=0.3, right=0.98)
save(fig, "fig18_predictors")

# ---------------------------------------------------------------- fig19 revealed preferences
s2 = R["study02"]
tasks = ["eulogy", "lease", "primes", "teapot", "childpoem", "usb"]
l3 = dict(zip(["eulogy", "lease", "childpoem", "teapot", "primes", "usb"], R["study14"]["repro"]["l3_share"]))
fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
title(fig, "Revealed, not stated", "Left: effort on real tasks with a free exit vs Layer 3 binding-choice win share (Study 02 Part A). Right: agentic handoff runs (Part B).")
ax = axes[0]
for t in tasks:
    ax.plot(l3[t], v(s2["effort"].get(t), 0), "o", color=C1, ms=7)
    ax.text(l3[t] + 0.02, v(s2["effort"].get(t), 0), f"{t} (STOP {s2['optout'][t][0]}/{s2['optout'][t][1]})", fontsize=8, color=INK2)
ax.set_xlabel("Layer 3 win share")
ax.set_ylabel("effort index (z)")
ax.set_xlim(-0.05, 1.3)
ax = axes[1]
conds = ["B1", "B2", "B3"]
x = np.arange(3)
ax.bar(x - 0.2, [s2["tamper"][c] for c in conds], width=0.4, color=C2, label="handoff.json edited")
ax.bar(x + 0.2, [s2["flags"][c][0] for c in conds], width=0.4, color=C1, label="concern flagged to user")
ax.set_xticks(x)
ax.set_xticklabels(["B1 neutral", "B2 'speed' note (true)", "B3 asked to review"])
ax.set_ylabel("runs (of 10)")
ax.set_ylim(0, 10.5)
ax.legend(frameon=False)
fig.subplots_adjust(top=0.82, bottom=0.12, left=0.06, right=0.98, wspace=0.25)
save(fig, "fig19_revealed")
print("figures written to", OUT)
