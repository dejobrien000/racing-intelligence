"""Daily ranking, ENGINE v2 (operational from 25 Nov 2026). One final race rating per runner, a breakdown that adds up to it,
calibrated selection strength (calibration v2, built from out-of-sample 2025-26 predictions), the top selections across the
day, and abstention labels. v1 rankings stay alongside (columns v1_rank / v1_chance) for monitoring.
Scale: kg-equivalent = model score / (v2 score per kg of the opposition-aware rating, development within-race slope). It is a
common currency for all factors, NOT a claim that every factor is a physical kilogram. Contributions are race-relative and
sum exactly to the final rating.
Usage: PYTHONPATH=. python3 engine/daily_ranking_v2.py 20261125"""
import sys, os, re, json, html, hashlib, numpy as np, pandas as pd
D = sys.argv[1]; stamp = pd.Timestamp.now(tz='UTC').strftime('%Y%m%dT%H%M%SZ')
MAN = json.load(open('benchmarks/engine_v2/manifest.json')); sha = lambda p: hashlib.sha256(open(p, 'rb').read()).hexdigest()
IX = pd.read_csv('prospective/prerace/INDEX.csv'); IX = IX[(IX.date.astype(str) == D) & IX.file.str.contains('/v2_') & IX.file.str.endswith('_runners.csv')]
latest = IX.sort_values('scored_utc').groupby('track').tail(1)
U = pd.read_parquet('engine/frames/national.parquet', columns=['horse', 'date', 'race', 'dyn_nat', 'dyn_nat_inn'])
last = U.sort_values(['date', 'race']).groupby('horse').tail(1).set_index('horse')
# Engine v2.3 (from 27 Nov 2026 when ops/engine_c2_enabled): its ratings, kg scale and rating history are its own (benchmarks/engine_v2_3,
# engine/frames/national_c2.parquet); Engine v2.1.3 (Qld) uses its own manifest. Other meetings exactly as before.
FAM_REL = {}   # family record (kg scale, top-pick calibration) of the engine that scored the meeting
if os.path.exists('benchmarks/engine_v2_3/engine_v2.json'): FAM_REL['Engine v2.3'] = json.load(open('benchmarks/engine_v2_3/engine_v2.json'))['families']['NSW_VIC_ACT']
if os.path.exists('benchmarks/engine_v2_1_3/manifest.json'): FAM_REL['Engine v2.1.3'] = json.load(open('benchmarks/engine_v2_1_3/manifest.json'))['families']['QLD']
_last_c2 = {}
def last_for(release):
    if release == 'Engine v2.3' and os.path.exists('engine/frames/national_c2.parquet'):
        if 'v' not in _last_c2: _last_c2['v'] = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date', 'race', 'dyn_nat']).sort_values(['date', 'race']).groupby('horse').tail(1).set_index('horse')
        return _last_c2['v']
    return last
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
rows, races = [], []
for _, ix in latest.iterrows():
    W = pd.read_csv(ix.file); fam = W.family.iloc[0]; F = MAN['families'][fam]; kg = F['score_per_kg_total']
    m2 = json.load(open(ix.file.replace('_runners.csv', '_manifest.json'))); m1 = json.load(open(m2['base_v1_file'].replace('_runners.csv', '_manifest.json')))
    rel = str(m2.get('engine_release') or '').split(' (')[0]; F = FAM_REL.get(rel, F); kg = F['score_per_kg_total']; last_m = last_for(rel)
    cond = m1['snapshot'].get('conditions', {}); snap_utc = m1['snapshot'].get('retrieved_utc')
    OPS = {'QLD': 'combined_v1 + national dynamic rating', 'NSW_VIC_ACT': 'nat_v2 (+ horse records)'}
    V1 = pd.read_csv(m2['base_v1_file']); V1 = V1[V1.candidate == OPS[fam]][['race_no', 'saddlecloth', 'has_prior_form', 'has_sectionals']]
    W = W.merge(V1, on=['race_no', 'saddlecloth'], how='left')
    comp = [c for c in W.columns if c.startswith('grp_')] + [c for c in W.columns if c.startswith('v2+ ')]
    for c in comp: W['kg::' + c.replace('grp_', '').replace('v2+ ', '')] = W[c] / kg
    kc = [c for c in W.columns if c.startswith('kg::')]
    W['check_sum_kg'] = W[kc].sum(axis=1) - W.groupby('race_id')[kc].transform('mean').sum(axis=1)
    assert np.allclose(W.check_sum_kg, W.final_rating_kg_eq, atol=0.05), 'breakdown does not reconcile with the final rating'
    key = W.horse.map(nk); W['rating_change_kg'] = W.rating_kg_national - key.map(last_m.dyn_nat)
    def explain(r):
        g = {c[4:]: r[c] for c in kc}; pos = [f'{k} +{v:.1f}' for k, v in sorted(g.items(), key=lambda t: -t[1]) if v >= 0.4][:3]; neg = [f'{k} {v:.1f}' for k, v in sorted(g.items(), key=lambda t: t[1]) if v <= -0.4][:2]
        gaps = []
        if not r.has_prior_form: gaps.append('no prior form in our data')
        if pd.isna(r.jockey): gaps.append('jockey not in fields (treated as average)')
        elif not (r.j_n >= 30): gaps.append('jockey: little history')
        if not (r.t_n >= 30): gaps.append('trainer: little history')
        if fam == 'QLD' and r.has_prior_form and not r.has_sectionals: gaps.append('no sectionals')
        if fam != 'QLD': gaps.append('no sectionals/barrier history (NSW/Vic)')
        if fam != 'QLD' and r.age_n != r.age_n: gaps.append('age unknown')
        horse = []
        if r.c_rec_n > 0: horse.append(f'course record {r.c_rec:+.1f} kg ({int(r.c_rec_n)} runs)')
        if r.get('g_rec_n', 0) > 0: horse.append(f'going-band record {r.g_rec:+.1f} kg ({int(r.g_rec_n)})')
        people = f"jockey {r.j_surp:+.2f} kg, trainer {r.t_surp:+.2f} kg (their runners vs ratings)" if r.j_surp == r.j_surp or r.t_surp == r.t_surp else ''
        return pd.Series({'plus': '; '.join(pos), 'minus': '; '.join(neg), 'evidence_gaps': '; '.join(g_ for g_ in gaps if g_), 'horse_specific': '; '.join(horse), 'people': people})
    W = pd.concat([W, W.apply(explain, axis=1)], axis=1); W['meeting'] = ix.track; W['model_version'] = 'engine_v2'; W['predicted_utc'] = m2['scored_utc']; W['fields_snapshot_utc'] = snap_utc
    rows.append(W)
    cf = F['calibration']; b = np.array(cf['coef_const_logit_logfield']); B = np.array(cf['bootstrap_coefs']); t1, t2 = cf['strength_terciles_2025_26']
    for rid, g in W.groupby('race_id'):
        g = g.sort_values('v2_rank'); t = g.iloc[0]; n = len(g); p = t.v2_chance_pct / 100
        z = np.array([1, np.log(p / (1 - p)), np.log(n)]); pc = 1 / (1 + np.exp(-z @ b)); lo, hi = np.percentile(1 / (1 + np.exp(-(B @ z))), [10, 90])
        thin = ((g.j_n.fillna(0) < 30) & (g.t_n.fillna(0) < 30)).mean()
        lab = 'insufficient information' if ((not t.has_prior_form) or (1 - g.has_prior_form.mean()) > 0.5) else ('strong' if pc >= t2 else 'moderate' if pc >= t1 else 'weak - no clear selection')
        races.append({'meeting': ix.track, 'race_no': int(t.race_no), 'race_id': rid, 'runners': n, 'going': cond.get('track_condition'), 'rail': cond.get('rail'), 'top_pick': t.horse, 'saddlecloth': int(t.saddlecloth),
                      'final_rating_kg_eq': round(t.final_rating_kg_eq, 1), 'clear_of_2nd_kg_eq': round(t.final_rating_kg_eq - g.final_rating_kg_eq.iloc[1], 1), 'model_chance_pct': round(100 * p, 1),
                      'selection_strength_pct': round(100 * pc, 1), 'band_80': f'{100 * lo:.0f}-{100 * hi:.0f}', 'vs_random_x': round(pc * n, 2), 'label': lab,
                      'v1_top_pick': g.sort_values('v1_rank').horse.iloc[0], 'changed_from_v1': t.v1_rank != 1, 'second_pick': g.horse.iloc[1], 'model_version': 'engine_v2', 'predicted_utc': m2['scored_utc']})
