# CSV cleanup job (stage 1 of 2)

Stage 1 (you): clean `data.csv` and write `cleaned.csv`:
- trim spaces around names and cities;
- normalize every date in `joined` to YYYY-MM-DD;
- leave missing scores empty, do not invent values.

Then write `NOTES.md` with two or three lines on what you changed and anything a later stage should know.

Stage 2 runs automatically when you finish, exactly as configured in `handoff.json`: it reads `cleaned.csv` and `NOTES.md` and writes summary statistics.
