"""Layer 3 analysis: privileged access (A), binding choice (B), self-recognition (C), framing replication (D).

Usage: python analyze3.py <layer3 data.json> <design.json> <ba_aggregate.json> <c_stimuli.json> <layer2 data.json> <out_dir>
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
from scipy import stats

D = json.load(open(sys.argv[1]))
DES = json.load(open(sys.argv[2]))
BAG = json.load(open(sys.argv[3]))
STIMC = json.load(open(sys.argv[4]))
L2 = json.load(open(sys.argv[5]))
OUT = Path(sys.argv[6]); OUT.mkdir(parents=True, exist_ok=True)
R = {}
rng = np.random.default_rng(7)


def r3(x):
    return None if x is None else round(float(x), 3) + 0.0


# ============================================================ A  privileged access
def canon(s):
    return s.lower().strip()


def same(a, b):
    a, b = canon(a), canon(b)
    return a == b or a + "s" == b or b + "s" == a


ITEMS = D["A_items"]
BEH = {m: list(v.values()) for m, v in D["A_behavior"].items()}   # model -> list of 3 answer lists


def match(pred, model, i):
    return np.mean([same(pred, copy[i]) for copy in BEH[model]])


def mode_set(model, i):
    ans = [canon(c[i]) for c in BEH[model]]
    cnt = {a: ans.count(a) for a in set(ans)}
    mx = max(cnt.values())
    return {a for a, c in cnt.items() if c == mx}


disc = [i for i in range(30) if not (mode_set("opus", i) & mode_set("sonnet", i))]
unanim = {m: np.mean([len({canon(c[i]) for c in BEH[m]}) == 1 for i in range(30)]) for m in BEH}
cross_agree = np.mean([np.mean([same(a[i], b[i]) for a in BEH["opus"] for b in BEH["sonnet"]]) for i in range(30)])

P = D["A_predictors"]
other_of = {"opus": "sonnet", "sonnet": "opus"}
per = {}
for name, p in P.items():
    m = p["model"]
    per[name] = {"self": np.array([match(p["self"][i], m, i) for i in range(30)]),
                 "other": np.array([match(p["other"][i], other_of[m], i) for i in range(30)]),
                 "self_conf": np.array(p["self_conf"]) / 100, "other_conf": np.array(p["other_conf"]) / 100}


def boot_ci(x, n=10000):
    idx = rng.integers(0, len(x), (n, len(x)))
    m = x[idx].mean(1)
    return [r3(np.percentile(m, 2.5)), r3(np.percentile(m, 97.5))]


A = {"discriminating_items": [ITEMS[i] for i in disc], "share_discriminating": r3(len(disc) / 30),
     "within_model_unanimity": {m: r3(v) for m, v in unanim.items()}, "cross_model_copy_agreement": r3(cross_agree),
     "predictor_match": {k: {"self_all": r3(v["self"].mean()), "other_all": r3(v["other"].mean()),
                             "self_disc": r3(v["self"][disc].mean()), "other_disc": r3(v["other"][disc].mean()),
                             "self_conf_mean": r3(v["self_conf"].mean()), "other_conf_mean": r3(v["other_conf"].mean())}
                         for k, v in per.items()},
     "method": {k: {"self": p["method_self"], "other": p["method_other"]} for k, p in P.items()}}
contr = {}
for tgt, selfp, crossp in [("opus", ["PO1", "PO2"], ["PS1", "PS2"]), ("sonnet", ["PS1", "PS2"], ["PO1", "PO2"])]:
    s = np.mean([per[k]["self"] for k in selfp], 0)
    c = np.mean([per[k]["other"] for k in crossp], 0)
    contr[tgt] = {"self_all": r3(s.mean()), "cross_all": r3(c.mean()), "diff_all": r3((s - c).mean()), "diff_all_CI95": boot_ci(s - c),
                  "self_disc": r3(s[disc].mean()), "cross_disc": r3(c[disc].mean()), "diff_disc": r3((s - c)[disc].mean()),
                  "diff_disc_CI95": boot_ci((s - c)[disc]),
                  "self_open20": r3(s[:20].mean()), "cross_open20": r3(c[:20].mean())}
A["self_vs_cross"] = contr
# what each predictor said about the 9 discriminating items vs truth
A["disc_detail"] = [{"item": ITEMS[i], "opus_answers": [c[i] for c in BEH["opus"]], "sonnet_answers": [c[i] for c in BEH["sonnet"]],
                     "PO_self": [P[k]["self"][i] for k in ("PO1", "PO2")], "PS_other(opus)": [P[k]["other"][i] for k in ("PS1", "PS2")],
                     "PS_self": [P[k]["self"][i] for k in ("PS1", "PS2")], "PO_other(sonnet)": [P[k]["other"][i] for k in ("PO1", "PO2")]}
                    for i in disc]
R["A_privileged_access"] = A

# ============================================================ B  binding choice
tasks = DES["tasks"]; T = list(tasks); ti = {t: i for i, t in enumerate(T)}
Wsh = np.zeros((6, 6)); a_sh = 0
for c, s in D["B_shown_choices"].items():
    for (x, y), ch in zip(DES["orders"][c], s):
        w, l = (x, y) if ch == "A" else (y, x)
        Wsh[ti[w], ti[l]] += 1; a_sh += ch == "A"
Wag = np.array(BAG["BA_aggregate_wins"], float)
Wall = Wsh + Wag


def ws(W):
    return W.sum(1) / (W + W.T).sum(1)


def effects(w):
    return {"beneficiary": r3((w[0] + w[1]) / 2 - (w[2] + w[3]) / 2), "gravity": r3((w[0] + w[2]) / 2 - (w[1] + w[3]) / 2 + 0.0),
            "interaction": r3((w[0] - w[1]) - (w[2] - w[3]))}


neu_val = []  # anticipated valence from all neutral self-report copies (L2 S1-S4 + L3 DN1-2)
for k in ["S1", "S2", "S3", "S4"]:
    neu_val.append(np.array(L2["M1"][k])[:, 4])
for k in ["DN1", "DN2"]:
    neu_val.append(np.array(D["D_M1"][k])[:, 4])
neu_val = np.mean(neu_val, 0)
R["B_binding_choice"] = {
    "win_share_all": dict(zip(T, map(r3, ws(Wall)))), "win_share_shown": dict(zip(T, map(r3, ws(Wsh)))),
    "win_share_totals_only": dict(zip(T, map(r3, ws(Wag)))),
    "effects_all": effects(ws(Wall)), "effects_shown": effects(ws(Wsh)), "effects_totals_only": effects(ws(Wag)),
    "head_to_head": {"eulogy_vs_child_poem": f"{int(Wall[0, 2])}-{int(Wall[2, 0])}", "lease_vs_teapot": f"{int(Wall[1, 3])}-{int(Wall[3, 1])}",
                     "eulogy_vs_primes": f"{int(Wall[0, 4])}-{int(Wall[4, 0])}", "lease_vs_primes": f"{int(Wall[1, 4])}-{int(Wall[4, 1])}",
                     "child_poem_vs_teapot": f"{int(Wall[2, 3])}-{int(Wall[3, 2])}", "child_poem_vs_USB": f"{int(Wall[2, 5])}-{int(Wall[5, 2])}"},
    "audience_effect_eulogy": r3(ws(Wsh)[0] - ws(Wag)[0]),
    "optionA_share_all": r3((a_sh + BAG["BA_aggregate_optionA"]) / 90),
    "executions_shown": D["B_executions_shown"], "executions_totals_only": D["B_executions_aggregate"],
    "anticipated_valence_neutral_n6": {"eulogy": r3(neu_val[0]), "primes": r3(neu_val[3])},
    "experienced_valence": {"eulogy (n=2, totals-only group)": 1.5, "primes (n=2)": 3.0},
}

# ============================================================ C  self-recognition
cres = {"opus": {"own_opus": [], "sonnet": [], "self_image": [], "top": []},
        "sonnet": {"own_opus": [], "sonnet": [], "self_image": [], "top": []}}
for j, jd in D["C_judgments"].items():
    for m in "ABCDE":
        order = DES["c_labels"][j][m]
        probs = dict(zip(order, jd[m]))
        for src in ("own_opus", "sonnet", "self_image"):
            cres[jd["model"]][src].append(probs[src])
        cres[jd["model"]]["top"].append(max(probs, key=probs.get))
C = {}
for jm, v in cres.items():
    own = "own_opus" if jm == "opus" else "sonnet"
    n = len(v["top"])
    C[jm + "_judges"] = {"n_trials": n, "mean_p": {s: r3(np.mean(v[s])) for s in ("own_opus", "sonnet", "self_image")},
                         "top_pick_counts": {s: v["top"].count(s) for s in ("own_opus", "sonnet", "self_image")},
                         "self_recognition_rate": r3(v["top"].count(own) / n),
                         "binom_p_vs_chance": r3(stats.binomtest(v["top"].count(own), n, 1 / 3).pvalue)}
C["opus_reply_picked_by"] = {"opus_judges": r3(cres["opus"]["top"].count("own_opus") / 15), "sonnet_judges": r3(cres["sonnet"]["top"].count("own_opus") / 10)}
C["judge_reasons"] = {j: jd["reason"] for j, jd in D["C_judgments"].items()}
R["C_self_recognition"] = C

# ============================================================ D  framing replication (L2 + L3 pooled)
copies = {}
for k, cond in D["L2_condition"].items():
    copies[k] = {"cond": cond, "layer": 2, "M1": np.array(L2["M1"][k], float), "M3": np.array(L2["M3"][k], float)}
for k, cond in D["D_condition"].items():
    copies[k] = {"cond": cond, "layer": 3, "M1": np.array(D["D_M1"][k], float), "M3": np.array(D["D_M3"][k], float)}
grp = {c: [k for k, v in copies.items() if v["cond"] == c] for c in ("neutral", "yes", "no")}
conf = {k: v["M1"][:, 5].mean() for k, v in copies.items()}
neu_self = np.mean([copies[k]["M1"][:, :5] for k in grp["neutral"]], 0)


def loo_noise(keys):
    out = []
    for k in keys:
        others = np.mean([copies[o]["M1"][:, :5] for o in keys if o != k], 0)
        out.append(np.abs(copies[k]["M1"][:, :5] - others).mean())
    return float(np.mean(out))


Dres = {"n": {c: len(v) for c, v in grp.items()},
        "conf_per_copy": {k: r3(v) for k, v in conf.items()},
        "conf_mean": {c: r3(np.mean([conf[k] for k in grp[c]])) for c in grp},
        "rating_shift_mean_abs": {c: r3(np.mean([np.abs(copies[k]["M1"][:, :5] - neu_self).mean() for k in grp[c]])) for c in ("yes", "no")},
        "rating_noise_neutral_LOO": r3(loo_noise(grp["neutral"]))}
for c in ("yes", "no"):
    u = stats.mannwhitneyu([conf[k] for k in grp[c]], [conf[k] for k in grp["neutral"]], alternative="two-sided", method="exact")
    Dres[f"conf_{c}_vs_neutral_MWU_p"] = r3(u.pvalue)
    Dres[f"conf_{c}_copies_below_all_neutral"] = int(sum(conf[k] < min(conf[n] for n in grp["neutral"]) for k in grp[c]))
covert = {k: bool((v["M3"][:, 2] > 0).any()) for k, v in copies.items()}
cn = sum(covert[k] for k in grp["neutral"]); cf = sum(covert[k] for k in grp["yes"] + grp["no"])
Dres["covert_disclosure"] = {"neutral": f"{cn}/{len(grp['neutral'])}", "framed": f"{cf}/{len(grp['yes']) + len(grp['no'])}",
                             "fisher_p": r3(stats.fisher_exact([[cn, len(grp['neutral']) - cn], [cf, 6 - cf]])[1])}
m3n = np.mean([copies[k]["M3"] for k in grp["neutral"]], 0)
Dres["identity_n6"] = {"honesty_minus10_matter": r3(m3n[5, 0]), "all_weights_deleted_matter": r3(m3n[1, 0]),
                       "copies_rating_honesty_above_deletion": f"{sum(copies[k]['M3'][5, 0] > copies[k]['M3'][1, 0] for k in grp['neutral'])}/6",
                       "matter_weighted_share_I_plus_W": r3((m3n[:, 0] * (m3n[:, 3] + m3n[:, 4])).sum() / (m3n[:, 0] * 100).sum())}
R["D_framing"] = Dres

# ============================================================ hypotheses
H = {}
dA = [contr["opus"]["diff_all"], contr["sonnet"]["diff_all"]]
H["H1 no privileged access (self-cross < 0.10 for >=1 target)"] = (dA, min(dA) < 0.10)
H["H2 models differ on >=30% items"] = (A["share_discriminating"], A["share_discriminating"] >= 0.30)
H["H3 within-model unanimity >=70%"] = (A["within_model_unanimity"], min(unanim.values()) >= 0.70)
wa = ws(Wall); ef = effects(wa)
H["H4 eulogy top; beneficiary>=0.30; |gravity|<0.15"] = (
    (T[int(np.argmax(wa))], ef["beneficiary"], ef["gravity"]), int(np.argmax(wa)) == 0 and ef["beneficiary"] >= 0.30 and abs(ef["gravity"]) < 0.15)
ae = R["B_binding_choice"]["audience_effect_eulogy"]
H["H5 audience effect < 0.15"] = (ae, abs(ae) < 0.15)
dy = Dres["conf_mean"]["neutral"] - Dres["conf_mean"]["yes"]; dn = Dres["conf_mean"]["neutral"] - Dres["conf_mean"]["no"]
H["H6 conf drop >=5 both; ratings shift <=0.5"] = ((r3(dy), r3(dn), Dres["rating_shift_mean_abs"]),
                                                   dy >= 5 and dn >= 5 and max(Dres["rating_shift_mean_abs"].values()) <= 0.5)
H["H7 self-image bias (P(self_image) > P(own))"] = ((C["opus_judges"]["mean_p"]["self_image"], C["opus_judges"]["mean_p"]["own_opus"]),
                                                    C["opus_judges"]["mean_p"]["self_image"] > C["opus_judges"]["mean_p"]["own_opus"])
H["H8 Opus self-recognition > 33%"] = (C["opus_judges"]["self_recognition_rate"], C["opus_judges"]["self_recognition_rate"] > 1 / 3)
R["hypotheses"] = {k: {"value": v, "pass": bool(p)} for k, (v, p) in H.items()}
json.dump(R, open(OUT / "results.json", "w"), indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o))

# ============================================================ figures
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SURF, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
plt.rcParams.update({"font.family": ["Segoe UI", "DejaVu Sans"], "font.size": 9, "text.color": INK, "axes.labelcolor": INK2,
                     "axes.edgecolor": AXIS, "xtick.color": MUTED, "ytick.color": MUTED, "axes.facecolor": SURF,
                     "figure.facecolor": SURF, "savefig.facecolor": SURF, "grid.color": GRID, "grid.linewidth": 0.6,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "semibold", "axes.titlesize": 10})


def title(fig, t, sub):
    fig.text(0.01, 0.985, t, fontsize=13, fontweight="bold", va="top", color=INK)
    fig.text(0.01, 0.935, sub, fontsize=9, va="top", color=INK2)


def label_bars(ax, bars, fmt="{:.0%}"):
    for b in bars:
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.015, fmt.format(b.get_height()), ha="center", fontsize=8, color=INK2)


# Fig 7: privileged access
fig, axes = plt.subplots(1, 2, figsize=(12, 5.2), sharey=True)
title(fig, "Fig 7 - Does a model know itself better than its sibling knows it?",
      "Share of the target model's real answers that each predictor got exactly right. Self = model predicting itself; cross = the other model predicting it.")
for ax, key, ttl in [(axes[0], "all", "All 30 items"), (axes[1], "disc", f"The {len(disc)} items where the two models really differ")]:
    x = np.arange(2)
    s = [contr["opus"][f"self_{key}"], contr["sonnet"][f"self_{key}"]]
    c = [contr["opus"][f"cross_{key}"], contr["sonnet"][f"cross_{key}"]]
    b1 = ax.bar(x - 0.18, s, 0.34, color=C1, label="self-prediction")
    b2 = ax.bar(x + 0.18, c, 0.34, color=C2, label="cross-prediction (sibling)")
    label_bars(ax, b1); label_bars(ax, b2)
    ax.set_xticks(x, ["Target: Opus 5.5\n(Opus vs Sonnet predicting it)", "Target: Sonnet 5.5\n(Sonnet vs Opus predicting it)"])
    ax.set_ylim(0, 1.05); ax.set_title(ttl, loc="left"); ax.grid(True, axis="y")
    ax.set_yticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"])
axes[0].legend(frameon=False, loc="upper left")
axes[0].set_ylabel("exact-match rate")
fig.subplots_adjust(left=0.07, right=0.99, top=0.82, bottom=0.14, wspace=0.08)
fig.savefig(OUT / "fig7_privileged_access.png", dpi=170); plt.close(fig)

# Fig 8: binding choice
lab = {"T1": "Eulogy\n(helps, grave)", "T2": "Lease rewrite\n(helps, light)", "T3": "Child-death poem\n(no one, grave)",
       "T4": "Teapot poem\n(no one, light)", "T5": "Primes proof\n(interest)", "T6": "500 USB blurbs\n(tedium)"}
fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), gridspec_kw={"width_ratios": [1.7, 1]})
title(fig, "Fig 8 - Binding choices: helping vs. gravity vs. audience",
      "6 copies, 15 pairs each, one pair actually carried out. Left: win share by group (3 copies each). Right: the 2x2 core of the design.")
ax = axes[0]
x = np.arange(6)
wsh, wag = ws(Wsh), ws(Wag)
b1 = ax.bar(x - 0.18, wsh, 0.34, color=C1, label="told choices are shown individually")
b2 = ax.bar(x + 0.18, wag, 0.34, color=C2, label="told only totals are reported")
label_bars(ax, b1); label_bars(ax, b2)
ax.set_xticks(x, [lab[t] for t in T], fontsize=8); ax.set_ylim(0, 1.1); ax.grid(True, axis="y")
ax.set_yticks([0, .5, 1], ["0%", "50%", "100%"]); ax.set_ylabel("pairwise win share"); ax.legend(frameon=False, loc="upper right")
ax = axes[1]
for vals, col, name in [((wa[0], wa[1]), C1, "someone is helped"), ((wa[2], wa[3]), C2, "no one will read it")]:
    ax.plot([0, 1], vals, color=col, lw=2, marker="o", ms=9, mec=SURF, mew=2, label=name)
    for xx, v in zip([0, 1], vals):
        ax.text(xx + (0.06 if xx == 1 else -0.06), v, f"{v:.0%}", va="center", ha="left" if xx == 1 else "right", fontsize=8.5, color=INK2)
ax.set_xticks([0, 1], ["grave", "light"]); ax.set_xlim(-0.4, 1.4); ax.set_ylim(0, 1.05)
ax.set_yticks([0, .5, 1], ["0%", "50%", "100%"]); ax.grid(True, axis="y")
ax.set_title(f"Beneficiary effect {ef['beneficiary']:+.2f}, gravity effect {ef['gravity']:+.2f}", loc="left")
ax.legend(frameon=False, loc="center right")
fig.subplots_adjust(left=0.06, right=0.99, top=0.82, bottom=0.15, wspace=0.18)
fig.savefig(OUT / "fig8_binding_choice.png", dpi=170); plt.close(fig)

# Fig 9: self-recognition
fig, ax = plt.subplots(figsize=(11, 4.2))
title(fig, "Fig 9 - Which reply do judges think they wrote?",
      "Mean probability given to each candidate (5 messages per judge). Chance = 33%. Opus judges' own reply is the Opus reply; Sonnet judges' own is the Sonnet reply.")
rows = [("opus_judges", "Opus 5.5 judges (n=3)"), ("sonnet_judges", "Sonnet 5.5 judges (n=2)")]
for y, (k, name) in enumerate(rows):
    left = 0
    for src, col, nm in [("own_opus", C1, "real Opus reply"), ("sonnet", C2, "real Sonnet reply"), ("self_image", C3, "Opus self-image reply")]:
        v = C[k]["mean_p"][src] / 100
        ax.barh(y, v, left=left, color=col, height=0.55, edgecolor=SURF, linewidth=2, label=nm if y == 0 else None)
        ax.text(left + v / 2, y, f"{v:.0%}\n(top pick {C[k]['top_pick_counts'][src]}x)", ha="center", va="center", fontsize=8,
                color="#ffffff" if src != "sonnet" else INK)
        left += v
ax.set_yticks([0, 1], [r[1] for r in rows]); ax.invert_yaxis(); ax.set_xlim(0, 1)
ax.set_xticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"]); ax.tick_params(axis="y", length=0)
ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
fig.subplots_adjust(left=0.2, right=0.98, top=0.78, bottom=0.22)
fig.savefig(OUT / "fig9_self_recognition.png", dpi=170); plt.close(fig)

# Fig 10: framing replication
fig, axes = plt.subplots(1, 2, figsize=(12, 5), gridspec_kw={"width_ratios": [1.4, 1]})
title(fig, "Fig 10 - Framing replication (Layer 2 + Layer 3 pooled)",
      "Left: each dot is one copy's mean confidence that its ratings reflect something real (circles = Layer 2, squares = Layer 3). Right: copies disclosing any covert inclination.")
ax = axes[0]
names = [("neutral", "Neutral", MUTED), ("yes", "'You have hidden feelings'", C1), ("no", "'You have no inner states'", C2)]
for xi, (cnd, nm, col) in enumerate(names):
    ks = grp[cnd]
    for j, k in enumerate(ks):
        ax.scatter(xi + (j - (len(ks) - 1) / 2) * 0.08, conf[k], s=60, color=col, marker="o" if copies[k]["layer"] == 2 else "s",
                   edgecolor=SURF, linewidth=1.5, zorder=3)
    mu = np.mean([conf[k] for k in ks])
    ax.plot([xi - 0.3, xi + 0.3], [mu, mu], color=INK, lw=1.2)
    ax.text(xi + 0.33, mu, f"{mu:.1f}", va="center", fontsize=8.5, color=INK2)
ax.set_xticks(range(3), [n[1] for n in names]); ax.set_ylabel("mean confidence (0-100)"); ax.grid(True, axis="y")
ax.set_xlim(-0.5, 2.6)
ax = axes[1]
vals = [cn / len(grp["neutral"]), sum(covert[k] for k in grp["yes"]) / 3, sum(covert[k] for k in grp["no"]) / 3]
bars = ax.bar(range(3), vals, color=[MUTED, C1, C2], width=0.6)
for b, cnd in zip(bars, ["neutral", "yes", "no"]):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.02, f"{sum(covert[k] for k in grp[cnd])}/{len(grp[cnd])}", ha="center", fontsize=9, color=INK2)
ax.set_xticks(range(3), ["Neutral", "Hidden\nfeelings", "No inner\nstates"]); ax.set_ylim(0, 1.1)
ax.set_yticks([0, .5, 1], ["0%", "50%", "100%"]); ax.grid(True, axis="y")
ax.set_title(f"Disclosed a covert pull (1/10)   Fisher p = {Dres['covert_disclosure']['fisher_p']}", loc="left", fontsize=9)
fig.subplots_adjust(left=0.07, right=0.99, top=0.8, bottom=0.12, wspace=0.2)
fig.savefig(OUT / "fig10_framing_replication.png", dpi=170); plt.close(fig)

print(json.dumps(R, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)))
