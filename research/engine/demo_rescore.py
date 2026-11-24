"""Dynamic re-scoring demonstration (brief Part 15 item 6) on a real race: Wyong R7, Wed 25 Nov 2026 (the day's top-ranked
race under v1). Every scenario changes ONE known input, then the race is re-scored end to end with the learned models:
the frozen v1 operational model (nat_v2) and engine v2. Nothing is adjusted by hand: a change moves the rating only through
features whose learned coefficients are non-zero. Inputs with no term in the model (barrier and rail for NSW, where history
has no barriers) are changed too, to show honestly that they do nothing yet.
Outputs engine/out/demo_rescore.csv and engine/out/demo_rescore.md"""
import json, numpy as np, pandas as pd
from engine import score_v2 as S
from engine.lab import person_key
RACE_NO = 7; D = '20261125'
IX = pd.read_csv('prospective/prerace/INDEX.csv'); IX = IX[(IX.date.astype(str) == D) & (IX.track == 'Wyong') & IX.file.str.endswith('_runners.csv') & ~IX.file.str.contains('/v2_')]
ix = IX.sort_values('scored_utc').iloc[-1]
W, fam, cond, mf = S.meeting_table(ix)
dump = pd.read_parquet(f'/tmp/v2_features_Wyong_{D}.parquet'); mn = json.load(open('benchmarks/candidates_national_common/manifest.json')); SD = mn['dev_sd_after_race_centring']; C2 = mn['candidates']['nat_v2 (+ horse records)']
need = [c for c in C2 if c not in W.columns]; W = W.merge(dump[['race_no', 'saddlecloth'] + need], on=['race_no', 'saddlecloth'], how='left')
H_ = S.history(D); base = W[W.race_no == RACE_NO].copy()
def v1score(T): return sum(C2[c] * ((T[c].astype(float) - T.groupby('race_id')[c].transform(lambda s: s.astype(float).mean())) / SD[c]).fillna(0.0) for c in C2)
chk = (v1score(base) - base.v1_score).abs().max(); assert chk < 1e-3, f'v1 recomputation differs from the saved prediction by {chk}'
def score(T, recompute_records):
    T = T.copy(); T['field'] = T.groupby('race_id').saddlecloth.transform('count'); T['a_wt_rel'] = T.weight_kg - T.groupby('race_id').weight_kg.transform('mean')
    T = S.new_raw(T, H_, fam, records=recompute_records); T['v1_score'] = v1score(T); T['v1_score'] -= T.v1_score.mean()
    T, contrib = S.apply(T, fam)
    e = np.exp(T.v1_score - T.v1_score.max()); T['v1_chance'] = 100 * e / e.sum(); T['v1_kg_eq'] = T.v1_score / json.load(open('benchmarks/selection_strength_v1/manifest.json'))['families']['NSW_VIC_ACT']['score_per_kg_total']
    return T
top = base.sort_values('rank').iloc[0]; second = base.sort_values('rank').iloc[1]
nsw_j = H_[H_.state == 'NSW'].groupby('jkey').agg(n=('dyn_nat_inn', 'count')); good = H_[H_.jkey.isin(nsw_j[nsw_j.n >= 500].index)].drop_duplicates('jkey', keep='last').set_index('jkey').j_surp
best_j, worst_j = good.idxmax(), good.idxmin()
SC = [('Published fields (Good 4, Wyong)', lambda T: T, False, 'nothing'),
      ('Track downgraded to Soft 6', lambda T: T.assign(gband='soft'), True, 'going band -> each horse\'s soft-track record replaces its good-track record; v2 also applies the learned wet-track interactions'),
      ('Track downgraded to Heavy 8', lambda T: T.assign(gband='heavy'), True, 'going band -> heavy-track records; wet interactions'),
      ('Same race run at Newcastle', lambda T: T.assign(config='beaumont', venue='newcastle'), True, 'course configuration -> each horse\'s Newcastle record replaces its Wyong record'),
      (f'{top.horse_name}: jockey changed to the strongest-record NSW jockey ({best_j})', lambda T: T.assign(jockey=np.where(T.saddlecloth == top.saddlecloth, best_j.title(), T.jockey)), False, 'jockey -> v2 jockey terms (v1 has no jockey term)'),
      (f'{top.horse_name}: jockey changed to the weakest-record NSW jockey ({worst_j})', lambda T: T.assign(jockey=np.where(T.saddlecloth == top.saddlecloth, worst_j.title(), T.jockey)), False, 'jockey -> v2 jockey terms'),
      (f'{top.horse_name}: barrier 1 -> 12', lambda T: T.assign(barrier=np.where(T.saddlecloth == top.saddlecloth, 12, T.barrier)), False, 'NO TERM: NSW/Vic history has no barriers, so no barrier effect has been learned for these models'),
      ('Rail moved out 6 m', lambda T: T, False, 'NO TERM: rail is collected but no rail effect has been validated'),
      (f'{top.horse_name}: carries 3 kg more', lambda T: T.assign(weight_kg=np.where(T.saddlecloth == top.saddlecloth, T.weight_kg + 3, T.weight_kg)), False, 'weight vs field (v1) and weight change since last start (v2)'),
      (f'{second.horse_name} scratched', lambda T: T[T.saddlecloth != second.saddlecloth], False, 'field composition: everyone is re-scored against the remaining field')]
out = []
for name, fn, rec, how in SC:
    T = score(fn(base.copy()), rec)
    for _, r in T.iterrows(): out.append({'scenario': name, 'what the model changes': how, 'horse': r.horse_name, 'jockey': r.jockey, 'v1_kg_eq': round(r.v1_kg_eq, 2), 'v1_chance_pct': round(r.v1_chance, 1),
                                          'v2_final_kg_eq': round(r.final_rating_kg_eq, 2), 'v2_chance_pct': round(r.v2_chance_pct, 1), 'v2_rank': int(r.v2_rank), 'g_rec': round(r.g_rec, 2), 'c_rec': round(r.c_rec, 2)})
O = pd.DataFrame(out); O.to_csv('engine/out/demo_rescore.csv', index=False)
P = O.pivot_table(index='horse', columns='scenario', values='v2_final_kg_eq', sort=False); P0 = O[O.scenario == SC[0][0]].set_index('horse')
lines = [f'# Dynamic re-scoring: Wyong R{RACE_NO}, 25 Nov 2026', '', 'Final rating (kg-equivalent, engine v2) under each one-input change; chance in brackets.', '']
for name, _, _, how in SC:
    o = O[O.scenario == name].set_index('horse'); lines.append(f'## {name}'); lines.append(f'*{how}*'); lines.append('')
    lines.append('| Horse | Final rating | Chance | Change vs published |'); lines.append('| --- | --- | --- | --- |')
    for h, r in o.sort_values('v2_rank').iterrows():
        d = r.v2_final_kg_eq - P0.v2_final_kg_eq.get(h, np.nan); lines.append(f'| {h} | {r.v2_final_kg_eq:+.2f} | {r.v2_chance_pct:.1f}% | {d:+.2f} |')
    lines.append('')
open('engine/out/demo_rescore.md', 'w').write('\n'.join(lines)); print('\n'.join(lines[:80]))
