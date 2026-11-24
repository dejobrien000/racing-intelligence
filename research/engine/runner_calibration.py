"""Runner-level calibration for engine v2 (for the dashboard's cross-race leaderboard), built 25 Nov 2026 before racing.
The race-level selection-strength layer only covers top picks. To compare ANY runner across races we need a calibrated win
chance for every runner: logistic regression of 'won' on logit(model chance) and log(field size), fitted on every runner in
2025-26 races, using engine v2 predictions from coefficients fitted only on earlier (development) races, i.e. out-of-sample.
Uncertainty: 200 meeting-bootstrap refits (80% band). Also writes the decile table (model vs calibrated vs actual) shown in
the dashboard's advanced view. Writes benchmarks/engine_v2/runner_calibration.json. Never refitted from daily results."""
import json, numpy as np, pandas as pd, statsmodels.api as sm
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
MAN = json.load(open('benchmarks/engine_v2/manifest.json')); rng = np.random.default_rng(25)
QREL = {'Horse course/going/distance records': QFAM2['Horse course/going/distance records'], 'Jockey & trainer': QFAM2['Jockey & trainer']}
OUT = {'built_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'what': 'P(win) for any runner given engine v2 model chance and field size; fitted on 2025-26 out-of-sample predictions', 'families': {}}
lg = lambda p: np.log(p / (1 - p)); des = lambda d: sm.add_constant(np.column_stack([lg(d.p.clip(1e-4, 1 - 1e-4)), np.log(d.field)]), has_constant='add')
for kind, FAM in [('QLD', QREL), ('NSW_VIC_ACT', NFAM2)]:
    x = E.nat_frame(U) if kind != 'QLD' else E.qld_frame(U); allt = sum(FAM.values(), []); x = build_terms(x, allt); off = offset_v1(x, 'nat' if kind != 'QLD' else 'qld')
    bd = np.array([MAN['families'][kind]['coef_per_term_sd_dev_fit'][t] for t in allt]); ev = x.period == 'evaluation'
    t = x.loc[ev, ['race_id', 'meeting_id', 'win', 'field']].copy(); t['e'] = (off + x[['t::' + a for a in allt]].values @ bd)[ev.values]
    mx = t.groupby('race_id').e.transform('max'); t['p'] = np.exp(t.e - mx); t['p'] /= t.groupby('race_id').p.transform('sum'); t['field'] = t.groupby('race_id').win.transform('size')
    m = sm.Logit(t.win.astype(float), des(t)).fit(disp=0); t['cal'] = m.predict(des(t))
    meets = t.meeting_id.unique(); idx = {k: np.where(t.meeting_id.values == k)[0] for k in meets}; B = []
    for _ in range(200):
        pick = np.concatenate([idx[k] for k in rng.choice(meets, len(meets))]); dd = t.iloc[pick]
        B.append([float(v) for v in sm.Logit(dd.win.astype(float), des(dd)).fit(disp=0).params.values])
    top = t.sort_values(['race_id', 'p'], ascending=[True, False]).groupby('race_id').head(1)
    terc = [float(v) for v in np.percentile(top.cal, [100 / 3, 200 / 3])]
    top = top.assign(tier=np.select([top.cal >= terc[1], top.cal >= terc[0]], ['strong', 'moderate'], 'weak'))
    tiers = top.groupby('tier').agg(races=('win', 'size'), mean_calibrated=('cal', 'mean'), top_pick_won=('win', 'mean')).round(4).reset_index().to_dict('records')
    t['bin'] = pd.qcut(t.p, 10, labels=False, duplicates='drop')
    tab = t.groupby('bin').agg(runners=('win', 'size'), model_chance=('p', 'mean'), calibrated=('cal', 'mean'), actual=('win', 'mean')).reset_index(drop=True)
    OUT['families'][kind] = {'races': int(t.race_id.nunique()), 'runners': int(len(t)), 'coef_const_logitp_logfield': [float(v) for v in m.params.values], 'bootstrap_coefs': B, 'top_pick_terciles': terc, 'top_pick_tiers_2025_26': tiers, 'top_pick_win_rate': float(top.win.mean()),
                             'deciles': [{k: (round(float(v), 4) if k != 'runners' else int(v)) for k, v in r.items()} for r in tab.to_dict('records')]}
    print(kind, t.race_id.nunique(), 'races', len(t), 'runners | coefs', np.round(m.params.values, 3)); print(tab.round(3).to_string()); print('top-pick terciles', np.round(terc, 3), tiers)
json.dump(OUT, open('benchmarks/engine_v2/runner_calibration.json', 'w'), indent=1)