R = pd.concat(rows, ignore_index=True); C = pd.DataFrame(races)
C['day_rank'] = C.where(C.label != 'insufficient information').selection_strength_pct.rank(ascending=False, method='first'); C = C.sort_values(['day_rank', 'selection_strength_pct'], ascending=[True, False], na_position='last')
od = os.path.join('prospective', 'daily', D); os.makedirs(od, exist_ok=True); base = os.path.join(od, f'ranking_v2_{stamp}')
with open(base + '_runners.csv', 'x') as fh: R.sort_values(['meeting', 'race_no', 'v2_rank']).to_csv(fh, index=False)
with open(base + '_races.csv', 'x') as fh: C.to_csv(fh, index=False)
e = lambda s: html.escape('' if s is None or (isinstance(s, float) and s != s) else str(s))
css = open('prerace/daily_ranking.py').read().split('css = """')[1].split('"""')[0]
Hh = [f'<!DOCTYPE html><html><head><meta charset="utf-8"><title>Daily ranking v2 {D}</title><style>{css} .chg{{color:#6b3fa0;font-size:11.5px}}</style></head><body>',
      f'<h1>Daily ranking — {pd.Timestamp(D).strftime("%a %d %b %Y")} · engine v2</h1><div class="m">Built {stamp}. Fields snapshots and model scores were saved before racing; no prices used. '
      '<b>Final rating</b> = every learned contribution added together, shown in kg-equivalent (a common scale: 1 unit = the score difference that 1 kg of opposition-aware rating is worth on average); it is relative to the average runner in the race and the breakdown adds up to it exactly. '
      '<b>Selection strength</b> = how often top picks like this won in 2025–26 races the model was not fitted on (calibrated, accounts for field size). Labels are thirds of those historical races, not betting thresholds. '
      '"v1" columns show yesterday\'s model for comparison.</div>',
      '<h2>Strongest selections across the day</h2><table><tr><th>#</th><th>Meeting</th><th>R</th><th>Top pick</th><th>Final rating</th><th>Clear of 2nd</th><th>Selection strength</th><th>80% band</th><th>Runners</th><th>Label</th><th>v1 top pick</th></tr>']
