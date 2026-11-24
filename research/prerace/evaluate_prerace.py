"""Evaluate saved pre-race predictions once results are in the database. Never edits a prediction file.
For every prediction file given: per candidate, races with a known single winner, mean log-probability given to the
winner (higher is better; a uniform guess scores -log(field)), top-pick win rate, and the winner's model rank.
Appends one row per (prediction file x candidate) to prospective/prerace/EVALUATION.csv (append-only) unless --test.
Usage: python3 prerace/evaluate_prerace.py ../history/history.duckdb <pred_..._runners.csv> [more files] [--test]"""
import sys, os, duckdb, numpy as np, pandas as pd
args = [a for a in sys.argv[1:] if not a.startswith('--')]; TEST = '--test' in sys.argv
con = duckdb.connect(args[0], read_only=True); files = args[1:]
res = con.execute("select race_id, saddlecloth, finish_pos, result_state, scratched from starter").fetchdf()
out, detail = [], []
for f in files:
    p = pd.read_csv(f); m = p.merge(res, on=['race_id', 'saddlecloth'], how='left')
    for cand, g in m.groupby('candidate'):
        rs = []
        for rid, r in g.groupby('race_id'):
            if r.finish_pos.isna().all(): continue                       # result not loaded yet
            w = r[r.finish_pos == 1]
            late_scr = int(r.scratched.fillna(False).sum() + (r.result_state == 'DidNotStart').sum())
            if len(w) != 1: rs.append({'race_id': rid, 'note': f'{len(w)} winners among scored runners'}); continue
            pw = float(w.chance_pct.iloc[0]) / 100
            rs.append({'race_id': rid, 'runners_scored': len(r), 'late_scratchings': late_scr, 'winner': w.horse.iloc[0], 'winner_rank': int(w['rank'].iloc[0]),
                       'p_winner': pw, 'log_p_winner': np.log(max(pw, 1e-9)), 'uniform_log_p': np.log(1 / len(r)), 'top_pick_won': int(w['rank'].iloc[0] == 1)})
        R = pd.DataFrame(rs)
        for x in rs: detail.append({'file': os.path.basename(f), 'candidate': cand, **x})
        ok = R[R.get('p_winner', pd.Series(dtype=float)).notna()] if len(R) else R
        out.append({'evaluated_utc': pd.Timestamp.now(tz='UTC').isoformat(), 'file': f, 'candidate': cand, 'races_evaluated': len(ok),
                    'races_pending_or_excluded': int(g.race_id.nunique() - len(ok)), 'mean_log_p_winner': round(ok.log_p_winner.mean(), 4) if len(ok) else None,
                    'mean_uniform_log_p': round(ok.uniform_log_p.mean(), 4) if len(ok) else None, 'top_pick_win_rate': round(ok.top_pick_won.mean(), 3) if len(ok) else None,
                    'mean_winner_rank': round(ok.winner_rank.mean(), 2) if len(ok) else None})
O = pd.DataFrame(out); print(O.drop(columns=['file']).to_string(index=False))
D = pd.DataFrame(detail)
if TEST: print(D.to_string(index=False)); sys.exit()
path = 'prospective/prerace/EVALUATION.csv'; O.to_csv(path, mode='a', header=not os.path.exists(path), index=False)
dp = 'prospective/prerace/EVALUATION_races.csv'; D.to_csv(dp, mode='a', header=not os.path.exists(dp), index=False)
print('appended to', path)
