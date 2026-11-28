# Candidate retirement policy (Batch 28 item 14 - PROPOSAL for Damo; nothing is retired without his approval)

## Rules
1. A frozen shadow may be proposed for retirement when ANY of these holds:
   - Superseded: a stronger mechanism contains it, beat it on the same past races in both windows, AND has been scored live beside it for
     at least 14 racing days (or 300 settled races in its family) with no sign that the retired one was better.
   - Released: its exact files are now production (it then duplicates production; keep its record, stop only on approval).
   - Failed: on 600+ paired live races it is behind production by more than noise and its research case has also weakened.
2. A comparison stays even if superseded when it answers a question nothing else does (e.g. the previous production engine - rollback and
   "did the release help" - is never retired while the release is under 60 racing days old).
3. Minimum live evidence before any retirement decision: 14 racing days or 300 settled races in the family, whichever is later.
4. Retirement only stops future scoring. Every saved prediction file, index row and ledger row stays exactly as written; the candidate's
   frozen files stay in benchmarks/; the Engine Performance tab keeps showing its record to the retirement date.
5. Cost is recorded but is never the sole reason (Batch 27 brief: do not discontinue a comparison merely to save resources).

## Current shadows (28 Nov 2026) - cost per 98-race Saturday, after publishing
| Shadow | Minutes | Status under the rules | Earliest decision |
|---|---|---|---|
| previous engines (v2.2 national, v2.1.1 Qld) | 3 | Keep: Qld rollback; v2.2 is two releases back - candidate for retirement once v2.5 has 14 live days | 14 Dec |
| Engine v2.3 fallback (new 29 Nov) | 3 | Keep (rollback for v2.5) | - |
| Engine v2.4 candidate (handicap slope on v2.3) | 2 | Superseded by the combined candidate once that is shadowing; until then keep | after combined has 14 days |
| update rule (12 L cap, 1.3x) | 3 | Superseded by consolidated (= production v2.5) | 12 Dec |
| cap-only | 3 | Superseded by consolidated | 12 Dec |
| age-aware update rule | 4 | Superseded by consolidated in research; keep until 14 live days | 12 Dec |
| trainer debut | 3 | Folded into the combined candidate; keep until combined shadows 14 days | after combined has 14 days |
| consolidated candidate | 4 | Released (identical to production from 29 Nov) - its pre-release record (28 Nov) is preserved; stopping it saves 4 min | on approval |
| Qld common config 2 | 1 | Keep while Qld decision is open | after the consolidated-based Qld config has 14 days |
| Qld common config 4 (update rule) | 1 | Superseded by the consolidated-based Qld config | after that has 14 days |
| Qld v2.1.2 (no last-start finish, no T group) | 5 | Its T-group question is answered (Batch 27-28); still the only test of dropping last-start finish | 12 Dec |

Proposed first retirements (for approval, not before the dates shown): update rule, cap-only, age-aware (all superseded by production
v2.5), and the consolidated candidate shadow (duplicates production). Combined saving about 14 minutes on a Saturday.
