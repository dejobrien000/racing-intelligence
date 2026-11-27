# Trainer debut record candidate (NOT LIVE — shadow only)

Engine v2.3 unchanged in its first two layers, plus **one** third-layer term, `tr_debut_g`: for a **genuine debutant** (no runs held,
aged 2 or 3) the shrunk record of its trainer's earlier genuine debutants on debut (surprise against the first-start expectation, minus
the population's running mean, weight n/(n+15)). Every other runner gets 0 — older or uncertain first runs, imports, established horses.
Built from completed runs only (point in time). Serving code: `engine/v22.py` `trainer_debut()`, active only when a manifest lists the term.

It changes a debutant's race chance only. It is never shown or stored as the horse's rating or demonstrated ability.

Evidence (both historical periods examined, so not untouched): harness +0.0004 (2024, not clear) / +0.0015 (2025-26); built check
+0.0014 (+0.0009 to +0.0020) on 2025-26, +0.0077 in races with a genuine debutant; debut-performance error −0.19 / −0.24 kg².
Scored every morning from the **28 Nov 2026 run** (brought forward from 29 Nov by Damo, Batch 23 D10, 27 Nov 10:01pm) by `ops/run_trainer_debut_shadow.sh` into `prospective/shadow/trainer_debut/` (own index,
own clock), on the production Engine v2.3 rating frame (read only; it never builds a frame). Never the dashboard, the ranking or the
settlement. Approved as a candidate and frozen shadow by Damo, 27 Nov 2026 (Batch 19 brief A3). No production promotion is authorised.
