"""Coverage matrix: what we actually hold, by state, venue, tier and year, with completeness % for each field.
Reference count of races = Betfair TAB races from 1 Oct 2022 (the research window; year 2022 = Oct-Dec only). Detailed sources:
Racing Queensland tracking (Qld TAB tracked meetings), Breednet results (NSW/ACT/Vic so far, incl. non-TAB meetings),
Racing NSW results pages (Jul-Nov 2026), racing.com results and speed data (Vic, samples), Racing NSW career form lines.
"Prior form" = share of starters with at least one earlier run with a result and margin in our data.
Usage: python3 coverage_matrix.py ../history/history.duckdb out/coverage_matrix.csv"""
import sys, re, duckdb, numpy as np, pandas as pd
db, out = sys.argv[1], sys.argv[2]
con = duckdb.connect(db, read_only=True)
slug = lambda t: re.sub(r'[^a-z0-9]+', '-', str(t).lower().replace('&', 'and').replace('_', ' ')).strip('-')
qld_map = dict(con.execute("select track, bf_track from venue_map where rk = 1").fetchall()); qld_map['TAB_Park_Gold_Coast'] = 'Gold Coast'
METRO = {'eagle-farm', 'doomben', 'randwick', 'rosehill', 'warwick-farm', 'canterbury', 'flemington', 'caulfield', 'moonee-valley', 'sandown',
         'morphettville', 'ascot', 'belmont', 'elwick', 'launceston', 'fannie-bay'}
PROV = {'sunshine-coast', 'gold-coast', 'ipswich', 'toowoomba', 'newcastle', 'kembla-grange', 'hawkesbury', 'wyong', 'gosford', 'canberra', 'pakenham',
        'ballarat', 'geelong', 'cranbourne', 'bendigo', 'mornington', 'kilmore', 'seymour', 'sale', 'werribee', 'yarra-valley', 'moe', 'warrnambool',
        'illawarra-grange', 'murray-bridge', 'gawler', 'pinjarra', 'bunbury', 'northam'}
tier = lambda s: 'metro' if s in METRO else ('provincial' if s in PROV else 'country')
alias = {'caulfield-heath': 'caulfield', 'sandown-hillside': 'sandown', 'sandown-lakeside': 'sandown', 'randwick-kensington': 'randwick', 'kensington': 'randwick',
         'the-valley': 'moonee-valley', 'beaumont-newcastle': 'newcastle', 'newcastle-beaumont': 'newcastle', 'wagga-wagga': 'wagga', 'rosehill-gardens': 'rosehill',
         'pakenham-synthetic': 'pakenham', 'ballarat-synthetic': 'ballarat', 'geelong-synthetic': 'geelong', 'sunshine-coast-poly-track': 'sunshine-coast'}
norm = lambda s: alias.get(s, s)
# reference: Betfair TAB races
bf = con.execute("select state, bf_track, extract(year from meeting_date)::int y, count(distinct meeting_date||':'||race_no) races, count(*) starters from bf_runner where state <> 'NZ' and meeting_date >= '2022-10-01' group by 1,2,3").fetchdf()
bf['venue'] = bf.bf_track.map(slug).map(norm)
ref = bf.groupby(['state', 'venue', 'y'], as_index=False)[['races', 'starters']].sum().rename(columns={'races': 'tab_races', 'starters': 'tab_starters'})
rows = []
# Queensland tracking
q = con.execute("""select r.track, extract(year from r.meeting_date)::int y, r.race_id, r.race_name, r.track_rating_tracking, r.rail, r.race_time_s,
                   s.saddlecloth, s.finish_pos, s.margin_l, s.weight_kg, s.barrier, s.jockey, s.trainer, s.ground_m, s.name_key, r.meeting_date, coalesce(x.n_sec, 0) n_sec
                   from starter s join race r using (race_id)
                   left join (select race_id, saddlecloth, count(*) n_sec from sectional group by 1, 2) x on x.race_id = s.race_id and x.saddlecloth = s.saddlecloth
                   where not coalesce(s.scratched, false)""").fetchdf()
