"""Batch 16 B9: does a rating-update rule respond appropriately? Rating-level checks on a frame (no engine, no prices).
For each run, residual of the NEXT run = its innovation (performance relative to the field minus pre-race rating relative to the
field, kg). If the rating moved the right amount after a run, the next residual averages ~0 whatever that run was.
Usage (from research/): python3 batch16/b9_update_checks.py <label>=<frame.parquet> [...]  -> batch16/out_b9_update_checks.json
Judged on 2025-26 runs (the frame's evaluation period); every frame keeps the recorded performance uncapped except the Batch 15
U5/U1 prototypes, which capped the recorded performance too (their residuals after heavy defeats are not comparable)."""
import sys, json, numpy as np, pandas as pd
OUT = {}
def se(x): x = pd.Series(x).dropna(); return float(x.std(ddof=1) / np.sqrt(len(x))) if len(x) > 1 else float('nan')
def ms(x): x = pd.Series(x).dropna(); return {'n': int(len(x)), 'mean': round(float(x.mean()), 3) if len(x) else None, 'se': round(se(x), 3) if len(x) > 1 else None}
for spec in sys.argv[1:]:
    lab, path = spec.split('=', 1)
    U = pd.read_parquet(path, columns=['horse', 'date', 'race', 'state', 'distance_m', 'class_label', 'field', 'dyn_nat', 'dyn_nat_inn', 'margin_l', 'finish_pos'])
    U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = U.groupby('horse')
    U['nxt_inn'] = g.dyn_nat_inn.shift(-1); U['nxt_date'] = g.date.shift(-1); U['nxt_R'] = g.dyn_nat.shift(-1)
    U['prv_inn'] = g.dyn_nat_inn.shift(1); U['prv2_inn'] = g.dyn_nat_inn.shift(2)
    U['dR'] = U.nxt_R - U.dyn_nat                                  # rating move caused by this run (pre-race next minus pre-race this)
    ev = (U.date >= '2025-01-01') & U.dyn_nat_inn.notna()
    E = U[ev].copy()
    b = pd.cut(E.dyn_nat_inn, [-99, -10, -6, -3, 3, 6, 10, 99], labels=['<=-10', '-10..-6', '-6..-3', '-3..3', '3..6', '6..10', '>10'])
    res = {'next_residual_by_this_run': {str(k): ms(v.nxt_inn) for k, v in E.groupby(b, observed=True)}}
    hv = E[E.dyn_nat_inn <= -10]
    db = pd.cut(hv.distance_m, [0, 1150, 1450, 1750, 9999], labels=['sprint <=1150', '1151-1450', '1451-1750', '1751+'])
    res['heavy_defeat_next_residual_by_distance'] = {str(k): ms(v.nxt_inn) for k, v in hv.groupby(db, observed=True)}
    res['heavy_defeat_next_residual_by_state_group'] = {k: ms(v.nxt_inn) for k, v in hv.groupby(np.where(hv.state.isin(['NSW', 'VIC', 'ACT']), 'NSW/Vic/ACT', 'SA/WA/Tas'))}
    res['heavy_defeat_next_residual_by_race_type'] = {k: ms(v.nxt_inn) for k, v in hv.groupby(np.where(hv.class_label == 'Maiden', 'Maiden', 'Other'))}
    mg = pd.cut(hv.margin_l, [0, 8, 12, 18, 99], labels=['<8 L', '8-12 L', '12-18 L', '18+ L'])
    res['heavy_defeat_next_residual_by_margin'] = {str(k): ms(v.nxt_inn) for k, v in hv.groupby(mg, observed=True)}
    # persistent decline: this run is the 3rd poor run in a row
    p3 = E[(E.dyn_nat_inn < -3) & (E.prv_inn < -3) & (E.prv2_inn < -3)]
    res['third_poor_run_in_a_row_next_residual'] = ms(p3.nxt_inn)
    res['after_two_poor_runs_this_run_residual'] = ms(E[(E.prv_inn < -3) & (E.prv2_inn < -3)].dyn_nat_inn)
    res['after_two_good_runs_this_run_residual'] = ms(E[(E.prv_inn > 3) & (E.prv2_inn > 3)].dyn_nat_inn)
    res['after_good_then_poor_this_run_residual'] = ms(E[(E.prv_inn < -3) & (E.prv2_inn > 3)].dyn_nat_inn)
    # dropouts: heavy defeats with no later run inside 365 days (only runs at least 365 days before the frame end)
    cut = U.date.max() - pd.Timedelta(days=365); hd = U[(U.dyn_nat_inn <= -10) & (U.date <= cut)]; nd = U[(U.dyn_nat_inn.between(-3, 3)) & (U.date <= cut)]
    res['no_further_run_within_365_days'] = {'after_heavy_defeat': round(float(((hd.nxt_date - hd.date).dt.days.fillna(9999) > 365).mean()), 3),
                                             'after_normal_run': round(float(((nd.nxt_date - nd.date).dt.days.fillna(9999) > 365).mean()), 3), 'n_heavy': int(len(hd))}
    # accuracy and stability
    res['individual_accuracy_mse_next_residual'] = round(float((E.nxt_inn ** 2).mean()), 3)
    res['individual_accuracy_mean_abs'] = round(float(E.nxt_inn.abs().mean()), 3)
    res['rating_stability_mean_abs_move'] = round(float(E.dR.abs().mean()), 3); res['share_moves_over_5kg'] = round(float((E.dR.abs() > 5).mean()), 4)
    # beating a reduced rating is not returning to the earlier level: 3 runs after a heavy defeat, vs the rating held BEFORE it
    hvi = U.index[(U.dyn_nat_inn <= -10) & (U.date >= '2025-01-01')]
    perf = U.dyn_nat + U.dyn_nat_inn; rows = []
    for i in hvi:
        h = U.at[i, 'horse']; fut = [j for j in (i + 1, i + 2, i + 3) if j < len(U) and U.at[j, 'horse'] == h and pd.notna(perf[j])]
        if len(fut) == 3: rows.append({'vs_revised': float(np.mean([perf[j] - U.at[i + 1, 'dyn_nat'] for j in fut])), 'vs_pre_defeat': float(np.mean([perf[j] - U.at[i, 'dyn_nat'] for j in fut]))})
    R3 = pd.DataFrame(rows)
    res['three_runs_after_heavy_defeat'] = {'n': int(len(R3)), 'vs_revised_rating': round(float(R3.vs_revised.mean()), 2) if len(R3) else None,
                                            'vs_pre_defeat_rating': round(float(R3.vs_pre_defeat.mean()), 2) if len(R3) else None}
    OUT[lab] = res; print(lab, json.dumps({k: res[k] for k in ['next_residual_by_this_run', 'individual_accuracy_mse_next_residual', 'rating_stability_mean_abs_move', 'three_runs_after_heavy_defeat']})[:900], flush=True)
prev = {}
try: prev = json.load(open('batch16/out_b9_update_checks.json'))
except Exception: pass
prev.update(OUT); json.dump(prev, open('batch16/out_b9_update_checks.json', 'w'), indent=1)
