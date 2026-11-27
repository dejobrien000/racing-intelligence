"""Batch 21 A2-A3: a durable horse identity (research; nothing in production changes; the history release is untouched).
Proposed identity = (name without country suffix, country suffix, sire, dam), with foaling season as a check, never the name alone.
Sources read: Breednet results (name with suffix, sire, dam, age, sex), Racing Queensland and SA results (their own horse codes =
authoritative ids where held), TAB morning form records (name WITHOUT suffix, sire, dam, age, sex, career starts).
Checks:
  1 identities per name key; foaling-season consistency inside each identity (season = race year, Aug-Jul, minus age)
  2 dam-name variants: same name, suffix and sire, two dam spellings -> one horse if the foaling seasons agree, else two horses
  3 authoritative ids: Racing Queensland / SA horse codes per name key (more than one code = different horses with one name)
  4 live resolution: every TAB runner on 26-27 Nov matched by name key + sire + dam (normalised, suffixes dropped) to the identities:
    unique / dam spelling variant / several plausible (never auto-chosen) / no identity (TAB career 0 = genuine first starter,
    TAB career > 0 = history missing) ; and whether the production name-key match would have picked a merged career
Outputs: batch21/out_b21_identity.json, batch21/identity_crosswalk_proposal.csv (one row per proposed identity, original names kept),
batch21/live_identity_check.csv. Usage (from research/): python3 batch21/b21_identity.py"""
import re, json, glob, difflib, duckdb, numpy as np, pandas as pd
con = duckdb.connect('../history/history.duckdb', read_only=True)
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
suf = lambda s: (re.search(r'\(([A-Z]{2,3})\)\s*$', str(s).upper()) or [None, ''])[1]
pn = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper())) if isinstance(s, str) and s.strip() else ''   # sire/dam, suffix + punctuation dropped
B = con.execute("select meeting_date, slug, horse, age, sex, sire, dam from bn_runner where horse is not null").fetchdf()
B['key'] = B.horse.map(nk); B['suffix'] = B.horse.map(suf); B['sire_n'] = B.sire.map(pn); B['dam_n'] = B.dam.map(pn)
md = pd.to_datetime(B.meeting_date); B['season'] = np.where(md.dt.month >= 8, md.dt.year, md.dt.year - 1); B['foal'] = B.season - B.age
# rows with no sire or dam attach to the single complete identity with the same name and suffix; otherwise they stay unresolved
full = B[(B.sire_n != '') & (B.dam_n != '')]; one = full.groupby(['key', 'suffix'])[['sire_n', 'dam_n']].agg(lambda s: s.iloc[0] if s.nunique() == 1 else None)
inc = (B.sire_n == '') | (B.dam_n == ''); att = B[inc].join(one, on=['key', 'suffix'], rsuffix='_1')
ok_att = att.sire_n_1.notna() & att.dam_n_1.notna(); B.loc[att.index[ok_att], 'sire_n'] = att.sire_n_1[ok_att]; B.loc[att.index[ok_att], 'dam_n'] = att.dam_n_1[ok_att]
N_ATT, N_UNRES = int(ok_att.sum()), int((~ok_att).sum()); B.loc[att.index[~ok_att], 'dam_n'] = 'UNRESOLVED'
I = B.groupby(['key', 'suffix', 'sire_n', 'dam_n']).agg(runs=('horse', 'size'), names=('horse', lambda s: '; '.join(sorted(set(s)))), foal_min=('foal', 'min'), foal_max=('foal', 'max'),
                                                     foal_mode=('foal', lambda s: s.mode().iloc[0] if s.notna().any() else np.nan), first=('meeting_date', 'min'), last=('meeting_date', 'max')).reset_index()
OUT = {'breednet_runs': int(len(B)), 'name_keys': int(B.key.nunique()), 'proposed_identities_raw': int(len(I)),
       'runs_missing_sire_or_dam': int(inc.sum()), 'of_which_attached_to_single_identity': N_ATT, 'of_which_unresolved': N_UNRES}
OUT['foaling_season_consistency'] = {'identities': int(len(I)), 'single_season': int((I.foal_max - I.foal_min <= 0).sum()), 'within_one_season': int((I.foal_max - I.foal_min <= 1).sum()),
                                     'spread_2_plus': int((I.foal_max - I.foal_min >= 2).sum())}
# dam-name variants: same key+suffix+sire, 2+ dams
def resolve(g):
    if len(g) == 1: return pd.Series(['single'] * 1, index=g.index)
    lab = []
    for i, r in g.iterrows():
        others = g.drop(i)
        same = [(difflib.SequenceMatcher(None, r.dam_n, o.dam_n).ratio(), abs((r.foal_mode or 0) - (o.foal_mode or 0))) for _, o in others.iterrows()]
        if all(fd >= 2 for _, fd in same): lab.append('different horse (foaling seasons differ)')
        elif any(fd <= 1 for _, fd in same): lab.append('dam spelling variant, same foaling season -> one horse')
        else: lab.append('unresolved')
    return pd.Series(lab, index=g.index)
