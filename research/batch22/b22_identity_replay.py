"""Batch 22 B: replay tests of the proposed live identity rule on the difficult cases (research; nothing in production changes).
Proposed live rule (TAB gives name without suffix, sire, dam, age, career starts; trainer is NOT used and never creates an identity):
  1 candidates = history identities with the same name key (identity = name + suffix + sire + dam; name variants and punctuation-only
    dam spellings merged; the Monday correction list applied)
  2 keep candidates whose sire and dam match (normalised: suffix tags, punctuation and case dropped; recorded dam/sire spellings of a
    merged identity all count)
  3 exactly one match and the foaling season implied by today's age agrees within one season -> that identity
  4 no candidates -> no history (genuine first starter if TAB career 0, otherwise "history missing")
  5 candidates exist but none match the pedigree -> a different horse with a reused name: no history (labelled)
  6 pedigree missing, or several matches, or a flagged-uncertain identity, or the age disagrees -> "identity uncertain" fallback
    (scored with no usable history and labelled; never silently given one of the careers)
Fixtures come from our own history (Breednet rows), written the way TAB writes them (no suffix on the name). Output:
batch22/out_b22_identity_replay.json and batch22/identity_replay_failures.csv (should be empty).
Usage (from research/): python3 batch22/b22_identity_replay.py"""
import re, json, duckdb, numpy as np, pandas as pd
con = duckdb.connect('../history/history.duckdb', read_only=True)
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
suf = lambda s: (re.search(r'\(([A-Z]{2,3})\)\s*$', str(s).upper()) or [None, ''])[1]
pn = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper())) if isinstance(s, str) and s.strip() else ''
I = pd.read_csv('batch21/identity_crosswalk_proposal.csv', keep_default_na=False)
CORR = pd.read_csv('batch21/identity_correction_monday.csv', keep_default_na=False)
act = CORR.groupby('key').action.first().to_dict()
I['foal'] = pd.to_numeric(I.foal_mode, errors='coerce')
# merge rules: name variants (same sire) and flagged uncertain -> one identity per key+suffix+sire; splits keep sire+dam
def ident(r):
    a = act.get(r.key, '')
    if a.startswith('keep merged'): return f'{r.key}|{r.suffix}|MERGED'
    return f'{r.key}|{r.suffix}|{r.sire_n}|{r.dam_n}'
I['id'] = I.apply(ident, axis=1); I['uncertain'] = I.key.map(lambda k: act.get(k, '').startswith('keep merged: identity uncertain'))
CAND = {k: g for k, g in I.groupby('key')}
SEASON = 2026   # Aug 2026 - Jul 2027 season for 27 Nov 2026
def resolve(name, sire, dam, age, career):
    k = nk(name); g = CAND.get(k)
    if g is None: return ('no history: genuine first starter' if career == 0 else 'no history: history missing'), None
    s_, d_ = pn(sire), pn(dam)
    if not s_ or not d_: return 'identity uncertain (pedigree missing)', None
    m = g[(g.sire_n == s_) & (g.dam_n == d_)]
    ids = m.id.unique()
    if len(ids) == 0: return 'different horse with a reused name: no history', None
    if len(ids) > 1: return 'identity uncertain (several matches)', None
    r = m.iloc[0]
    if r.uncertain: return 'identity uncertain (flagged)', None
    if pd.notna(age) and pd.notna(m.foal.max()) and not ((SEASON - age) - 1 <= m.foal.median() <= (SEASON - age) + 1): return 'identity uncertain (age disagrees)', None
    return 'resolved', ids[0]
B = con.execute("select meeting_date, horse, sire, dam, age, trainer from bn_runner where horse is not null and sire is not null and dam is not null").fetchdf()
B['key'] = B.horse.map(nk); B['suffix'] = B.horse.map(suf); B['sire_n'] = B.sire.map(pn); B['dam_n'] = B.dam.map(pn)
md = pd.to_datetime(B.meeting_date); B['foal'] = np.where(md.dt.month >= 8, md.dt.year, md.dt.year - 1) - B.age
last = B.sort_values('meeting_date').groupby(['key', 'suffix', 'sire_n', 'dam_n']).tail(1)
def tab_name(h): return re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(h)).upper()
def tab_age(r): return SEASON - r.foal if pd.notna(r.foal) else np.nan
OUT, FAIL = {}, []
def run(label, rows, expect):
    ok = 0
    for r in rows:
        st, rid = resolve(r['name'], r['sire'], r['dam'], r['age'], r.get('career', 5))
        good = expect(r, st, rid)
        ok += good
        if not good: FAIL.append({'test': label, **{k: r[k] for k in ['name', 'sire', 'dam', 'age']}, 'got': st, 'id': rid, 'want': r.get('want', '')})
    OUT[label] = {'cases': len(rows), 'passed': ok}
