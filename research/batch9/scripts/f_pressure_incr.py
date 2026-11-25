"""Batch 9 F: last-start pace pressure x recovery (Qld 200m data) as terms on top of Queensland Engine v2."""
import json, numpy as np, pandas as pd, duckdb
src = open('engine/v2.py').read().split('def run(')[0]; exec(src)
MAN = json.load(open('benchmarks/engine_v2/manifest.json')); rng = np.random.default_rng(13)
con = duckdb.connect('../history/history.duckdb', read_only=True)
S = con.execute("""select s.race_id, s.saddlecloth, r.distance_m - s.segment_end_m to_go, s.avg_speed_ms v, s.position pos, r.track, r.distance_m
                   from sectional s join race r using (race_id) where r.distance_m - s.segment_end_m in (600, 800)""").fetchdf()
W = S.pivot_table(index=['race_id', 'saddlecloth', 'track', 'distance_m'], columns='to_go', values=['v', 'pos']).reset_index()
W.columns = ['race_id', 'saddlecloth', 'track', 'distance_m'] + [f'{a}{int(b)}' for a, b in W.columns[4:]]
W = W.dropna(subset=['v600', 'v800', 'pos800'])
rv = W.groupby('race_id')[['v800', 'v600']].median().mean(axis=1).rename('race_mid'); W = W.merge(rv, left_on='race_id', right_index=True)
W['tempo'] = W.race_mid - W.groupby(['track', 'distance_m']).race_mid.transform('median')
q = pd.read_parquet('runs.parquet', columns=['race_id', 'horse_id', 'saddlecloth', 'margin_l'])
W = W.merge(q, on=['race_id', 'saddlecloth'])
W['hot_on_speed'] = ((W.pos800 <= 2) & (W.tempo >= 0.15)).astype(float); W['beaten_far'] = (W.margin_l.fillna(99) > 2).astype(float)
U = U.merge(W[['race_id', 'horse_id', 'hot_on_speed', 'beaten_far', 'pos800']].rename(columns={'race_id': 'q_race_id', 'horse_id': 'q_horse_id'}), on=['q_race_id', 'q_horse_id'], how='left')
U = U.sort_values(['horse', 'date', 'race']).reset_index(drop=True); g = U.groupby('horse')
gap = (U.date - g.date.shift()).dt.days; backup = (gap <= 27).astype(float)
hot = g.hot_on_speed.shift(); far = g.beaten_far.shift(); close_nospeed = ((g.pos800.shift() > 2) & (far == 0)).astype(float).where(hot.notna())
U['ls_hot_beaten'] = (hot * far); U['ls_hot_beaten_x_backup'] = hot * far * backup; U['ls_hot_fought_x_backup'] = hot * (1 - far) * backup; U['ls_close_x_backup'] = close_nospeed * backup
QREL = {'Horse course/going/distance records': QFAM2['Horse course/going/distance records'], 'Jockey & trainer': QFAM2['Jockey & trainer']}
x = E.qld_frame(U); allt = sum(QREL.values(), []); x = build_terms(x, allt); off = offset_v1(x, 'qld')
bd = np.array([MAN['families']['QLD']['coef_per_term_sd_dev_fit'][t] for t in allt]); v2 = off + x[['t::' + a for a in allt]].values @ bd
dev = (x.period == 'development').values; ev = ~dev; base = E.metrics(x, v2, pd.Series(ev, index=x.index)); rows = []
for c in ['ls_hot_beaten', 'ls_hot_beaten_x_backup', 'ls_hot_fought_x_backup', 'ls_close_x_backup']:
    x = E.zcols(x, [c]); b = E.fit(x, [c], pd.Series(dev, index=x.index), tau=1e-6, offset=v2)
    m = E.metrics(x, E.eta(x, [c], b, offset=v2), pd.Series(ev, index=x.index)); d = m.lp - base.lp
    meets = m.meeting_id.values; um = np.unique(meets); idx = {k: np.flatnonzero(meets == k) for k in um}
    bs = [d.values[np.concatenate([idx[k] for k in rng.choice(um, len(um))])].mean() for _ in range(300)]
    rows.append({'term': c, 'coef_per_sd': round(float(b[0]), 4), 'gain_2025_26': round(d.mean(), 5), 'lo95': round(np.percentile(bs, 2.5), 5), 'hi95': round(np.percentile(bs, 97.5), 5),
                 'gain_2026': round(d[(m.date.dt.year == 2026).values].mean(), 5), 'top_pick_pts': round(100 * (m.hit - base.hit).mean(), 2), 'share_nonzero_%': round(100 * (x.loc[ev, c].fillna(0) != 0).mean(), 1)}); print(rows[-1], flush=True)
pd.DataFrame(rows).to_csv('/tmp/exp/rt/f_pressure_incr.csv', index=False)
