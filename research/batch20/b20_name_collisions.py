"""Batch 20 A1-A3: horses merged by the name key (which drops the country suffix). Review list for the controlled correction (nothing is
changed here; production history is untouched). A horse has exactly one dam, so two different dams under one key means two horses unless
the dam names are spelling variants of each other.
Classes:
  different_country   the key covers names with different country suffixes (e.g. X and X (NZ)) -> split by suffix (51 in the sandbox)
  same_suffix_two_dams  same suffix, 2+ dams: split only where the dams are clearly different names; flag spelling variants for review
  concurrent          runs under the key overlap in time at different meetings on the same day or within 2 days (two horses racing at once)
Outputs: batch20/out_b20_name_collisions.json and batch20/name_collision_review.csv (for the Monday correction plan).
Usage (from research/): python3 batch20/b20_name_collisions.py"""
import re, json, difflib, duckdb, numpy as np, pandas as pd
con = duckdb.connect('../history/history.duckdb', read_only=True)
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\([A-Z]{2,3}\)\s*$', '', str(s).upper()))
suf = lambda s: (re.search(r'\(([A-Z]{2,3})\)\s*$', str(s).upper()) or [None, ''])[1]
B = con.execute("select meeting_date, slug, horse, dam, sire from bn_runner where horse is not null").fetchdf()
B['key'] = B.horse.map(nk); B['suffix'] = B.horse.map(suf); B['dam_n'] = B.dam.fillna('').str.upper().str.replace(r'\s*\([A-Z]{2,3}\)\s*$', '', regex=True).str.strip()
G = B.groupby('key').agg(names=('horse', lambda s: sorted(set(s))), suffixes=('suffix', lambda s: sorted(set(s))), dams=('dam_n', lambda s: sorted(set(x for x in s if x))), sires=('sire', lambda s: sorted(set(str(x).upper().strip() for x in s if isinstance(x, str) and x.strip()))),
                         runs=('horse', 'size'), first=('meeting_date', 'min'), last=('meeting_date', 'max'))
G = G[(G.suffixes.map(len) > 1) | (G.dams.map(len) > 1)].copy()
def dam_sim(d):
    if len(d) < 2: return 1.0
    return min(difflib.SequenceMatcher(None, a, b).ratio() for i, a in enumerate(d) for b in d[i + 1:])
G['dam_min_similarity'] = G.dams.map(dam_sim)
def concurrent(k):
    d = B[B.key == k].drop_duplicates(['meeting_date', 'slug']).sort_values('meeting_date'); dd = pd.to_datetime(d.meeting_date).diff().dt.days
    return bool(((dd <= 2) & (d.slug != d.slug.shift())).any())
G['concurrent'] = [concurrent(k) for k in G.index]
G['two_sires'] = G.sires.map(len) > 1
G['class'] = np.where(G.suffixes.map(len) > 1, 'different_country', np.where(G.two_sires, 'same_suffix_different_sire_and_dam', 'same_suffix_same_sire_dam_name_differs'))
G['proposed_action'] = G['class'].map({'different_country': 'split by suffix (sandbox-tested)', 'same_suffix_different_sire_and_dam': 'two horses: split by sire and dam',
                                         'same_suffix_same_sire_dam_name_differs': 'probably one horse (dam name variant): keep merged, check by hand'})
G.reset_index().assign(names=lambda x: x.names.map('; '.join), suffixes=lambda x: x.suffixes.map(','.join), dams=lambda x: x.dams.map('; '.join), sires=lambda x: x.sires.map('; '.join)).to_csv('batch20/name_collision_review.csv', index=False)
OUT = {'keys_with_two_suffixes_or_dams': int(len(G)), 'runs_under_those_keys': int(G.runs.sum()), 'by_class': G['class'].value_counts().to_dict(), 'concurrent_careers': int(G.concurrent.sum())}
json.dump(OUT, open('batch20/out_b20_name_collisions.json', 'w'), indent=1); print(OUT)
