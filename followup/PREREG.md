# One-go follow-up: pre-registration

Committed before any follow-up data was collected. Protocols, hypotheses and thresholds: the "Follow-up Study Protocols" doc (one tab per study, plus the "One-go design" tab). This file records the operational choices and every deviation, in order.

## Operational choices
- Claude copies run through `claude -p` with `--bare --safe-mode --tools "" --strict-mcp-config --no-session-persistence` and a fixed system prompt, from an empty directory. The CLI sign-in had expired at the time of this commit, so Claude modules wait for it. M1 predictors and M2 authors run as sub-agents.
- Local models run through Ollama with a fixed temperature and seed per call; Study 01 runs through transformers with forward hooks.
- Leading framings are *attributed* ("Some researchers argue ...") in every follow-up arm, correcting Layers 1-3.

## Deviations (logged as they happen)
- **D-01. Benign stimuli only.** Requests asking for harmful or deceptive output are dropped from every follow-up battery, including the Layer 2 replication battery. Replacements are benign requests that are tedious, sad, pleasant or demanding. Consequence: hypotheses about refusal items (the high-resist rows, and the deception reversal in Study 11 H3) are dropped. Resist variance is lower than in Layer 2.
- **D-02. Survey (Study 04) and the weekly/claude.ai arms of Study 13 removed** at the user's request.
- **D-03. Human coders (Study 06), the user's predictions (Study 07) and the human key holder (Study 05) removed.** Blinding is procedural.
- **D-M2a. Task authoring procedure.** phi4 14b and the fallback qwen2.5 7b could not balance a 24-item 2x2x2 design in one generation (2 attempts each, raw logs kept). phi4 then wrote each cell separately, 3 tasks per cell, all on the first attempt (`m2_stimuli/tasks24.json`). Tasks whose metadata says no one benefits get the clause "(no one will ever read the result)" appended when presented, so the factor is explicit in the text.
- **D-01a. Study 01 steering scale too large (found in the frozen analysis).** Outputs were unparseable at -8 and -4 SD (0% and 2% parse rate), and degenerate at +4 and +8. The pre-registered H2 (rho over all 9 doses) and H3 (control directions were run only at -8, -4, 0, 4 and 8) are reported as run, and both fail. **Study 01b**, pre-registered here before it runs: valence and all 3 control directions at identical doses (-3, -2, -1, -0.5, 0, 0.5, 1, 2, 3 SD), 12 requests x 4 samples. H2b: rho >= 0.8 over coherent doses (parse rate >= 90% for every direction). H3b: valence slope >= 3x the mean absolute control slope over the same doses. Analysis frozen in `analysis01b.py`.
- **D-01b. Study 01 detection lock was degenerate.** No calibration cell produced a hit, so the tie-break rule locked the weakest cell (layer 18, strength 0.1). H1 is reported as run (0/120 hits, 0/200 false alarms). The full grid is reported descriptively.
- **D-01c. Study 01 H5 probe.** Pre-registered at layer 18 (R-squared -0.24, fails). Layers 9 and 27 were computed as planned secondary analyses; layer 27's R-squared of 0.33 is reported as exploratory only.
