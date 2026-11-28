"""Batch 26 Part 2, engine check: does a point-in-time level + spread anchor change RACE PROBABILITY accuracy inside the engines?
Builds harness frames with the rating input transformed (research only, /tmp/cand/frames/*; frozen engines untouched):
  <V>_AFsc  dyn_nat' = c_m + s_m (dyn_nat - o_m - c_m) by the race's month (level + spread, 'cum' reference)
  <V>_AFusc same, by the month the carried rating was last updated (the horse's previous run) - within-race differences change
Monthly o (level offset), c (centre) and s (spread ratio) come from batch26/b26_stretch.py's build_anchor on the re-run rating
(P0 for Engine v2.3 frame, C0 for the consolidated frame), fitted on half the horses, months before the month only.
Only the current-rating column is transformed (plus venue levels, which the harness recomputes from it); other rating-derived
history inputs in the frame (field-strength averages, surprise records) stay as built - so this is a lower bound for full
reconstruction. Usage (from research/): python3 batch26/b26_scale_frames.py"""
import sys, json
sys.argv = ['b26']
src = open('batch26/b26_stretch.py').read().split("KEYS = [")[0].replace("r_P0 = rate(d, rule='P0'); r_C0 = rate(d, rule='C0'); log('rated P0, C0')", "r_P0 = rate(d, rule='P0'); r_C0 = rate(d, rule='C0'); log('rated')")
exec(src)
info = {}
for V, r, frame in [('C2', r_P0, '/tmp/cand/frames/C2_national.parquet'), ('CONS', r_C0, '/tmp/cand/frames/CONS_national.parquet')]:
    R = pd.Series(r['pre'], index=base.index); beta = fit_beta(R, EST & NAT & HALF & (base.year <= 2023))
    off, ctr, s_ = build_anchor(R, beta, 'race', 'cum')
    Fm = pd.read_parquet(frame); Fm['date'] = pd.to_datetime(Fm.date)
    # check the frame's rating is the re-run rating
    chk = base[['race_key', 'horse']].assign(pre=r['pre']).rename(columns={'race_key': 'race'}).merge(Fm[['race', 'horse', 'dyn_nat']], on=['race', 'horse'], how='inner')
    info[V] = {'beta': round(beta, 4), 'rows_matched': int(len(chk)), 'corr_frame_vs_rerun': round(float(chk[['pre', 'dyn_nat']].corr().iloc[0, 1]), 5),
               'mean_abs_diff_kg': round(float((chk.pre - chk.dyn_nat).abs().mean()), 4), 'scale_by_year_end': {str(k): round(float(v), 3) for k, v in s_.items() if k.month == 12}}
    mon = Fm.date.dt.to_period('M')
    Fm = Fm.sort_values(['horse', 'date', 'race']); prev = Fm.groupby('horse').date.shift().dt.to_period('M'); Fm['_pm'] = prev.fillna(mon.reindex(Fm.index))
    Fm = Fm.sort_index()
    for lab, use in [('AFsc', mon), ('AFusc', Fm._pm)]:
        o = use.map(off).astype(float).fillna(0.0); c = use.map(ctr).astype(float).fillna(0.0); s = use.map(s_).astype(float).fillna(1.0)
        G = Fm.drop(columns=['_pm']).copy(); G['dyn_nat'] = (c + s * ((G.dyn_nat - o) - c)).astype(G.dyn_nat.dtype)
        if 'dyn_nat_sd' in G: G['dyn_nat_sd'] = G.dyn_nat_sd * s
        G.to_parquet(f'/tmp/cand/frames/{V}_{lab}_national.parquet'); del G
    print(V, json.dumps(info[V]), flush=True); del Fm
json.dump(info, open('batch26/out_b26_scale_frames.json', 'w'), indent=1)
