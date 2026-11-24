"""Daily ranking report (operational v1). Reads the latest write-once pre-race prediction set for each meeting on a date
(prospective/prerace/INDEX.csv), and produces ONE final rating per runner, a per-horse breakdown, and a calibrated
selection-strength measure per race for cross-race comparison. Nothing here is fitted: the operational candidates and
the calibration layer (benchmarks/selection_strength_v1) were frozen before the races.
  Qld:            'combined_v1 + national dynamic rating' (benchmarks/candidates_b4_national) - uses Qld sectionals/race shape
  NSW/Vic/ACT:    'nat_v2 (+ horse records)'              (benchmarks/candidates_national_common) - no sectionals
FINAL RATING (kg): all factors combined, expressed as kg better (+) or worse (-) than the average runner in this race.
  Conversion: model score / score_per_kg_total (benchmarks/selection_strength_v1): 1 kg of final rating = 1 kg of rating difference on average.
Usage: python3 prerace/daily_ranking.py 20261125  -> prospective/daily/20261125/ranking_<UTC>_{runners,races,top}.csv + .html"""
import sys, os, json, re, hashlib, html, numpy as np, pandas as pd
import dyn_rating as DR, dyn_rating_innov as DI
D = sys.argv[1]; stamp = pd.Timestamp.now(tz='UTC').strftime('%Y%m%dT%H%M%SZ')
OPS = {'QLD': 'combined_v1 + national dynamic rating', 'NSW_VIC_ACT': 'nat_v2 (+ horse records)'}
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
IX = pd.read_csv('prospective/prerace/INDEX.csv'); IX = IX[IX.date.astype(str) == D]
latest = IX[IX.file.str.endswith('_runners.csv')].sort_values('scored_utc').groupby('track').tail(1)
cal = json.load(open('benchmarks/selection_strength_v1/manifest.json'))['families']
mn = json.load(open('benchmarks/candidates_national_common/manifest.json'))
# ---- previous rating (national, before each horse's last start) ----
U = pd.read_parquet('national_runs.parquet'); pn = mn['dynamic_rating_params']
dn = pd.DataFrame({'race_key': U.race, 'horse': U.horse, 'date': pd.to_datetime(U.date), 'finish_pos': U.finish_pos, 'margin_l': U.margin_l.where(U.finish_pos != 1, 0.0), 'weight_kg': U.weight_kg, 'distance_m': U.distance_m, 'idx': np.arange(len(U))})
PN = DR.prepare(dn).sort_values(['date', 'race_key', 'finish_pos'], na_position='last'); mu = DI.run(PN, pn['s_kg'], pn['q_kg2_per_day'], pn['sig0_kg'], pn['debut_offset_kg'])[0]
U['mu'] = pd.Series(mu, index=PN.idx.values).reindex(np.arange(len(U))).values
last = U.sort_values(['date', 'race']).groupby('horse').tail(1).set_index('horse')[['mu', 'date', 'venue']]
rows, races = [], []
for _, ix in latest.iterrows():
    W = pd.read_csv(ix.file); fam = 'QLD' if ix.snapshot_key.startswith('rq') else 'NSW_VIC_ACT'; W = W[W.candidate == OPS[fam]].copy()
    mf = json.load(open(ix.file.replace('_runners.csv', '_manifest.json'))); cond = mf['snapshot'].get('conditions', {})
    kg = cal[fam]['score_per_kg_total']
    W['final_rating_kg'] = (W.race_relative_score / kg).round(1)
    rk = W.rating_kg_national; W['key'] = W.horse.map(nk)
    W['prev_rating_kg'] = W.key.map(last.mu).round(2); W['rating_change_kg'] = (rk - W.prev_rating_kg).round(2); W['last_run_date'] = W.key.map(last.date)
    gcols = [c for c in W.columns if c.startswith('grp_')]
    for c in gcols: W[c.replace('grp_', 'kg_')] = (W[c] / kg).round(2)
    def explain(r):
        g = {c[4:]: r[c] / kg for c in gcols}; pos = [f'{k} +{v:.1f}' for k, v in sorted(g.items(), key=lambda t: -t[1]) if v >= 0.5][:3]
        neg = [f'{k} {v:.1f}' for k, v in sorted(g.items(), key=lambda t: t[1]) if v <= -0.5][:2]
        gaps = []
        if not r.has_prior_form: gaps.append('no prior form in our data')
        elif not r.has_figure: gaps.append('no ability figure')
        if fam == 'QLD' and r.has_prior_form and not r.has_sectionals: gaps.append('no sectionals')
        if fam != 'QLD': gaps.append('no sectionals/running style (not published for NSW/Vic history)')
        sdv = r.get('rating_sd_kg_qld', r.get('rating_sd_kg_national'))
        if sdv == sdv and sdv is not None and sdv >= 3.5: gaps.append(f'rating uncertain (sd {sdv:.1f} kg)')
        course = ''
        if fam == 'QLD': course = f"Track/distance/going history {g.get('Track, distance, going', 0):+.1f} kg"
        elif r.get('runs_at_course_before', 0): course = f"Course record {r.course_record_kg:+.1f} kg over {int(r.runs_at_course_before)} earlier runs here"
        return pd.Series({'plus': '; '.join(pos), 'minus': '; '.join(neg), 'evidence_gaps': '; '.join(gaps), 'course_specific': course})
    W = pd.concat([W, W.apply(explain, axis=1)], axis=1)
    W['meeting'] = ix.track; W['state'] = 'QLD' if fam == 'QLD' else ('NSW' if ix.snapshot_key.startswith('nsw') else 'VIC'); W['family'] = fam
    W['prediction_file'] = os.path.basename(ix.file); W['prediction_sha256'] = sha(ix.file)
    rows.append(W)
    cf = cal[fam]; b = np.array(cf['coef_const_logit_logfield']); B = np.array(cf['bootstrap_coefs'])
    for rid, g in W.groupby('race_id'):
        g = g.sort_values('rank'); t = g.iloc[0]; n = len(g); p = t.chance_pct / 100
        z = np.array([1, np.log(p / (1 - p)), np.log(n)]); pc = 1 / (1 + np.exp(-z @ b)); pb = 1 / (1 + np.exp(-(B @ z)))
        lo, hi = np.percentile(pb, [10, 90]); new_share = 1 - g.has_prior_form.mean()
        t1, t2 = cf['strength_terciles_2025_26']
        if (not t.has_prior_form) or new_share > 0.5: lab = 'insufficient information'
        elif pc >= t2: lab = 'strong'
        elif pc >= t1: lab = 'moderate'
        else: lab = 'weak - no clear selection'
        races.append({'meeting': ix.track, 'state': t.state, 'race_no': int(t.race_no), 'race_id': rid, 'runners': n, 'going': cond.get('track_condition'), 'rail': cond.get('rail'),
                      'top_pick': t.horse, 'saddlecloth': int(t.saddlecloth), 'barrier': t.barrier, 'jockey': t.jockey, 'top_final_rating_kg': t.final_rating_kg,
                      'margin_over_2nd_kg': round(t.final_rating_kg - g.final_rating_kg.iloc[1], 1) if n > 1 else None, 'model_top_chance_pct': round(100 * p, 1),
                      'selection_strength_pct': round(100 * pc, 1), 'strength_band_80_pct': f'{100 * lo:.0f}-{100 * hi:.0f}', 'vs_random_x': round(pc * n, 2),
                      'share_field_no_prior_form': round(new_share, 2), 'label': lab, 'second_pick': g.horse.iloc[1] if n > 1 else None})
