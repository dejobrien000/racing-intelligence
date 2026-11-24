"""Exploratory: does the dynamic rating's gain hold when every placing counts? Plackett-Luce top-3 likelihood
(choose the winner from the field, then 2nd from the rest, then 3rd) for combined_v1 vs combined_v1 + dynamic rating,
fitted on development races, scored 2025-26 Qld. Outputs out/out_s12_fullorder.csv"""
import numpy as np, pandas as pd
import hier_tools as H
src = open('inv23_dynamic_rating.py').read(); src = src.replace(src[src.index("best = None; grid = []"):src.index("print('chosen on development")], "best = (np.nan, 4.0, 0.1, 5.0)\n")
exec(src.split("res = {k: score")[0])
fp = pd.read_parquet('runs.parquet')[['race_id', 'horse_id', 'finish_pos', 'field']]
x = x.merge(fp.rename(columns={'field': 'field_r'}), on=['race_id', 'horse_id'], how='left')
def explode(df, K=3):
    f = df.finish_pos.where(df.finish_pos <= df.field_r).fillna(99); out = []
    for k in range(1, K + 1):
        s = df[f >= k].copy(); s['y'] = (f[f >= k] == k).astype(float); s['rid'] = s.race_id.astype(str) + f'#{k}'; out.append(s)
    e = pd.concat(out); return e[e.groupby('rid').y.transform('sum') == 1]
dv, ev = explode(x[x.period == 'development']), explode(x[x.period == 'evaluation'])
rng = np.random.default_rng(20261124); res = {}
for name, cols in [('combined_v1', BENCH), ('combined_v1 + dynamic rating', BENCH + ['dyn_mu'])]:
    z = [c + '_z' for c in cols]
    Rd = H.Races(dv.rid.values, dv.y.values, np.zeros(len(dv)), dv[z].values); b = H.fit(Rd, np.full(len(z), 1e-6))
    Re = H.Races(ev.rid.values, ev.y.values, np.zeros(len(ev)), ev[z].values); stage = ev.rid.values[Re.o][Re.starts]
    res[name] = pd.DataFrame({'stage': stage, 'lp': Re.loglik_per_race(b)}).assign(race=lambda t: t.stage.str.split('#').str[0]).groupby('race').lp.sum()
mid = x.drop_duplicates('race_id').set_index('race_id').meeting_id
d = (res['combined_v1 + dynamic rating'] - res['combined_v1']).rename('d').to_frame().join(mid)
m = d.groupby('meeting_id').d.agg(['sum', 'count']); s, n = m['sum'].values, m['count'].values
bs = [s[i].sum() / n[i].sum() for i in (rng.integers(0, len(s), len(s)) for _ in range(1000))]
out = pd.DataFrame([{'comparison': 'combined_v1 + dynamic rating vs combined_v1, top-3 likelihood', 'races': len(d), 'gain_per_race': round(d.d.mean(), 4),
                     'lo95': round(np.percentile(bs, 2.5), 4), 'hi95': round(np.percentile(bs, 97.5), 4)}])
out.to_csv('out/out_s12_fullorder.csv', index=False); print(out.to_string(index=False))