q['venue'] = q.track.map(lambda t: norm(slug(qld_map.get(t, t.replace('_', ' '))))); q['state'] = 'QLD'
q = q.sort_values('meeting_date'); q['prior'] = q.groupby('name_key').cumcount() > 0
q['cls'] = q.race_name.str.contains(r'BENCHMARK|BM\s?\d|CLASS\s?\d|MAIDEN|GROUP|LISTED|OPEN|QUALITY|RESTRICTED|HANDICAP', case=False, na=False)
def agg_q(h):
    return pd.Series({'races': h.race_id.nunique(), 'starters': len(h), 'pct_result_margin': (h.finish_pos.notna() & (h.margin_l.notna() | (h.finish_pos == 1))).mean(),
        'pct_weight': h.weight_kg.notna().mean(), 'pct_barrier': h.barrier.notna().mean(), 'pct_jockey': h.jockey.notna().mean(), 'pct_trainer': h.trainer.notna().mean(),
        'pct_class': h.cls.mean(), 'pct_track_condition': h.track_rating_tracking.notna().mean(), 'pct_rail': h.rail.notna().mean(), 'pct_race_time': h.race_time_s.notna().mean(),
        'pct_individual_sectionals': (h.n_sec > 0).mean(), 'pct_in_running': (h.n_sec > 0).mean(), 'pct_ground_covered': h.ground_m.notna().mean(), 'pct_prior_form': h.prior.mean(),
        'sources': 'Racing Queensland tracking + Race Fields'})
qa = q.groupby(['state', 'venue', 'y']).apply(agg_q, include_groups=False).reset_index()
rows.append(qa)
# Breednet (all its states) + Racing NSW form lines for barrier / in-running on the same runs
bn = con.execute("""select m.state, m.bf_track_slug venue, extract(year from u.meeting_date)::int y, u.meeting_date, u.slug, u.race_no, u.finish_pos, u.margin_l, u.weight_kg, u.jockey, u.trainer, u.name_key,
                    r.class, r.going, r.race_time_s from bn_runner u join bn_meeting m using (meeting_date, slug) join bn_race r using (meeting_date, slug, race_no) where not r.is_trial""").fetchdf()
if len(bn):
    fl = con.execute("select name_key, run_date meeting_date, distance_m, barrier, pos800, pos400 from nsw_form_line where not trial").fetchdf()
    fl['meeting_date'] = pd.to_datetime(fl.meeting_date).dt.date; bn['meeting_date'] = pd.to_datetime(bn.meeting_date).dt.date
    fl['nk'] = fl.name_key.str.replace(r'[^A-Z0-9]', '', regex=True); bn['nk'] = bn.name_key.str.replace(r'[^A-Z0-9]', '', regex=True)
    bn = bn.merge(fl.drop_duplicates(['nk', 'meeting_date'])[['nk', 'meeting_date', 'barrier', 'pos800', 'pos400']], on=['nk', 'meeting_date'], how='left')
    bn = bn.sort_values('meeting_date'); bn['prior'] = bn.groupby('nk').cumcount() > 0
    bn['venue'] = bn.venue.map(norm); bn['state'] = bn.state.fillna('UNKNOWN')
    def agg_b(h):
        return pd.Series({'races': h[['meeting_date', 'slug', 'race_no']].drop_duplicates().shape[0], 'starters': len(h),
            'pct_result_margin': (h.finish_pos.notna() & (h.margin_l.notna() | (h.finish_pos == 1))).mean(), 'pct_weight': h.weight_kg.notna().mean(),
            'pct_barrier': h.barrier.notna().mean(), 'pct_jockey': (h.jockey.fillna('') != '').mean(), 'pct_trainer': (h.trainer.fillna('') != '').mean(),
            'pct_class': (h['class'].fillna('') != '').mean(), 'pct_track_condition': h.going.notna().mean(), 'pct_rail': 0.0, 'pct_race_time': h.race_time_s.notna().mean(),
            'pct_individual_sectionals': 0.0, 'pct_in_running': h.pos400.notna().mean(), 'pct_ground_covered': 0.0, 'pct_prior_form': h.prior.mean(),
            'sources': 'Breednet results; barrier and in-running only where a Racing NSW form line covers the run'})
    rows.append(bn.groupby(['state', 'venue', 'y']).apply(agg_b, include_groups=False).reset_index())
# Racing NSW results pages (Jul-Nov 2026): full fields incl. barrier, benchmark, rail
nr = con.execute("""select m.state, m.venue, extract(year from m.meeting_date)::int y, m.key, r.race_no, r.finish_pos, r.margin_l, r.weight_kg, r.barrier, r.jockey, r.trainer, r.benchmark,
                    m.track_condition, m.rail, x.race_time_s from nsw_runner r join nsw_meeting m using (key) left join nsw_race x on x.key = r.key and x.race_no = r.race_no
                    where not coalesce(r.scratched, false) and m.meeting_kind <> 'Trial'""").fetchdf() if 'meeting_kind' in con.execute('describe nsw_meeting').fetchdf().column_name.tolist() else pd.DataFrame()
