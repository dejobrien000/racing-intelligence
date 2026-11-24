"""Batch 1, B3 and B4 (NSW part). Independent tests on Racing NSW career form lines, non-Queensland races only.
B3 (R13): do ordinary beaten runners stepping up 200m+ underperform next start?
B4 (R41, NSW): does a 2kg+ weight drop from last start help, once class level and margin are allowed for?
Consecutive race lines of a horse are its consecutive starts in every state (trials in between are allowed).
Usage: python3 inv15_b3b4_nsw_tests.py <history.duckdb>  -> out/out_b3_*.csv, out/out_b4_nsw_*.csv"""
import sys, duckdb, numpy as np, pandas as pd, statsmodels.formula.api as smf
from scipy.stats import chi2
con = duckdb.connect(sys.argv[1], read_only=True)
d = con.execute("select * from nsw_form_line where not trial and finish_pos is not null and field >= 2").fetchdf()
qld = {'DOOM', 'E FM', 'GCST', 'SCST', 'IPSW', 'TOOW', 'SCPT', 'CANP', 'TWNS', 'ROCK', 'MACK', 'KILC', 'WARW', 'DALB', 'BDST', 'DEAG'}
d['run_date'] = pd.to_datetime(d.run_date); d['hid'] = d.name_key + '|' + d.dob
d = d.sort_values(['hid', 'run_date', 'distance_m'])
g = d.groupby('hid')
for c in ['run_date', 'distance_m', 'field', 'finish_pos', 'track_code', 'weight_kg', 'claim_weight_kg', 'nsw_rating', 'prize']:
    d['next_' + c] = g[c].shift(-1)
d['gap'] = (d.next_run_date - d.run_date).dt.days
d['carried'] = d.claim_weight_kg.fillna(d.weight_kg); d['next_carried'] = d.next_claim_weight_kg.fillna(d.next_weight_kg)
base = d[(d.run_date >= '2022-10-01') & d.gap.between(7, 60) & (d.field >= 6) & (d.next_field >= 6) & ~d.track_code.isin(qld) & ~d.next_track_code.isin(qld)].copy()
base['next_win'] = (base.next_finish_pos == 1).astype(int); base['exp'] = 1 / base.next_field
base['lm'] = np.log(base.margin_l.fillna(0) + 0.5); base['lnf'] = np.log(base.next_field)
def ae(h):
    w, e = h.next_win.sum(), h.exp.sum(); return round(w / e, 2), round(chi2.ppf(0.025, 2 * w) / 2 / e, 2), round(chi2.ppf(0.975, 2 * w + 2) / 2 / e, 2)
def cells(h, col):
    out = []
    for k, x in h.groupby(col, observed=True):
        a = ae(x); out.append({col: k, 'runs': len(x), 'horses': x.hid.nunique(), 'next_win_%': round(100 * x.next_win.mean(), 1), 'A/E': a[0], 'lo95': a[1], 'hi95': a[2]})
    return pd.DataFrame(out)
def logit(f, h, term):
    m = smf.logit(f, data=h).fit(disp=0, cov_type='cluster', cov_kwds={'groups': pd.factorize(h.hid)[0]})
    return {'term': term, 'odds_ratio': round(np.exp(m.params[term]), 3), 'lo95': round(np.exp(m.conf_int().loc[term, 0]), 3), 'hi95': round(np.exp(m.conf_int().loc[term, 1]), 3),
            'p_two_sided': round(m.pvalues[term], 4), 'runs': int(m.nobs), 'horses': h.hid.nunique()}

# B3: beaten runners, step up
b3 = base[base.finish_pos > 1].copy(); step = b3.next_distance_m - b3.distance_m
b3['step'] = pd.cut(step, [-1e9, -200, 199, 399, 1e9], right=False, labels=['down 200+', 'same (+/-199)', 'up 200-399', 'up 400+'])
b3['step_up'] = (step >= 200).astype(int); b3['step_down'] = (step <= -200).astype(int)
t3 = cells(b3, 'step'); t3.to_csv('out/out_b3_nsw_stepup_cells.csv', index=False); print(t3.to_string(index=False))
p4 = logit('next_win ~ step_up + step_down + lm + lnf', b3, 'step_up'); print('Primary 4 (B3):', p4)
# sensitivity: allow for the class of the next race via NSW rating band where shown (benchmark races only)
s3 = b3.dropna(subset=['nsw_rating', 'next_nsw_rating']).copy(); s3['rating_move'] = s3.next_nsw_rating - s3.nsw_rating
p4s = logit('next_win ~ step_up + step_down + lm + lnf + rating_move', s3, 'step_up'); print('B3 sensitivity with NSW rating move (benchmark races):', p4s)

# B4 NSW: weight change, all finishers
b4 = base.dropna(subset=['carried', 'next_carried']).copy(); wc = b4.next_carried - b4.carried
b4['wt_band'] = pd.cut(wc, [-99, -2, 1.5, 99], right=False, labels=['drop 2kg+', 'within 1.5kg', 'rise 2kg+'])
b4 = b4[b4.wt_band.notna()]
b4['drop2'] = (b4.wt_band == 'drop 2kg+').astype(int); b4['rise2'] = (b4.wt_band == 'rise 2kg+').astype(int)
b4['won'] = (b4.finish_pos == 1).astype(int); b4['lprize_move'] = np.log((b4.next_prize + 1000) / (b4.prize + 1000))
t4 = cells(b4, 'wt_band'); t4.to_csv('out/out_b4_nsw_weight_cells.csv', index=False); print(t4.to_string(index=False))
p6 = logit('next_win ~ drop2 + rise2 + lm + lnf + won + lprize_move', b4, 'drop2'); print('Primary 6 (B4 NSW):', p6)
pd.DataFrame([dict(test='Primary 4: B3 step up 200m+ (NSW form lines)', **p4), dict(test='B3 sensitivity: + NSW rating move', **p4s),
              dict(test='Primary 6: B4 weight drop 2kg+ (NSW form lines)', **p6)]).to_csv('out/out_b3b4_nsw_primary.csv', index=False)
