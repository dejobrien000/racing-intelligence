"""TAB venue-code map (approved by Damo 26 Nov 2026, foundation step 2; runs at the weekly update after load_tab_daily.py).
Two kinds of TAB code: the racecard meeting code (e.g. HAW) and the 4-letter venue code in TAB form records (e.g. CANT, YGLN).
Each code is tied to the Breednet meeting slug, which keeps track configurations apart (e.g. pakenham vs pakenham-synthetic,
sandown-lakeside vs sandown-hillside), by matching the SAME horses on the SAME dates. Nothing is guessed from names alone
unless marked 'name only'. A code that lands on more than one configuration is kept with every configuration and marked
'ambiguous' (never merged automatically).
Usage: python3 history/build_tab_venue_map.py <history.duckdb> <collect/national dir>
Table tab_venue_code: code, source (racecard | form), state, tab_name, bn_slug, surface, matched_runs, share, status."""
import sys, os, re, glob, duckdb, pandas as pd
DB, NAT = sys.argv[1], sys.argv[2]
con = duckdb.connect(DB)
nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\(.*?\)', '', str(s).upper()))
bn = con.execute("""select regexp_replace(upper(u.name_key), '[^A-Z0-9]', '', 'g') k, cast(u.meeting_date as varchar) d, m.slug, m.state
                    from bn_runner u join bn_meeting m using (meeting_date, slug)""").fetchdf()
surface = lambda s: 'synthetic' if re.search(r'synthetic|poly|tapeta|all.?weather', str(s), re.I) else 'turf'
rows = []
def tie(df, source, code_col, extra):
    m = df.merge(bn, on=['k', 'd'], how='left')
    for code, g in m.groupby(code_col):
        hit = g.dropna(subset=['slug']); n = len(g)
        base = {'code': code, 'source': source, **{c: g[c].dropna().iloc[0] if c in g and g[c].notna().any() else None for c in extra}}
        if hit.empty:
            rows.append({**base, 'bn_slug': None, 'surface': None, 'matched_runs': 0, 'runs_seen': n, 'share': 0.0, 'status': 'unmatched (Breednet has none of these runs yet)'}); continue
        vc = hit.groupby(['slug', 'state']).size().sort_values(ascending=False); tot = vc.sum()
        for (slug, st), c in vc.items():
            share = c / tot
            rows.append({**base, 'state': base.get('state') or st, 'bn_slug': slug, 'surface': surface(slug), 'matched_runs': int(c), 'runs_seen': n, 'share': round(float(share), 3),
                         'status': 'confirmed' if len(vc) == 1 else ('ambiguous: majority' if share >= 0.5 else 'ambiguous: minority')})
# racecard codes (tab_runner/tab_race from load_tab_daily.py)
try:
    t = con.execute("""select r.venue_code code, max(c.meeting_name) tab_name, max(c.state) state, regexp_replace(upper(r.name_key), '[^A-Z0-9]', '', 'g') k, r.race_date d
                       from tab_runner r join tab_race c using (file, venue_code, race_no) group by all""").fetchdf()
    tie(t, 'racecard', 'code', ['tab_name', 'state'])
except duckdb.CatalogException: print('tab_runner not loaded yet: racecard codes skipped')
# TAB form record codes (past starts in every form file)
P = [pd.read_csv(f, dtype=str) for f in glob.glob(os.path.join(NAT, '*', 'form_past_starts.csv'))]
if P:
    P = pd.concat(P); P = P[P.start_type.isin(['LastStarts', 'WinRun']) & P.venue.notna() & (P.venue != '-')]
    P = P.assign(k=P.name.map(nk), d=P.start_date, code=P.venue.str.upper()).drop_duplicates(['k', 'd'])
    tie(P, 'form', 'code', [])
O = pd.DataFrame(rows)
con.register('o_', O); con.execute('create or replace table tab_venue_code as select * from o_')
print('tab venue codes:', O.groupby(['source', 'status']).code.nunique().to_dict())
print('ambiguous:', O[O.status.str.startswith('ambiguous')][['code', 'source', 'bn_slug', 'matched_runs', 'share']].to_string(index=False)[:1500])