if len(nr):
    nr['venue'] = nr.venue.map(slug).map(norm)
    def agg_n(h):
        return pd.Series({'races': h[['key', 'race_no']].drop_duplicates().shape[0], 'starters': len(h), 'pct_result_margin': (h.finish_pos.notna() & (h.margin_l.notna() | (h.finish_pos == 1))).mean(),
            'pct_weight': h.weight_kg.notna().mean(), 'pct_barrier': h.barrier.notna().mean(), 'pct_jockey': h.jockey.notna().mean(), 'pct_trainer': h.trainer.notna().mean(),
            'pct_class': h.benchmark.notna().mean(), 'pct_track_condition': h.track_condition.notna().mean(), 'pct_rail': h.rail.notna().mean(), 'pct_race_time': h.race_time_s.notna().mean(),
            'pct_individual_sectionals': 0.0, 'pct_in_running': 0.0, 'pct_ground_covered': 0.0, 'pct_prior_form': np.nan, 'sources': 'Racing NSW results pages'})
    rows.append(nr.groupby(['state', 'venue', 'y']).apply(agg_n, include_groups=False).reset_index())
# Victoria speed data sample
vs = con.execute("select count(distinct meet_code||':'||race_no) races, count(*) starters from vic_speed_runner").fetchone()
det = pd.concat(rows, ignore_index=True)
# combine per venue-year: take the best value of each field across sources (a field is covered if any source has it)
pct = [c for c in det.columns if c.startswith('pct_')]
best = det.groupby(['state', 'venue', 'y']).agg({**{c: 'max' for c in pct}, 'races': 'max', 'starters': 'max', 'sources': lambda s: ' | '.join(sorted(set(s)))}).reset_index()
m = ref.merge(best, on=['state', 'venue', 'y'], how='outer')
# completeness against ALL eligible races and starters we know of (Betfair TAB races plus any extra non-TAB races in the
# detailed sources): a field's % = starters with that field / all known starters at that venue-year
m['all_races'] = np.maximum(m.tab_races.fillna(0), m.races.fillna(0)); m['all_starters'] = np.maximum(m.tab_starters.fillna(0), m.starters.fillna(0))
for c in pct: m[c] = np.where(m.all_starters > 0, m[c].fillna(0) * m.starters.fillna(0) / m.all_starters, np.nan)
m['pct_starters_with_full_results'] = m['pct_result_margin']
m['tier'] = m.venue.map(tier); m.loc[~m.state.isin(['QLD', 'NSW', 'ACT', 'VIC']), 'tier'] = m.loc[~m.state.isin(['QLD', 'NSW', 'ACT', 'VIC']), 'venue'].map(tier)
m['races_with_full_results'] = m.races.fillna(0).astype(int)
m['pct_races_with_full_results'] = np.where(m.all_races > 0, m.races_with_full_results / m.all_races, np.nan)
m['non_tab_or_extra_races'] = np.maximum(0, m.races_with_full_results - m.tab_races.fillna(0)).astype(int)
for c in pct + ['pct_starters_with_full_results']: m[c] = (100 * m[c]).round(1)
m['pct_races_with_full_results'] = (100 * m.pct_races_with_full_results).round(1)
m['sources'] = m.sources.fillna('Betfair runner files only (runners and winner)')
cols = ['state', 'venue', 'tier', 'y', 'all_races', 'all_starters', 'tab_races', 'races_with_full_results', 'pct_races_with_full_results', 'non_tab_or_extra_races'] + pct + ['sources']
m = m[cols].rename(columns={'y': 'year'}).sort_values(['state', 'tier', 'venue', 'year'])
m.to_csv(out, index=False)
# summary by state, tier and year (starter-weighted)
w = m.copy(); w['wt'] = w.all_starters.fillna(0)
def wavg(h, c): return round(np.average(h[c].fillna(0), weights=h.wt), 1) if h.wt.sum() > 0 else 0.0
summ = w.groupby(['state', 'tier', 'year']).apply(lambda h: pd.Series({'all_races': int(h.all_races.sum()), 'all_starters': int(h.all_starters.sum()), 'races_with_full_results': int(h.races_with_full_results.sum()),
        'pct_races_with_full_results': round(100 * h.races_with_full_results.sum() / max(1, h.all_races.sum()), 1),
        **{c: wavg(h, c) for c in ['pct_result_margin', 'pct_weight', 'pct_barrier', 'pct_jockey', 'pct_class', 'pct_track_condition', 'pct_rail', 'pct_race_time', 'pct_individual_sectionals', 'pct_in_running', 'pct_ground_covered', 'pct_prior_form']}}), include_groups=False).reset_index()
summ.to_csv(out.replace('.csv', '_summary.csv'), index=False)
print(summ[(summ.year >= 2022) & summ.state.isin(['QLD', 'NSW', 'VIC', 'ACT'])].to_string(index=False)); print('Vic speed-data sample: races', vs[0], 'starters', vs[1]); print('rows', len(m))