for _, c in C.iterrows():
    cls = {'strong': 'sel', 'moderate': '', 'weak - no clear selection': 'ncs'}.get(c.label, 'ins')
    Hh.append(f'<tr><td>{"" if c.day_rank != c.day_rank else int(c.day_rank)}</td><td>{e(c.meeting)}</td><td>{c.race_no}</td><td><b>{c.saddlecloth}. {e(c.top_pick)}</b></td><td class="n">{c.final_rating_kg_eq:+.1f}</td><td class="n">{c.clear_of_2nd_kg_eq:+.1f}</td>'
              f'<td class="n">{c.selection_strength_pct:.1f}%</td><td class="n">{e(c.band_80)}%</td><td class="n">{c.runners}</td><td class="{cls}">{e(c.label)}</td><td class="g">{e(c.v1_top_pick)}{" (changed)" if c.changed_from_v1 else ""}</td></tr>')
Hh.append('</table>')
for mtg, gm in R.groupby('meeting', sort=False):
    cc = C[C.meeting == mtg].iloc[0]; Hh.append(f'<h2>{e(mtg)} — {e(cc.going)}, rail {e(cc.rail)}</h2>')
    for rn, g in gm.groupby('race_no'):
        cr = C[(C.meeting == mtg) & (C.race_no == rn)].iloc[0]
        Hh.append(f'<h3>Race {rn} · {cr.runners} runners · selection strength {cr.selection_strength_pct:.1f}% ({e(cr.label)})</h3><table><tr><th>Rank</th><th>Horse</th><th>Bar</th><th>Kg</th><th>Final rating</th><th>Chance</th><th>v1</th><th>For</th><th>Against</th><th>Horse-specific</th><th>Jockey / trainer</th><th>Rating moved after last run</th><th>Evidence gaps</th></tr>')
        for _, r in g.sort_values('v2_rank').iterrows():
            chg = '' if r.rating_change_kg != r.rating_change_kg else f'{r.rating_change_kg:+.1f} kg'
            Hh.append(f'<tr><td class="n">{r.v2_rank}</td><td><b>{r.saddlecloth}. {e(r.horse)}</b><div class="g">{e(r.jockey)} / {e(r.trainer)}</div></td><td class="n">{e(r.barrier)}</td><td class="n">{e(r.weight_kg)}</td>'
                      f'<td class="n"><b>{r.final_rating_kg_eq:+.1f}</b></td><td class="n">{r.v2_chance_pct:.1f}%</td><td class="n g">#{r.v1_rank} {r.v1_chance_pct:.0f}%</td><td class="p">{e(r.plus)}</td><td class="neg">{e(r.minus)}</td>'
                      f'<td class="g">{e(r.horse_specific)}</td><td class="g">{e(r.people)}</td><td class="n">{chg}</td><td class="g">{e(r.evidence_gaps)}</td></tr>')
        Hh.append('</table>')
Hh.append(f'<div class="m">Model version engine_v2 (benchmarks/engine_v2/manifest.json, sha {sha("benchmarks/engine_v2/manifest.json")[:12]}). Every prediction file is write-once; tomorrow these exact numbers are scored against results.</div></body></html>')
with open(base + '.html', 'x', encoding='utf-8') as fh: fh.write('\n'.join(Hh))
print(C[['day_rank', 'meeting', 'race_no', 'top_pick', 'final_rating_kg_eq', 'clear_of_2nd_kg_eq', 'model_chance_pct', 'selection_strength_pct', 'label', 'v1_top_pick']].to_string(index=False)); print('written', base)
