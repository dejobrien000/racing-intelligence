"""Batch 26 Part 1b: were any required inputs missing when Saturday's forecasts were made? (read-only audit; no forecast changes)
Production runner files (prospective/prerace/20261128/*/v2_pred_*_runners.csv, written 22:00-22:03Z) show the values production
actually used. TAB form records (5b, mostly fetched AFTER scoring) are used here only to measure what was missing - never to rescore.
Checks per scored runner: first-starter age and sex; career starts held vs TAB's career count (history window, missing in-window
starts, experienced horses with no held run); trainer and jockey identity; pedigree (not a production input); recent runs after the
history cutoff; missing-history classification. Output batch26/out_b26_inputs.json."""
import glob, re, json, os
import numpy as np, pandas as pd
os.chdir('/home/claude/racing-intelligence/research'); D = '20261128'
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
VEN = {'rosehill': 'RSH', 'sandown': 'SAN', 'doomben': 'DBN', 'morphettville': 'MPH', 'ascot': 'AST', 'kemblagrange': 'KGR', 'wagga': 'WAG', 'kempsey': 'KEM',
       'yarravalley': 'YVL', 'tabparkgoldcoast': 'GOC', 'toowoomba': 'TWB'}
rows = []
for f in glob.glob(f'prospective/prerace/{D}/*/v2_pred_*_runners.csv'):
    v = re.sub(r'[^a-z]', '', os.path.basename(os.path.dirname(f)).lower()); x = pd.read_csv(f); x['ven'] = VEN[v]; rows.append(x)
V2 = pd.concat(rows, ignore_index=True)
rows = []
for f in glob.glob(f'prospective/prerace/{D}/*/pred_*_runners.csv'):
    if os.path.basename(f).startswith('v2_'): continue
    v = re.sub(r'[^a-z]', '', os.path.basename(os.path.dirname(f)).lower()); x = pd.read_csv(f); x['ven'] = VEN[v]; rows.append(x)
V1 = pd.concat(rows, ignore_index=True)
V1 = V1[[c for c in ['ven', 'race_no', 'saddlecloth', 'n_prior_runs_held', 'has_prior_form', 'days_since', 'last_start_source', 'has_sectionals'] if c in V1]]
V1 = V1.drop_duplicates(['ven', 'race_no', 'saddlecloth'])
S = V2.merge(V1, on=['ven', 'race_no', 'saddlecloth'], how='left')
RC = pd.read_csv(f'collect/national/{D}/runners.csv'); RC['ven'] = RC.venue_code.str.upper()
S = S.merge(RC[['ven', 'race_no', 'saddlecloth', 'page_status', 'emergency']], on=['ven', 'race_no', 'saddlecloth'], how='left')
out0 = {'runner_lines_in_production_files': int(len(S)), 'page_status': S.page_status.value_counts(dropna=False).to_dict()}
S = S[S.page_status.astype(str).str.lower() != 'scratched'].copy()     # starters as listed at the capture (emergencies kept)
S['hk'] = S.horse.map(nk); S['qld'] = S.ven.isin(['DBN', 'GOC', 'TWB'])
out = {**out0, 'scored_runners_not_scratched_at_capture': int(len(S)), 'races': int(S.groupby(['ven', 'race_no']).ngroups)}
# TAB form records (5b) - what TAB knows about each scored runner
F = pd.read_csv(f'collect/national/{D}/form_runners.csv').rename(columns={'ven': 'ven', 'race': 'race_no', 'n': 'saddlecloth'})
F = F.drop_duplicates(['ven', 'race_no', 'saddlecloth'], keep='first')
F['captured'] = pd.to_datetime(F.captured_utc, utc=True)
S = S.merge(F[['ven', 'race_no', 'saddlecloth', 'age', 'sex', 'career_starts', 'sire', 'dam', 'trainer', 'captured']].rename(columns={'trainer': 'tab_trainer_form'}), on=['ven', 'race_no', 'saddlecloth'], how='left')
SC = pd.Timestamp('2026-11-27T22:00:00Z')
out['form_records_for_scored_runners'] = int(S.career_starts.notna().sum())
out['form_records_before_scoring'] = int((S.captured < SC).sum())
# held history per horse (the frame each engine rates from)
Hn = pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse', 'date']); Hq = pd.read_parquet('engine/frames/national_v3.parquet', columns=['horse', 'date'])
cut_n, cut_q = Hn.date.max(), Hq.date.max()
def held(H):
    g = H.groupby('horse').date; return pd.DataFrame({'held': g.size(), 'first_held': g.min(), 'last_held': g.max()})
