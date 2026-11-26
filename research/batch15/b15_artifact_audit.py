"""Batch 15 (brief s9): does the workload measurement artifact (controlling ABSOLUTE rating while the outcome is measured within the
race) touch earlier conclusions? Re-runs the main Batch 14 / follow-up results with the corrected control: the horse's rating RELATIVE
to its field (rating minus field mean, quintiles) in place of the absolute rating quintile (rband), everything else unchanged.
Covers: dip per sd (Batch 14), the seven profiles vs Steady (follow-up s1), abnormal decline (follow-up s2), jockey distance form
(beyond j_surp; same-race outcome, where the artifact could matter most)."""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, json
P = pd.read_parquet('/home/claude/b14/profiles.parquet')
P['rrel'] = P.dyn_nat - P.fmean; P['rrband'] = P.groupby('state').rrel.transform(lambda s: pd.qcut(s, 5, labels=False, duplicates='drop')).astype(str)
base = 'bs(dyn_nat_inn, df=5) + {R} + early_pos + def800c + tz + tz_miss + C(dband) + field + C(prep) + fp_pct'
def cf(form, d):
    idx = smf.ols(form, d).fit().model.data.row_labels; d = d.loc[idx]
    return smf.ols(form, d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
def co(m, k): return [round(m.params[k], 3), round(m.conf_int().loc[k, 0], 3), round(m.conf_int().loc[k, 1], 3)]
OUT = {}
P['per'] = np.where(P.state == 'SA', 'SA 2024-26', np.where(pd.to_datetime(P.meeting_date).dt.year <= 2024, 'Qld 2022-24', 'Qld 2025-26'))
P['dip_s'] = P.dip / P.groupby('state').dip.transform('std')
P['prof'] = pd.Categorical(P.profile, categories=['Steady', 'Building', 'Dip and recover', 'Early fade', 'Surge then fade', 'Late fade', 'Progressive fade'])
for per, d in P.groupby('per'):
    r = {}
    for lab, R in [('absolute rating control (as reported)', 'C(rband)'), ('rating relative to field (corrected)', 'C(rrband)')]:
        m = cf('inn_n1 ~ dip_s + ' + base.format(R=R), d); m2 = cf('inn_n1 ~ C(prof) + ' + base.format(R=R), d)
        r[lab] = {'dip per sd': co(m, 'dip_s'), 'Progressive fade vs Steady': co(m2, 'C(prof)[T.Progressive fade]'), 'Late fade vs Steady': co(m2, 'C(prof)[T.Late fade]'),
                  'Dip and recover vs Steady': co(m2, 'C(prof)[T.Dip and recover]')}
    OUT[per] = r; print(per, json.dumps(r), flush=True)
# jockey distance form (same-race outcome): Batch 14 follow-up specification with absolute vs relative rating control
V = pd.read_parquet('/home/claude/b14/national_v3_next.parquet', columns=['race_id', 'horse', 'date', 'distance_m', 'jkey', 'tkey', 'dyn_nat', 'dyn_nat_inn', 'j_surp', 'j_n', 'state'])
V = V[V.dyn_nat_inn.notna() & V.jkey.notna()].copy(); V['date'] = pd.to_datetime(V.date)
V['band'] = pd.cut(V.distance_m.astype(float), [0, 1250, 1650, 5000], labels=['sprint', 'middle', 'staying']).astype(str)
V['rband'] = pd.qcut(V.dyn_nat, 5, labels=False, duplicates='drop').astype(str)
V['rrel'] = V.dyn_nat - V.groupby('race_id').dyn_nat.transform('mean'); V['rrband'] = pd.qcut(V.rrel, 5, labels=False, duplicates='drop').astype(str)
V = V.sort_values('date'); kk = 734
def prior(key):
    day = V.groupby([key, 'band', 'date']).dyn_nat_inn.agg(['sum', 'count']).reset_index().sort_values('date')
    day['cs'] = day.groupby([key, 'band'])['sum'].cumsum() - day['sum']; day['cc'] = day.groupby([key, 'band'])['count'].cumsum() - day['count']
    al = V.groupby([key, 'date']).dyn_nat_inn.agg(['sum', 'count']).reset_index().sort_values('date'); al['as'] = al.groupby(key)['sum'].cumsum() - al['sum']; al['ac'] = al.groupby(key)['count'].cumsum() - al['count']
    X = V[[key, 'band', 'date']].merge(day[[key, 'band', 'date', 'cs', 'cc']], on=[key, 'band', 'date'], how='left').merge(al[[key, 'date', 'as', 'ac']], on=[key, 'date'], how='left')
    return (X['cs'] / (X['cc'] + kk) - X['as'] / (X['ac'] + kk)).fillna(0).values
V['j_spec'] = prior('jkey'); V['t_spec'] = prior('tkey')
e = V[(V.j_n >= 100) & (V.date >= '2023-07-01') & V.j_surp.notna()].copy()
r = {}
for lab, R in [('absolute rating control (as reported)', 'C(rband)'), ('rating relative to field (corrected)', 'C(rrband)'), ('no rating control', '1')]:
    form = f'dyn_nat_inn ~ j_surp + j_spec + t_spec + C(band) + {R} + C(state)'
    idx = smf.ols(form, e).fit().model.data.row_labels; f = e.loc[idx]
    m = smf.ols(form, f).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(f.jkey)[0]})
    r[lab] = {'j_spec kg per kg': co(m, 'j_spec'), 'j_surp': co(m, 'j_surp')}
OUT['jockey distance form (beyond j_surp), 2023-26'] = r; print(json.dumps(r), flush=True)
json.dump(OUT, open('batch15/out_artifact_audit.json', 'w'), indent=1)
