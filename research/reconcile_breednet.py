"""Reconcile Breednet results with Betfair runner files race by race, and record the actual cause of every disagreement.
Matching: same date, same Betfair venue, same race number. Names compared after removing country suffix and non-letters.
Causes assigned (first that applies):
  winners: dead heat | winner named differently (same saddlecloth) | race numbers shifted (winner found in another race
           that day) | Betfair has no winner flagged | Breednet winner absent from Betfair race | other
  runner counts: Betfair-only runners, each checked against Racing NSW (scratched flag, Jul-Nov 2026 overlap) and
           against the Breednet race (late scratching = in Betfair market, absent from Breednet result); Breednet-only
           runners (not in the Betfair market).
Usage: python3 reconcile_breednet.py ../history/history.duckdb -> out/out_reconcile_*.csv"""
import sys, re, duckdb, numpy as np, pandas as pd
con = duckdb.connect(sys.argv[1], read_only=True)
k = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
slug = lambda t: re.sub(r'[^a-z0-9]+', '-', str(t).lower().replace('&', 'and')).strip('-')
bn = con.execute("""select u.meeting_date, m.bf_track_slug venue, m.slug, u.race_no, u.saddlecloth, u.horse, u.finish_pos, u.pos_raw
                    from bn_runner u join bn_meeting m using (meeting_date, slug) join bn_race r using (meeting_date, slug, race_no) where not r.is_trial""").fetchdf()
bf = con.execute("select meeting_date, bf_track, race_no, saddlecloth, name, win_flag from bf_runner where state in ('NSW','VIC','ACT')").fetchdf()
bf['venue'] = bf.bf_track.map(slug); bn['nk'] = bn.horse.map(k); bf['nk'] = bf.name.map(k)
bn['meeting_date'] = pd.to_datetime(bn.meeting_date); bf['meeting_date'] = pd.to_datetime(bf.meeting_date)
mk = ['meeting_date', 'venue']
common = bn[mk].drop_duplicates().merge(bf[mk].drop_duplicates(), on=mk)
B = bn.merge(common, on=mk); F = bf.merge(common, on=mk)
# ---- winners ----
bw = B[B.finish_pos == 1]; fw = F[F.win_flag == True]
rk = mk + ['race_no']
wins = []
for key, g in B.groupby(rk):
    w_bn = g[g.finish_pos == 1]; f = F[(F.meeting_date == key[0]) & (F.venue == key[1]) & (F.race_no == key[2])]
    if not len(f): continue
    w_bf = f[f.win_flag == True]
    if set(w_bn.nk) == set(w_bf.nk) and len(w_bn): continue
    if len(w_bn) > 1 or len(w_bf) > 1: cause = 'dead heat'
    elif not len(w_bf): cause = 'Betfair has no winner flagged'
    elif len(w_bn) and len(w_bf) and (w_bn.saddlecloth.values[0] == w_bf.saddlecloth.values[0]): cause = 'winner named differently (same saddlecloth)'
    elif len(w_bn) and w_bn.nk.values[0] in set(fw[(fw.meeting_date == key[0]) & (fw.venue == key[1])].nk): cause = 'race numbers shifted'
    elif len(w_bn) and w_bn.nk.values[0] not in set(f.nk): cause = 'Breednet winner absent from Betfair race'
    elif len(w_bn) and len(w_bf) and w_bf.nk.values[0] in set(g.nk): cause = 'different horse placed first (protest / correction?)'
    else: cause = 'other'
    wins.append({'date': key[0].date(), 'venue': key[1], 'race_no': key[2], 'breednet_winner': ', '.join(w_bn.horse), 'betfair_winner': ', '.join(w_bf.name), 'cause': cause})
W = pd.DataFrame(wins); W.to_csv('out/out_reconcile_winners.csv', index=False)
print('winner disagreements:', len(W)); print(W.cause.value_counts().to_string())
# ---- runner counts ----
nsw = con.execute("select nm.meeting_date, r.race_no, r.horse, r.scratched from nsw_runner r join nsw_meeting nm using (key)").fetchdf()
nsw['nk'] = nsw.horse.map(k); nsw['meeting_date'] = pd.to_datetime(nsw.meeting_date)
scr = set(zip(nsw[nsw.scratched == True].meeting_date, nsw[nsw.scratched == True].nk))
rows = []
cnt = B.groupby(rk).size().rename('bn').to_frame().join(F.groupby(rk).size().rename('bf'), how='inner')
diff = cnt[cnt.bn != cnt.bf]
for key in diff.index:
    g = B[(B.meeting_date == key[0]) & (B.venue == key[1]) & (B.race_no == key[2])]; f = F[(F.meeting_date == key[0]) & (F.venue == key[1]) & (F.race_no == key[2])]
    for _, r in f[~f.nk.isin(g.nk)].iterrows():
        rows.append({'date': key[0].date(), 'venue': key[1], 'race_no': key[2], 'horse': r['name'], 'side': 'Betfair only',
                     'evidence': 'Racing NSW lists as scratched' if (key[0], r.nk) in scr else ('ran elsewhere that day' if r.nk in set(B[B.meeting_date == key[0]].nk) else 'not in Breednet result: late scratching or name mismatch')})
    for _, r in g[~g.nk.isin(f.nk)].iterrows():
        rows.append({'date': key[0].date(), 'venue': key[1], 'race_no': key[2], 'horse': r['horse'], 'side': 'Breednet only', 'evidence': f"not in Betfair market (Breednet position {r.pos_raw})"})
Rn = pd.DataFrame(rows); Rn.to_csv('out/out_reconcile_runners.csv', index=False)
print('races with different runner counts:', len(diff), 'of', len(cnt)); print(Rn.groupby(['side', 'evidence']).size().to_string())
# name-mismatch check: Betfair-only and Breednet-only in the same race with the same saddlecloth
if len(Rn):
    both = Rn.pivot_table(index=['date', 'venue', 'race_no'], columns='side', values='horse', aggfunc='count').fillna(0)
    print('races with runners on both sides (possible spelling differences):', int(((both.get('Betfair only', 0) > 0) & (both.get('Breednet only', 0) > 0)).sum()))
# race-count disagreements per meeting
rc = B.groupby(mk).race_no.nunique().rename('bn').to_frame().join(F.groupby(mk).race_no.nunique().rename('bf'))
rcd = rc[rc.bn != rc.bf].reset_index(); rcd.to_csv('out/out_reconcile_race_counts.csv', index=False)
print('meetings with different race counts:', len(rcd)); print(rcd.head(12).to_string(index=False))