hn, hq = held(Hn), held(Hq)
S = pd.concat([S[~S.qld].join(hn, on='hk'), S[S.qld].join(hq, on='hk')]).sort_index()
S['held'] = S.held.fillna(0).astype(int)
out['history_cutoff'] = {'national_c2': str(pd.Timestamp(cut_n).date()), 'national_v3_qld': str(pd.Timestamp(cut_q).date())}
# 1 first starters: age and sex used by production
fs = S[S.held == 0]
out['first_starters_no_held_run'] = int(len(fs))
out['first_starters_age_missing_in_production'] = int(fs.age_n.isna().sum()); out['first_starters_sex_missing_in_production'] = int(fs.female.isna().sum())
out['experienced_age_missing_in_production'] = int(S[S.held > 0].age_n.isna().sum())
fsl = fs[fs.age_n.isna()][['ven', 'race_no', 'saddlecloth', 'horse']].values.tolist(); out['first_starters_age_missing_list'] = fsl
# 2 career starts: TAB career count vs held runs
T = S[S.career_starts.notna()].copy(); T['gap'] = T.career_starts - T.held
out['career_check_runners'] = int(len(T)); out['career_equal'] = int((T.gap == 0).sum()); out['career_tab_more'] = int((T.gap > 0).sum()); out['career_held_more'] = int((T.gap < 0).sum())
out['experienced_but_no_held_run'] = T[(T.held == 0) & (T.career_starts > 0)][['ven', 'race_no', 'saddlecloth', 'horse', 'career_starts']].values.tolist()
# in-window starts missing from history, using TAB's listed previous starts (race starts only, not trials)
P = pd.read_csv(f'collect/national/{D}/form_past_starts.csv').rename(columns={'race': 'race_no', 'n': 'saddlecloth'})
P['d'] = pd.to_datetime(P.start_date, errors='coerce'); P = P[P.start_type.astype(str).str.lower() != 'trial']
P = P.merge(S[['ven', 'race_no', 'saddlecloth', 'hk', 'qld']], on=['ven', 'race_no', 'saddlecloth'], how='inner')
Hd = {False: set(zip(Hn.horse, pd.to_datetime(Hn.date).dt.date)), True: set(zip(Hq.horse, pd.to_datetime(Hq.date).dt.date))}
P['held_same_day'] = [((h, d.date()) in Hd[q]) if pd.notna(d) else False for h, d, q in zip(P.hk, P.d, P.qld)]
win = P[(P.d >= '2022-10-01') & (P.d <= pd.Timestamp(cut_n))]
miss = win[~win.held_same_day]
out['tab_listed_race_starts_in_window'] = int(len(win)); out['of_which_not_held'] = int(len(miss))
out['not_held_by_venue_code_top'] = miss.venue.value_counts().head(15).to_dict()
out['runners_with_an_unheld_in_window_start'] = int(miss.groupby(['ven', 'race_no', 'saddlecloth']).ngroups)
after = P[P.d > pd.Timestamp(cut_n)]
out['race_starts_after_history_cutoff'] = int(len(after)); out['runners_with_a_start_after_cutoff'] = int(after.groupby(['ven', 'race_no', 'saddlecloth']).ngroups)
out['runners_with_a_start_after_cutoff_list'] = after[['ven', 'race_no', 'saddlecloth', 'name', 'start_date', 'venue']].values.tolist()
# 3 trainer and jockey
out['jockey_not_notified'] = int(S.jockey.astype(str).str.upper().str.contains('NOT NOTIFIED').sum())
out['jockey_no_history_j_n0'] = int((S.j_n.fillna(0) == 0).sum()); out['trainer_missing'] = int(S.trainer.isna().sum()); out['trainer_no_history_t_n0'] = int((S.t_n.fillna(0) == 0).sum())
# 4 pedigree: not read by any production scorer (checked by searching the scoring code for sire/dam)
import subprocess
hits = subprocess.run("grep -l -i -E 'sire|dam_' engine/v2.py engine/score_v2.py prerace/score_prerace.py prerace/score_national_prerace.py", shell=True, capture_output=True, text=True).stdout.split()
out['pedigree_read_by_production_scorers'] = hits
out['pedigree_available_in_form_records'] = int(S.sire.notna().sum())
# 6 missing-history classification used by production
out['production_no_prior_form'] = int((S.has_prior_form == False).sum()) if 'has_prior_form' in S else None
json.dump(out, open('batch26/out_b26_inputs.json', 'w'), indent=1, default=str)
for k, v in out.items():
    if not isinstance(v, list) or len(v) <= 12: print(k, v)
    else: print(k, len(v), v[:6], '...')