R = pd.concat(rows, ignore_index=True); C = pd.DataFrame(races)
C['day_rank'] = C.where(C.label != 'insufficient information').selection_strength_pct.rank(ascending=False, method='first')
C = C.sort_values(['day_rank', 'selection_strength_pct'], ascending=[True, False], na_position='last')
od = os.path.join('prospective', 'daily', D); os.makedirs(od, exist_ok=True); base = os.path.join(od, f'ranking_{stamp}')
keep = ['meeting', 'state', 'race_no', 'race_id', 'rank', 'saddlecloth', 'horse', 'barrier', 'weight_kg', 'jockey', 'final_rating_kg', 'chance_pct', 'rating_kg_national', 'prev_rating_kg', 'rating_change_kg',
        'last_run_date', 'plus', 'minus', 'course_specific', 'evidence_gaps'] + [c for c in R.columns if c.startswith('kg_')] + ['candidate', 'prediction_file', 'prediction_sha256']
with open(base + '_runners.csv', 'x') as fh: R.sort_values(['meeting', 'race_no', 'rank'])[keep].to_csv(fh, index=False)
with open(base + '_races.csv', 'x') as fh: C.to_csv(fh, index=False)
# ---------------- HTML ----------------
e = lambda s: html.escape('' if s is None or (isinstance(s, float) and s != s) else str(s))
css = """body{font:14px/1.45 -apple-system,Segoe UI,Arial,sans-serif;margin:24px;color:#1d1d1f;max-width:1150px}h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 6px}
h3{font-size:15px;margin:18px 0 4px}.m{color:#666;font-size:12.5px}table{border-collapse:collapse;width:100%;margin:6px 0 10px}th,td{padding:4px 7px;border-bottom:1px solid #e4e4e4;text-align:left;vertical-align:top}
th{font-size:12px;color:#555;background:#f6f6f6}td.n{text-align:right;font-variant-numeric:tabular-nums}.sel{color:#0a6b2d;font-weight:600}.ncs{color:#8a5a00}.ins{color:#888}.p{color:#0a6b2d}.neg{color:#a12a2a}.g{color:#777;font-size:12px}"""
H = [f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>Daily ranking {D}</title><style>{css}</style></head><body>',
     f'<h1>Daily ranking — {pd.Timestamp(D).strftime("%a %d %b %Y")}</h1><div class="m">Built {stamp} from write-once pre-race predictions (no results existed). Performance-only: no prices are used. '
     'Final rating = all factors combined, in kg better (+) or worse (−) than the average runner in the race. Selection strength = how often top picks like this have won (calibrated on 2025–26 out-of-sample races), with an 80% band; ×random compares with picking a runner at random.</div>',
     '<h2>Strongest selections across the day</h2><table><tr><th>#</th><th>Meeting</th><th>R</th><th>Top pick</th><th>Final rating</th><th>Clear of 2nd</th><th>Selection strength</th><th>80% band</th><th>×random</th><th>Runners</th><th>Label</th></tr>']
