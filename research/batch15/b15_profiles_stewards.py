"""Batch 15 (brief s3): do the measured finishing profiles mean something different when the stewards REPORT interference, racing wide
without cover, a performance concern or a veterinary finding? Supplementary evidence only; an absent comment is not 'no event'
(rates are lower bounds); nothing is inferred about exhaustion, injury, motivation or fitness.
Measured = the profile (tracking). Reported = the stewards' tag on that horse (QRIC / SA reports; subject role, negations excluded).
Outcome: next-run surprise against the production rating for that state (kg; + = better than rated), and the mean of the next five.
Controls as Batch 14: this run's surprise, early position, deficit at 800, tempo, distance band, course, field strength, prep stage,
field size. Qld 2022-26 pooled (meetings with a report held: 98-99%), SA 2024 (reports held to Nov 2024 only). Cells under 60 runs
are shown but not interpreted."""
import numpy as np, pandas as pd, statsmodels.formula.api as smf, json
P = pd.read_parquet('/home/claude/b14/profiles.parquet')
P = P[P.report_held == 1].copy()
CT = 'dyn_nat_inn + early_pos + I(early_pos**2) + def800c + tz + tz_miss + C(dband) + C(track) + fmean_c + C(prep) + field'
FL = {'interference': 'reported interference (held up, checked, bumped...)', 'wide_no_cover': 'reported wide without cover', 'performance_concern': 'reported performance concern', 'vet_finding': 'veterinary finding reported'}
OUT = {}
P['prof'] = pd.Categorical(P.profile, categories=['Steady', 'Building', 'Dip and recover', 'Early fade', 'Surge then fade', 'Late fade', 'Progressive fade'])
for st, d0 in P.groupby('state'):
    r = {'runs with a report held': int(len(d0))}
    for fl, lab in FL.items():
        d = d0.dropna(subset=['inn_n1', fl]).copy(); d['f'] = d[fl].astype(float)
        cells = d.groupby(['prof', 'f'], observed=True).inn_n1.size().unstack().fillna(0).astype(int)
        try:
            idx = smf.ols(f'inn_n1 ~ C(prof) * f + {CT}', d).fit().model.data.row_labels; d = d.loc[idx]
            m = smf.ols(f'inn_n1 ~ C(prof) * f + {CT}', d).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(d.horse)[0]})
        except Exception as e:
            r[lab] = str(e)[:100]; continue
        res = {}
        for p in d.prof.cat.categories:
            base = 'f' ; inter = f'C(prof)[T.{p}]:f'
            # effect of the reported flag WITHIN this profile = f (+ interaction for non-Steady profiles)
            if p == 'Steady': est = m.params.get('f', np.nan); ci = m.conf_int().loc['f'].tolist() if 'f' in m.params else [np.nan, np.nan]
            else:
                if inter not in m.params: continue
                w = np.zeros(len(m.params)); ix = list(m.params.index); w[ix.index('f')] = 1; w[ix.index(inter)] = 1
                tt = m.t_test(w); est = float(tt.effect[0]); ci = [float(x) for x in tt.conf_int()[0]]
            n1 = int(cells.loc[p, 1.0]) if (p in cells.index and 1.0 in cells.columns) else 0
            res[p] = {'flagged runs': n1, 'next run: flagged vs not flagged, same profile (kg)': [round(est, 2), round(ci[0], 2), round(ci[1], 2)]}
        # joint test: does the flag's meaning differ across profiles?
        inters = [k for k in m.params.index if k.endswith(':f')]
        try:
            ft = m.f_test(' , '.join(f'{k} = 0' for k in inters)); res['all profiles alike? p-value'] = round(float(ft.pvalue), 3)
        except Exception: pass
        r[lab] = res
    OUT[st] = r; print(st, json.dumps(r, default=str)[:3000], flush=True)
json.dump(OUT, open('batch15/out_profiles_stewards.json', 'w'), indent=1, default=str)