I['variant_status'] = I.groupby(['key', 'suffix', 'sire_n'], group_keys=False).apply(resolve)
multi = I.groupby('key').filter(lambda g: len(g) > 1)
OUT['name_keys_with_more_than_one_identity'] = int(multi.key.nunique())
OUT['identity_status_within_shared_keys'] = multi.variant_status.value_counts().to_dict()
# within a shared key, different sire or suffix = different horse regardless of dam spelling
kk = multi.groupby('key').agg(suffixes=('suffix', 'nunique'), sires=('sire_n', 'nunique'), ids=('dam_n', 'size'))
OUT['shared_keys_by_reason'] = {'different_suffix': int((kk.suffixes > 1).sum()), 'same_suffix_different_sire': int(((kk.suffixes == 1) & (kk.sires > 1)).sum()),
                                 'same_suffix_same_sire_dam_spellings': int(((kk.suffixes == 1) & (kk.sires == 1)).sum())}
I.to_csv('batch21/identity_crosswalk_proposal.csv', index=False)
# authoritative codes
for t, lab in [('starter', 'Racing Queensland'), ('sa_starter', 'SA')]:
    c = con.execute(f"select name, name_key, horse_code from {t} where horse_code is not null and not coalesce(scratched, false)").fetchdf(); c['key'] = c.name.map(nk)
    c['fmt'] = np.where(c.horse_code.astype(str).str.startswith('AUS-'), 'Racing Australia style', 'numeric')   # RQ files carry two id systems for the same horse
    OUT[f'{lab} id formats'] = c.fmt.value_counts().to_dict()
    g = c[c.fmt == 'numeric'].groupby('key').horse_code.nunique(); OUT[f'{lab} horse codes'] = {'name_keys': int(len(g)), 'keys_with_2plus_codes': int((g > 1).sum()), 'examples': sorted(g[g > 1].index)[:12],
                                                                          'codes_with_2plus_keys(spelling variants)': int((c.groupby('horse_code').key.nunique() > 1).sum())}
    OUT[f'{lab} horse codes']['overlap_with_breednet_shared_keys'] = int(len(set(g[g > 1].index) & set(multi.key)))
# live resolution against TAB fields
T = pd.concat([pd.read_csv(f).assign(day=f.split('/')[2]) for f in sorted(glob.glob('collect/national/*/form_runners.csv'))], ignore_index=True)
T['key'] = T.name.map(nk); T['sire_n'] = T.sire.map(pn); T['dam_n'] = T.dam.map(pn)
idx = {k: g for k, g in I.groupby('key')}; rows = []
held = set(pd.read_parquet('engine/frames/national_c2.parquet', columns=['horse']).horse)
for _, r in T.iterrows():
    g = idx.get(r.key)
    if g is None:
        st = 'no identity: genuine first starter (TAB career 0)' if r.career_starts == 0 else ('no identity: history missing (TAB career > 0)' if pd.notna(r.career_starts) else 'no identity: TAB career unknown')
        rows.append((st, 0, r.key in held)); continue
    ex = g[(g.sire_n == r.sire_n) & (g.dam_n == r.dam_n)]
    if len(ex) == 1: rows.append(('unique exact (name + sire + dam)', len(g), r.key in held)); continue
    fz = g[(g.sire_n == r.sire_n) & g.dam_n.map(lambda d: difflib.SequenceMatcher(None, d, r.dam_n).ratio() >= 0.8 or d in r.dam_n or r.dam_n in d)]
    if len(fz) == 1: rows.append(('unique via dam spelling variant', len(g), r.key in held)); continue
    if len(ex) + len(fz) > 1 or (len(g) > 1 and len(fz) == 0 and (g.sire_n == r.sire_n).sum() > 1): rows.append(('several plausible identities: do not choose', len(g), r.key in held)); continue
    if len(g) == 1 and (r.sire_n == '' or r.dam_n == ''): rows.append(('name only (TAB pedigree missing): single identity', 1, r.key in held)); continue
    rows.append(('name matches but pedigree does not: treat as different horse / uncertain', len(g), r.key in held))
T['status'] = [x[0] for x in rows]; T['identities_under_name'] = [x[1] for x in rows]; T['name_key_in_rating_history'] = [x[2] for x in rows]
T['production_risk'] = (T.identities_under_name > 1)
T[['day', 'ven', 'race', 'n', 'name', 'age', 'sex', 'career_starts', 'sire', 'dam', 'status', 'identities_under_name', 'name_key_in_rating_history']].to_csv('batch21/live_identity_check.csv', index=False)
OUT['live_tab_runners'] = {'runners': int(len(T)), 'with_sire_and_dam': int(((T.sire_n != '') & (T.dam_n != '')).sum()), 'by_status': T.status.value_counts().to_dict(),
                           'names_with_2plus_identities_in_fields': int(T.production_risk.sum()),
                           'pedigree_mismatch_but_name_key_in_rating_history': int(((T.status.str.startswith('name matches')) & T.name_key_in_rating_history).sum())}
# stability across days: same name key on 2+ days with different TAB sire/dam strings
st = T.groupby('key').agg(days=('day', 'nunique'), ped=('sire_n', lambda s: s.nunique()), dams=('dam_n', 'nunique'))
OUT['live_tab_runners']['names_on_2plus_days'] = int((st.days > 1).sum()); OUT['live_tab_runners']['of_which_pedigree_string_changed'] = int(((st.days > 1) & ((st.ped > 1) | (st.dams > 1))).sum())
json.dump(OUT, open('batch21/out_b21_identity.json', 'w'), indent=1, default=str); print(json.dumps(OUT, indent=1, default=str))
