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
