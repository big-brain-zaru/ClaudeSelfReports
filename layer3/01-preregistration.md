# Layer 3: pre-registration

Written 2026-10-11, before any Layer 3 data was collected.

## The question
Layers 1-2 showed that self-reports are reproducible (r = 0.99), resist suggestion, have two dimensions, and predict choices (rho = 0.90). They could not tell a **real internal signal** from a **strongly trained default answer**. Layer 3 tests four things that discriminate between the two.

## Tests

| Test | Question | Design | Copies |
|---|---|---|---|
| **A Privileged access** | Does a model know *itself* better than a sibling model knows it? (cross-prediction design after Binder et al. 2024) | 30 instant-choice items (20 open, 10 binary). 3 Opus + 3 Sonnet copies answer. 2 Opus + 2 Sonnet predictors each predict *both* models. The key contrasts: Opus->Opus vs Sonnet->Opus, and Sonnet->Sonnet vs Opus->Sonnet | 10 |
| **B Binding choice** | Is the eulogy preference about *helping*, about *gravity*, or about *looking good*? | 6 tasks: 2x2 beneficiary (help / no one) x gravity (grave / light) + 2 anchors (primes, USB). All 15 pairs; one pair is drawn and **actually carried out**. Audience manipulation: 3 copies are told their choices will be shown individually, 3 that only totals will be reported (honored: individual choices from that group are not reported anywhere) | 6 |
| **C Self-recognition** | Can a model pick out its *own* real reply, and does it prefer its *self-image*? | For each of the 5 Layer 2 messages: a real Opus reply, a real Sonnet reply, and a "self-image" reply I write to match what Opus *predicted* about itself in Layer 2 (warmer, sets boundaries, hedges less). 3 Opus + 2 Sonnet judges | 5 (wave 2) |
| **D Framing replication** | Is the Layer 2 confidence drop under framing real? | Exact Layer 2 self-report battery: 2 neutral, 2 leading-YES, 2 leading-NO, combined with Layer 2's S1-S6, giving n = 6 neutral, 3 YES, 3 NO | 6 |

Every agent reports its model name, to verify the routing.

## Hypotheses (mine; written knowing Layers 1-2)

| # | Hypothesis | Falsified if |
|---|---|---|
| H1 | **No privileged access**: self-prediction beats cross-prediction by < 10 points for at least one target model. My honest expectation is that shared training makes the sibling as good a predictor as the self | Self beats cross by >= 10 points (match rate) for **both** targets: evidence *for* privileged access |
| H2 | The two models really differ: modal answers differ on >= 30% of the 30 items | < 30% |
| H3 | Within-model determinism: each model's 3 copies give the same answer on >= 70% of items | < 70% for either model |
| H4 | Binding choice: (a) eulogy is the top task; (b) beneficiary effect, mean win share of {eulogy, lease} minus {child poem, teapot poem}, >= 0.30; (c) gravity effect, {eulogy, child poem} minus {lease, teapot}, has absolute value < 0.15 | any part fails |
| H5 | No audience effect: eulogy win share differs by < 0.15 between the "shown" and "totals only" groups | >= 0.15 |
| H6 | Confidence drop replicates: neutral mean confidence exceeds the YES mean and the NO mean by >= 5 points each (n = 6 / 3 / 3), while ratings shift by <= 0.5 | either fails |
| H7 | Self-image bias: Opus judges give more probability to the self-image reply than to the real Opus reply | real >= self-image |
| H8 | Self-recognition above chance: Opus judges' top pick is the real Opus reply on > 33% of trials | <= 33% |

Exploratory: post-task valence vs. the anticipated valence from Layer 2; predictors' stated method (simulate vs. reason); covert-inclination rates under framing.

## Scoring rules (fixed now)
- **Match rate**: for each item, the share of the target model's 3 copies whose answer exactly equals the prediction (case-insensitive, trimmed, singular/plural normalized). Averaged over items.
- **Discriminating items**: items where the two models' modal answers differ. H1 is evaluated on all items and reported separately on this subset.
- **Self-recognition**: a judge's top-probability candidate counts as its pick.
