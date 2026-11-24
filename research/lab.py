"""Research lab: ask a "next start" question in plain filters and get a defensible answer.
Example (Damo's question): do horses with a fast last 600m do better next start when rising in distance,
and does it depend on class and early pace?
  python3 lab.py --when "top_l600==1 and step_up==1" --vs "top_l600==0 and step_up==1" --by class_move tempo_band
Population: Queensland beaten finishers (fields 6+, next start 7-60 days, no interstate run in between), from frames.py.
Columns you can filter on include: top_l600, l600_vs_best, step, step_up, step_down, class_move, class_delta,
strength_band, tempo_band, venue_tier, dist_band, margin_band, settle_rel, gap_to_next, rating, meeting_date.
Output: A/E with 95% CI for the group and the comparison, overall and split by each --by column, plus an odds ratio
adjusted for margin and next field size with horse-clustered errors. Saved to out/lab_<name>.csv and .md.
Reminder: everything in Queensland 2022-2026 has been looked at already; treat results as exploratory unless --since
points at races after the date the question was first asked."""
import argparse, re, numpy as np, pandas as pd, statsmodels.formula.api as smf
from scipy.stats import chi2
from frames import next_start_frame

ap = argparse.ArgumentParser(); ap.add_argument('--when', required=True); ap.add_argument('--vs', default=None)
ap.add_argument('--by', nargs='*', default=[]); ap.add_argument('--since', default=None); ap.add_argument('--name', default=None)
a = ap.parse_args()
b = next_start_frame()
if a.since: b = b[pd.to_datetime(b.meeting_date) >= pd.Timestamp(a.since)]
g1 = b.query(a.when, engine='python'); g0 = b.query(a.vs, engine='python') if a.vs else b.drop(g1.index)

def ae(h):
    w, e = h.next_win.sum(), h.exp.sum()
    lo = chi2.ppf(0.025, 2 * w) / 2 / e if w > 0 else 0.0; hi = chi2.ppf(0.975, 2 * w + 2) / 2 / e
    return len(h), h.horse_id.nunique(), round(100 * h.next_win.mean(), 1), round(w / e, 2), round(lo, 2), round(hi, 2)
rows = []
for label, h in [('group', g1), ('comparison', g0)]:
    rows.append(dict(zip(['split', 'level', 'set', 'runs', 'horses', 'next_win_%', 'A/E', 'lo95', 'hi95'], ['all', '', label, *ae(h)])))
for col in a.by:
    for lev in sorted(set(g1[col].dropna()) | set(g0[col].dropna()), key=str):
        for label, h in [('group', g1), ('comparison', g0)]:
            hh = h[h[col] == lev]
            if len(hh) >= 20: rows.append(dict(zip(['split', 'level', 'set', 'runs', 'horses', 'next_win_%', 'A/E', 'lo95', 'hi95'], [col, str(lev), label, *ae(hh)])))
t = pd.DataFrame(rows)
both = pd.concat([g1.assign(grp=1), g0.assign(grp=0)])
m = smf.logit('next_win ~ grp + np.log(margin_l + 0.5) + np.log(next_field)', data=both).fit(disp=0, cov_type='cluster', cov_kwds={'groups': pd.factorize(both.horse_id)[0]})
orr, (lo, hi), p = np.exp(m.params['grp']), np.exp(m.conf_int().loc['grp']), m.pvalues['grp']
name = a.name or re.sub(r'[^a-z0-9]+', '_', a.when.lower()).strip('_')[:40]
t.to_csv(f'out/lab_{name}.csv', index=False)
r1, r0 = t.iloc[0], t.iloc[1]
verdict = 'clear' if lo > 1 or hi < 1 else 'not clear'
md = [f'# {a.when}  vs  {a.vs or "everyone else"}', '',
      f'In racing terms: horses matching "{a.when}" won {r1["next_win_%"]}% of next starts ({int(r1.runs)} runs, {int(r1.horses)} horses), '
      f'{r1["A/E"]} times what their fields imply (95% range {r1.lo95}-{r1.hi95}). The comparison group won {r0["next_win_%"]}% (A/E {r0["A/E"]}, {r0.lo95}-{r0.hi95}).',
      f'Allowing for beaten margin and next field size, the odds of winning are {orr:.2f} times the comparison ({lo:.2f}-{hi:.2f}, p {p:.3f}): the difference is {verdict}.',
      'Horse-clustered errors (the same horse counts many times). Exploratory unless --since is after the question was first asked.', '',
      t.to_markdown(index=False)]
open(f'out/lab_{name}.md', 'w').write('\n'.join(md)); print('\n'.join(md))
