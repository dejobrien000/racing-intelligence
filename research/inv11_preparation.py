"""Research D (first pass): how does a horse's figure move through a preparation, once class and race strength are held steady?
Each horse is compared only with itself (horse fixed effects), so better horses racing more often can't create the pattern.
Preparation run number counts starts since a break of 60+ days (gaps use every Australian TAB start via Betfair).
Class is held steady with the class level of the race (rating units) and field strength; days since the last run enters too.
Usage: python3 inv11_preparation.py -> out/out_inv11_prep.csv"""
import numpy as np, pandas as pd, statsmodels.formula.api as smf
d = pd.read_parquet('runs_rated.parquet').drop_duplicates(['race_id', 'horse_id'])
d = d[d.rating.notna() & d.finished & (d.field >= 5)].copy()
d['days_since'] = pd.to_numeric(d.days_since, errors='coerce')
d = d.sort_values(['horse_id', 'meeting_date', 'race_no'])
d['new_prep'] = (d.days_since.isna() | (d.days_since >= 60)).astype(int)
d['prep_id'] = d.groupby('horse_id')['new_prep'].cumsum()
d['prep_run'] = d.groupby(['horse_id', 'prep_id']).cumcount() + 1
# counts only Queensland starts inside the prep; a horse that ran interstate mid-prep would be mis-numbered, so keep preps
# where every gap is consistent with the Betfair start history (days_since equals the gap to the previous Qld run)
d['gap_prev_qld'] = (pd.to_datetime(d.meeting_date) - pd.to_datetime(d.groupby('horse_id')['meeting_date'].shift())).dt.days
d['consistent'] = (d.new_prep == 1) | (d.gap_prev_qld == d.days_since)
d['prep_ok'] = d.groupby(['horse_id', 'prep_id'])['consistent'].transform('all')
d = d[d.prep_ok & d.prep_id.ge(1)]
d['first_prep'] = (d.prep_id == 1)       # first Qld prep seen may be a career debut or already part-way; drop debut preps
d['prep_run_c'] = d.prep_run.clip(upper=6).astype(str).replace({'6': '6+'})
level = d.groupby('class_bucket')['rating'].median(); d['class_level'] = d.class_bucket.map(level)
d['fs'] = d.field_strength
d['ln_days'] = np.log(d.days_since.clip(lower=7, upper=365))
x = d[~d.first_prep & d.fs.notna()].copy()
for c in ['rating', 'class_level', 'fs', 'ln_days']: x[c + '_w'] = x[c] - x.groupby('horse_id')[c].transform('mean')
for lv in ['2', '3', '4', '5', '6+']:
    x['p' + lv.replace('+', 'p')] = (x.prep_run_c == lv).astype(float); x['p' + lv.replace('+', 'p') + '_w'] = x['p' + lv.replace('+', 'p')] - x.groupby('horse_id')['p' + lv.replace('+', 'p')].transform('mean')
rows = []
for name, f in [('raw (horse vs itself only)', 'rating_w ~ p2_w + p3_w + p4_w + p5_w + p6p_w - 1'),
                ('holding class level, race strength and days steady', 'rating_w ~ p2_w + p3_w + p4_w + p5_w + p6p_w + class_level_w + fs_w + ln_days_w - 1')]:
    m = smf.ols(f, data=x).fit(cov_type='cluster', cov_kwds={'groups': pd.factorize(x.horse_id)[0]})
    for t, lab in [('p2_w', '2nd up'), ('p3_w', '3rd up'), ('p4_w', '4th up'), ('p5_w', '5th up'), ('p6p_w', '6th up+')]:
        rows.append({'model': name, 'run in prep (vs 1st up)': lab, 'figure_change_kg': round(m.params[t], 2), 'lo95': round(m.conf_int().loc[t, 0], 2), 'hi95': round(m.conf_int().loc[t, 1], 2), 'p': round(m.pvalues[t], 4)})
    rows.append({'model': name, 'run in prep (vs 1st up)': 'runs / horses', 'figure_change_kg': int(m.nobs), 'lo95': x.horse_id.nunique(), 'hi95': None, 'p': None})
# class moves by prep run: do horses rise in class as the prep goes on? (descriptive)
cm = x.groupby('prep_run_c').agg(runs=('rating', 'size'), mean_class_level=('class_level', 'mean'), mean_field_strength=('fs', 'mean'), mean_days=('days_since', 'median')).round(2)
t = pd.DataFrame(rows); t.to_csv('out/out_inv11_prep.csv', index=False); cm.to_csv('out/out_inv11_prep_class.csv'); print(t.to_string(index=False)); print(cm.to_string())
