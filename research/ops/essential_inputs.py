"""Essential-input record for a scored day (Batch 27, 28 Nov 2026; read-only, never fails the run, never changes a forecast).
For every runner production scored, records explicitly which essential inputs were missing AT SCORING and the existing fallback applied.
History status is never inferred from a missing record: "first starter" only when TAB's form record held before scoring shows 0 starts.
Usage (from research/): python3 ops/essential_inputs.py <YYYYMMDD>  -> prospective/prerace/<D>/essential_inputs.csv + one summary line"""
import sys, glob, os, re, pandas as pd
D = sys.argv[1]
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
low = lambda s: re.sub(r'[^a-z]', '', str(s).lower())
try:
    card = sorted(glob.glob(f'collect/national/{D}/tab_*.raw.txt'))[-1]
    MEETS = [p for p in (l.rstrip('\n').split('|') for l in open(card, encoding='utf-8')) if p[0] == 'MEET' and len(p) >= 4]
    VEN = {low(p[2]): p[1] for p in MEETS}; QLDV = {p[1] for p in MEETS if p[3] == 'QLD'}
    day = pd.Timestamp(f'{D[:4]}-{D[4:6]}-{D[6:]}')
    def held_counts(f):
        H = pd.read_parquet(f, columns=['horse', 'date']); H = H[pd.to_datetime(H.date) < day]; return H.groupby('horse').size()
    HN, HQ = held_counts('engine/frames/national_c2.parquet'), held_counts('engine/frames/national_v3.parquet')
    FR = pd.read_csv(f'collect/national/{D}/form_runners.csv') if os.path.exists(f'collect/national/{D}/form_runners.csv') else pd.DataFrame(columns=['race', 'n', 'name', 'career_starts', 'captured_utc'])
    FR['k'] = FR.name.map(nk); FR['cap'] = pd.to_datetime(FR.captured_utc, utc=True)
    rows = []
    for d in sorted(glob.glob(f'prospective/prerace/{D}/*/')):
        v2 = sorted(glob.glob(d + 'v2_pred_*_runners.csv'))
        if not v2: continue
        W = pd.read_csv(v2[-1]); stamp = re.findall(r'(\d{8}T\d{6}Z)', os.path.basename(v2[-1]))[-1]
        scored = pd.Timestamp(stamp[:4] + '-' + stamp[4:6] + '-' + stamp[6:8] + 'T' + stamp[9:11] + ':' + stamp[11:13] + ':' + stamp[13:15] + 'Z')
        W['ven'] = VEN.get(low(os.path.basename(d.rstrip('/'))), os.path.basename(d.rstrip('/'))); W['scored_utc'] = scored
        rows.append(W[[c for c in ['ven', 'race_no', 'saddlecloth', 'horse', 'age_n', 'female', 'scored_utc'] if c in W]])
    S = pd.concat(rows, ignore_index=True); S['k'] = S.horse.map(nk)
    pre = FR.sort_values('cap').drop_duplicates(['race', 'n', 'k'], keep='first')
    S = S.merge(pre[['race', 'n', 'k', 'career_starts', 'cap']].rename(columns={'race': 'race_no', 'n': 'saddlecloth'}), on=['race_no', 'saddlecloth', 'k'], how='left')
    S.loc[~(S.cap < S.scored_utc), 'career_starts'] = float('nan')          # only records held before scoring count
    S['n_prior_runs_held'] = [float((HQ if v in QLDV else HN).get(k, 0)) for v, k in zip(S.ven, S.k)]   # runs held in the frame that engine rates from
    held = S.n_prior_runs_held
    S['history_status'] = 'held runs'
    S.loc[(held == 0) & (S.career_starts == 0), 'history_status'] = 'first starter (TAB: 0 starts)'
    S.loc[(held == 0) & (S.career_starts > 0), 'history_status'] = 'has raced, none held (TAB starts > 0)'
    S.loc[(held == 0) & S.career_starts.isna(), 'history_status'] = 'no held runs; debut not confirmed (no TAB record before scoring)'
    S['missing'] = [';'.join(x for x, m in [('history', h == 0), ('age', pd.isna(a)), ('sex', pd.isna(f))] if m) for h, a, f in zip(held, S.age_n, S.female)]
    S['fallback'] = [';'.join(x for x, m in [('engine no-form treatment (missing-form indicators; no demonstrated rating)', 'history' in s),
                                               ('age missing indicator - never guessed', 'age' in s), ('sex missing indicator - never guessed', 'sex' in s)] if m) for s in S.missing]
    out = S.drop(columns=['k', 'cap']).rename(columns={'n_prior_runs_held': 'held_runs', 'career_starts': 'tab_career_starts_before_scoring'})
    fp = f'prospective/prerace/{D}/essential_inputs.csv'; out[out.missing != ''].to_csv(fp, index=False)
    vc = out.history_status.value_counts().to_dict()
    print(f"essential inputs {D}: {len(out)} scored runners | first starters (TAB 0) {vc.get('first starter (TAB: 0 starts)', 0)} | "
          f"raced but none held {vc.get('has raced, none held (TAB starts > 0)', 0)} | debut not confirmed {vc.get('no held runs; debut not confirmed (no TAB record before scoring)', 0)} | "
          f"age missing {int(out.age_n.isna().sum())} | sex missing {int(out.female.isna().sum())} -> {fp}")
except Exception as e:
    print(f'essential inputs {D}: WARNING could not build the record ({type(e).__name__}: {e}) - run not affected')
