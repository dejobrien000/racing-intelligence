"""Score races dated >= START with the FROZEN Batch 4 candidates (no refit, ever). Rebuilds the research tables from the
database in a scratch folder (point-in-time features: every feature uses only runs before the race), runs the dynamic
rating with the frozen parameters, applies the frozen development coefficients and writes
prospective/scores_<UTC stamp>.csv (one row per race: winner's probability under each candidate, top pick hit).
Usage (from research/): python3 prospective/score_frozen.py ../history/history.duckdb [START=2026-11-25] [scratch=/tmp/prosp]"""
import sys, os, json, shutil, subprocess, hashlib, numpy as np, pandas as pd
db = os.path.abspath(sys.argv[1]); START = sys.argv[2] if len(sys.argv) > 2 else '2026-11-25'; W = sys.argv[3] if len(sys.argv) > 3 else '/tmp/prosp'
here = os.getcwd(); man_p = os.path.join(here, 'benchmarks/candidates_b4/manifest.json'); man = json.load(open(man_p))
mh = hashlib.sha256(open(man_p, 'rb').read()).hexdigest()[:16]
DEST = sys.argv[4] if len(sys.argv) > 4 else os.path.join(here, 'prospective')
os.makedirs(os.path.join(W, 'out'), exist_ok=True)
for f in ['build_runs.py', 'rating_v0.py', 'features.py', 'inv20_pace_figures.py', 'clogit_tools.py', 'dyn_rating.py']: shutil.copy(f, W)
run = lambda *a: subprocess.run([sys.executable, *a], cwd=W, check=True, stdout=subprocess.DEVNULL)
run('build_runs.py', db, 'runs.parquet'); run('rating_v0.py', 'runs.parquet', 'runs_rated_dev.parquet', '--fit-until=2024-12-31')
run('features.py', 'runs_rated_dev.parquet', db, 'features.parquet'); run('inv20_pace_figures.py', db)
os.chdir(W); sys.path.insert(0, W)
from clogit_tools import eligible, prep
import dyn_rating as DR
q = pd.read_parquet('runs.parquet')
d = pd.DataFrame({'race_id': q.race_id, 'horse_id': q.horse_id, 'horse': q.horse_id, 'date': pd.to_datetime(q.meeting_date), 'race_key': q.race_id,
                  'finish_pos': q.finish_pos.where(q.finish_pos <= q.field), 'margin_l': q.margin_l, 'weight_kg': pd.to_numeric(q.weight_kg, errors='coerce'), 'distance_m': q.distance_m})
d.loc[d.finish_pos == 1, 'margin_l'] = 0.0
p = man['dynamic_rating_params']; P = DR.prepare(d); P['dyn_mu'], P['dyn_sd'], _ = DR.run(P, p['s_kg'], p['q_kg2_per_day'], p['sig0_kg'], p['debut_offset_kg'])
X = pd.read_parquet('features.parquet').merge(P[['race_id', 'horse_id', 'dyn_mu', 'dyn_sd']], on=['race_id', 'horse_id'], how='left')
X = X.merge(pd.read_parquet('pace_figures.parquet')[['race_id', 'horse_id', 'rec_rating_pa1']], on=['race_id', 'horse_id'], how='left')
has = X.f_avgfp3.notna()
for k, v in {'missform': ~has, 'missfig': has & X.a_avg3.isna(), 'misssec': has & X.s_gap600_avg3.isna(), 'missstyle': has & X.p_style.isna(), 'missgoing': has & X.t_going.isna(),
             'misspa': has & X.rec_rating_pa1.isna()}.items(): X[k] = v.astype(float)
X['dyn_new'] = (X.dyn_sd >= 0.999 * p['sig0_kg']).astype(float)
cols = sorted({c for m in man['coefficients_per_dev_sd'].values() for c in m})
x = prep(eligible(X), cols)                      # scaling uses the development sd only (pre-2025 races, unchanged)
x = x[x.meeting_date >= START]
rows = []
for name, coef in man['coefficients_per_dev_sd'].items():
    lp = x[[c + '_z' for c in coef]].values @ np.array(list(coef.values()))
    s = pd.Series(lp, index=x.index); e = np.exp(s - s.groupby(x.race_id).transform('max')); pr = e / e.groupby(x.race_id).transform('sum')
    t = pd.DataFrame({'race_id': x.race_id, 'p': pr, 'win': x.win, 'lp': s})
    for rid, g in t.groupby('race_id'):
        rows.append({'race_id': rid, 'candidate': name, 'p_winner': float(g.p[g.win == 1].sum()), 'top_pick_won': int(g.win.values[np.argmax(g.lp.values)]), 'runners': len(g)})
out = pd.DataFrame(rows); stamp = pd.Timestamp.utcnow().strftime('%Y%m%dT%H%M%SZ')
out['scored_utc'] = stamp; out['manifest_sha256_16'] = mh
os.chdir(here); dest = os.path.join(DEST, f'scores_{stamp}.csv'); out.to_csv(dest, index=False)
print(dest, len(out) // max(1, out.candidate.nunique()), 'races from', START)
if len(out): print(out.groupby('candidate').agg(races=('race_id', 'size'), mean_log_p=('p_winner', lambda v: np.log(np.clip(v, 1e-9, 1)).mean()), top_pick=('top_pick_won', 'mean')).round(4).to_string())