idmap = lambda r: ident(pd.Series({'key': r.key, 'suffix': r.suffix, 'sire_n': r.sire_n, 'dam_n': r.dam_n}))
split_keys = [k for k, a in act.items() if a.startswith('split')]
L = last[last.key.isin(split_keys)]
rows = [{'name': tab_name(r.horse), 'sire': r.sire, 'dam': r.dam, 'age': tab_age(r), 'want': idmap(r)} for r in L.itertuples()]
run('1 different horses sharing a name resolve to their own career', rows, lambda r, st, rid: st == 'resolved' and rid == r['want'])
OUT['1 distinct careers per shared name (minimum)'] = int(L.assign(id_=L.apply(idmap, axis=1)).groupby('key').id_.nunique().min())
# 2 trainer transfers: horses with 2+ trainers; every one of their rows resolves to the same identity (trainer is not an input)
multi = B.groupby(['key', 'suffix', 'sire_n', 'dam_n']).trainer.nunique(); mk = multi[multi > 1].sample(2000, random_state=22).index
T = B.set_index(['key', 'suffix', 'sire_n', 'dam_n']).loc[mk].reset_index()
T = T.groupby(['key', 'suffix', 'sire_n', 'dam_n', 'trainer']).tail(1)
rows = [{'name': tab_name(r.horse), 'sire': r.sire, 'dam': r.dam, 'age': np.nan, 'want': (r.key, r.suffix, r.sire_n, r.dam_n)} for r in T.itertuples()]
res = {}
for r in rows:
    st, rid = resolve(r['name'], r['sire'], r['dam'], r['age'], 5); res.setdefault(r['want'], set()).add((st, rid))
OUT['2 trainer transfers keep one career'] = {'horses': len(res), 'trainer_rows': len(rows), 'horses_resolving_to_one_identity': int(sum(len(v) == 1 for v in res.values())),
                                             'of_which_resolved': int(sum(len(v) == 1 and list(v)[0][0] == 'resolved' for v in res.values()))}
for k_, v in res.items():
    if len(v) != 1: FAIL.append({'test': '2 trainer transfer split', 'name': k_[0], 'sire': k_[2], 'dam': k_[3], 'age': np.nan, 'got': str(v), 'id': None, 'want': 'one identity'})
# 3 spelling variants (dam written two ways incl. punctuation) -> one career
var_keys = [k for k, a in act.items() if a == 'keep merged: same horse, name variant recorded'] + ['BATTLEDANCE', 'DOCTORTEEKAY', 'GERIATRIX', 'SELFLESSACT', 'SETTLERS']
V = B[B.key.isin(var_keys)].groupby(['key', 'dam']).tail(1)
rows = [{'name': tab_name(r.horse), 'sire': r.sire, 'dam': r.dam, 'age': np.nan, 'want': r.key} for r in V.itertuples()]
got = {}
for r in rows:
    st, rid = resolve(r['name'], r['sire'], r['dam'], r['age'], 5); got.setdefault(r['want'], set()).add((st, rid))
OUT['3 pedigree spelling variants keep one career'] = {'names': len(got), 'dam_spellings_tested': len(rows), 'names_resolving_to_one_identity': int(sum(len(v) == 1 for v in got.values())),
                                                      'of_which_resolved': int(sum(len(v) == 1 and list(v)[0][0] == 'resolved' for v in got.values()))}
for k_, v in got.items():
    if len(v) != 1 or list(v)[0][0] != 'resolved': FAIL.append({'test': '3 spelling variant', 'name': k_, 'sire': '', 'dam': '', 'age': np.nan, 'got': str(v), 'id': None, 'want': 'one resolved identity'})
# 4 missing pedigree never assigns a history
rows = [{'name': tab_name(r.horse), 'sire': '', 'dam': r.dam if i % 2 else '', 'age': tab_age(r)} for i, r in enumerate(L.itertuples())] + \
       [{'name': tab_name(r.horse), 'sire': '', 'dam': '', 'age': tab_age(r)} for r in last.sample(500, random_state=4).itertuples()]
run('4 missing pedigree never assigns a career', rows, lambda r, st, rid: rid is None and st.startswith('identity uncertain'))
# 5 flagged uncertain identities use the fallback
U_ = last[last.key.isin([k for k, a in act.items() if 'uncertain' in a])]
rows = [{'name': tab_name(r.horse), 'sire': r.sire, 'dam': r.dam, 'age': tab_age(r)} for r in U_.itertuples()]
run('5 flagged-uncertain identities use the fallback', rows, lambda r, st, rid: rid is None and st.startswith('identity uncertain'))
# 6 reused names: an existing name with a different sire and dam (a new horse) gets no history
S6 = last.sample(1000, random_state=6)
rows = [{'name': tab_name(r.horse), 'sire': 'NOT A REAL SIRE', 'dam': 'NOT A REAL DAM', 'age': 2.0, 'career': 0} for r in S6.itertuples()]
run('6 reused name, different pedigree: no history', rows, lambda r, st, rid: rid is None and st == 'different horse with a reused name: no history')
# 7 ordinary horses (control): random identities resolve to themselves with TAB-style strings (sire/dam with country tags)
S7 = last[~last.key.isin(act.keys())].sample(3000, random_state=7)
rows = [{'name': tab_name(r.horse), 'sire': str(r.sire).upper(), 'dam': str(r.dam).upper(), 'age': tab_age(r), 'want': idmap(r)} for r in S7.itertuples()]
run('7 ordinary horses resolve to themselves', rows, lambda r, st, rid: st == 'resolved' and rid == r['want'])
# 8 age check catches a same-pedigree horse of the wrong age (synthetic: age shifted by 3 seasons)
rows = [{'name': tab_name(r.horse), 'sire': r.sire, 'dam': r.dam, 'age': tab_age(r) + 3} for r in S7.head(500).itertuples() if pd.notna(r.foal)]
run('8 wrong age for the pedigree: fallback', rows, lambda r, st, rid: rid is None and st == 'identity uncertain (age disagrees)')
pd.DataFrame(FAIL).to_csv('batch22/identity_replay_failures.csv', index=False)
OUT['failures_total'] = len(FAIL); json.dump(OUT, open('batch22/out_b22_identity_replay.json', 'w'), indent=1, default=str); print(json.dumps(OUT, indent=1, default=str))
