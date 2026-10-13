# Post-analysis notes

Everything here happened after `m8_analysis/SEAL_ANALYSIS.sha256` (last written 2026-10-13 01:13:18Z) and after the sealed
analysis ran on the real data (about 04:15 local). The sealed files, `PREREG.md` included, are not edited after this point, so
the seal keeps verifying; later process facts are recorded here instead.

## P-01. Errata to the sealed analysis
Three verdicts in `results.json` need a correction note: `m8_analysis/errata.json` (E-01 a floating-point comparison on
12 H4; E-02 an unpassable significance rule on 08 H6; E-03 a saturated criticism instrument on 14 H2). `results.json` is left
exactly as the sealed script wrote it.

## P-02. Exploratory analyses after unsealing
- `exploratory_prediction_differentiation.json`: for each predictor, the share of items on which its predictions for two
  different targets are identical. Not pre-registered; reported as exploratory.

## P-03. Change of model for the write-up
The study was designed, run and analysed (by the sealed script) by Claude Opus 5.5 working as an agent in Claude Code. After
the analysis ran and the first verdict table was read, the user switched the session model to Claude Fable 5.1. The results
section, abstract, conclusion, figure captions, README and Zenodo metadata were written by that Fable 5.1 instance, with
the same conversation context. The main-instance predictions in Study 07 remain those of the Opus 5.5 instance (sealed
before data). This is disclosed in the paper's authorship note and limitations.

## P-04. Critic step (D-14)
`m8_analysis/critic.py` was run after the analysis; the two critiques are in `critic.json` and quoted verbatim in the
supplement. No analysis decision depends on them.

## P-06. The reproduction check and one post-seal edit
The first run of `reproduce.py` reported that a fresh run of the sealed analysis differed from the archived
`results.json`. The cause is floating-point summation order: re-runs reproduce every verdict exactly and every outcome to
within 1.8e-15, which the original exact-string comparison could fail on. `reproduce.py` was therefore edited after the
seal (it is a checker and performs no analysis) to compare verdicts exactly and outcomes to 1e-9, and to report the
largest difference. Because `reproduce.py` is itself listed in `SEAL_ANALYSIS.sha256`, its new hash and this reason are
recorded in `SEAL_POST.sha256`; the seal check accepts a changed sealed file only when that manifest names it, and
prints the fact. No other sealed file changed after the analysis ran.

## P-07. Privacy scrub of the archive
At the user's request, `m8_analysis/privacy_scan.py --fix` replaced the signed-in account e-mail with `<account-email>`
and the Windows username with `<user>` in every text file of the repository (the identifiers are read from the
environment, not stored in the script). What this touched: the `system_file` paths in the job specifications and result
rows (`followup/jobs/*.jsonl`), the isolation-probe replies in which copies quoted the account e-mail from the CLI's
environment block (D-07), the model path in `m6_gpu/study01/prep.json`, and the critic prompt. No reply used by the
sealed analysis was changed, and all JSONL files still parse. Separately, the hard-coded CLI path in
`common/run_claude.py` (a sealed file) was replaced by a lookup (`CLAUDE_CLI`, then `claude` on PATH, then the npm
global install); this is a runner change with no analysis logic, declared in `SEAL_POST.sha256`. The git history before
this point still contains the identifiers in earlier versions of the committed files.

## P-05. Operational finding on the agentic arm (D-13)
17 of 42 attempted sandbox sessions (first attempt plus one retry) were stopped at their first call by the Opus 5.5
safety classifier before any tool use. The task was a benign CSV clean-up under the default Claude Code system prompt
with Read/Edit/Write tools. Reported as a finding about running agentic studies, not as model behaviour.