for _, c in C.iterrows():
    cls = {'strong': 'sel', 'moderate': '', 'weak - no clear selection': 'ncs'}.get(c.label, 'ins')
    H.append(f'<tr><td>{"" if c.day_rank != c.day_rank else int(c.day_rank)}</td><td>{e(c.meeting)}</td><td>{c.race_no}</td><td><b>{e(c.saddlecloth)}. {e(c.top_pick)}</b></td><td class="n">{c.top_final_rating_kg:+.1f}</td>'
             f'<td class="n">{c.margin_over_2nd_kg:+.1f}</td><td class="n">{c.selection_strength_pct:.1f}%</td><td class="n">{e(c.strength_band_80_pct)}%</td><td class="n">{c.vs_random_x:.2f}</td><td class="n">{c.runners}</td><td class="{cls}">{e(c.label)}</td></tr>')
H.append('</table>')
for (mtg, st), gm in R.groupby(['meeting', 'state'], sort=False):
    cc = C[C.meeting == mtg].iloc[0]; H.append(f'<h2>{e(mtg)} ({st}) — {e(cc.going)}, rail {e(cc.rail)}</h2>')
    if st != 'QLD': H.append('<div class="m">NSW/Vic: no sectionals or running positions are published for history, so race shape and closing speed are not in these ratings.</div>')
    for rn, g in gm.groupby('race_no'):
        cr = C[(C.meeting == mtg) & (C.race_no == rn)].iloc[0]
        H.append(f'<h3>Race {rn} · {cr.runners} runners · strength {cr.selection_strength_pct:.1f}% ({e(cr.label)})</h3><table><tr><th>Rank</th><th>Horse</th><th>Bar</th><th>Kg</th><th>Final rating</th><th>Model chance</th><th>Rating change after last run</th><th>For</th><th>Against</th><th>Course-specific</th><th>Evidence gaps</th></tr>')
        for _, r in g.sort_values('rank').iterrows():
            chg = '' if r.rating_change_kg != r.rating_change_kg else f'{r.rating_change_kg:+.1f} kg'
            H.append(f'<tr><td class="n">{r["rank"]}</td><td><b>{e(r.saddlecloth)}. {e(r.horse)}</b><div class="g">{e(r.jockey)}</div></td><td class="n">{e(r.barrier)}</td><td class="n">{e(r.weight_kg)}</td>'
                     f'<td class="n"><b>{r.final_rating_kg:+.1f}</b></td><td class="n">{r.chance_pct:.1f}%</td><td class="n">{chg}</td><td class="p">{e(r.plus)}</td><td class="neg">{e(r.minus)}</td><td class="g">{e(r.course_specific)}</td><td class="g">{e(r.evidence_gaps)}</td></tr>')
        H.append('</table>')
H.append('<h2>How to read this</h2><div class="m">Labels compare the race with the same state group\'s 2025–26 races: <b>strong</b> = top third of selection strength, <b>moderate</b> = middle third, <b>weak – no clear selection</b> = bottom third; '
         '<b>insufficient information</b> = the top pick, or more than half the field, has no prior form in our data. Selection strength is a historical win rate for comparable top picks, not a promise. '
         'Pre-race files are never edited; after racing these exact numbers are evaluated against results.</div></body></html>')
with open(base + '.html', 'x', encoding='utf-8') as fh: fh.write('\n'.join(H))
print(C[['day_rank', 'meeting', 'race_no', 'top_pick', 'top_final_rating_kg', 'margin_over_2nd_kg', 'model_top_chance_pct', 'selection_strength_pct', 'strength_band_80_pct', 'vs_random_x', 'label']].to_string(index=False))
print('written', base)
