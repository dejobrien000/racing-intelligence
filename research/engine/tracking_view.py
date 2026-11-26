"""Measured tracking history for today's runners, for INSPECTION on the dashboard (display only; Damo 27 Nov 2026).
Reads the master database's tracking tables as they stand: Queensland (starter/sectional/race), South Australia
(sa_starter/sa_sectional/sa_race) and, once loaded at the weekly update, Victoria (vic_starter/vic_sectional/vic_race).
A missing table is skipped, so Victorian runs appear by themselves after the 30 Nov load. Nothing here feeds a rating.

Measured vs derived is kept: finish time is the tracking provider's (Victoria: the sum of measured sections, so 'derived');
last 600 m = cumulative time at the finish minus at 600 m out (from measured splits, so 'derived'); last 200 m = the final
measured split. Horses are matched by name, the same way the national ratings link a horse's runs."""
import re, duckdb, pandas as pd

nk = lambda s: re.sub(r'[^A-Z0-9]', '', re.sub(r'\s*\(.*?\)', '', str(s).upper()))
SRC = {'QLD': ('starter', 'sectional', 'race', 'race_id', 'meeting_date', 'track', 'finish_pos', 'finish_time_s', 'inter_s', False),
       'SA': ('sa_starter', 'sa_sectional', 'sa_race', 'race_id', 'meeting_date', 'track', 'finish_pos', 'finish_time_s', 'inter_s', False),
       'VIC': ('vic_starter', 'vic_sectional', 'vic_race', 'vic_race_id', 'race_date', 'track_config', 'bn_finish_pos', 'finish_time_s_derived', 'inter_s_derived', True)}
LABEL = {'QLD': 'Qld tracking (Racing Queensland)', 'SA': 'SA tracking (TripleS)', 'VIC': 'Vic tracking (TripleS)'}


def history(db, names, before, per_horse=5):
    """names: display names of today's runners. Returns ({name_key: {'held': {state: n}, 'runs': [...]}}, {state: tables present})."""
    keys = {nk(n) for n in names}
    con = duckdb.connect(db, read_only=True)
    have = {r[0] for r in con.execute("select table_name from information_schema.tables").fetchall()}
    out, present = {}, {}
    for st, (ts, tsec, tr, rid, dcol, tcol, fcol, tcol_time, icol, vic) in SRC.items():
        present[st] = all(t in have for t in (ts, tsec, tr))
        if not present[st]: continue
        S = con.execute(f"select {rid} rid, saddlecloth, name, {fcol} fin, {tcol_time} t from {ts} where {tcol_time} is not null and {tcol_time} > 0"
                        + (" and tracking_status = 'complete'" if vic else "")).fetchdf()
        S['k'] = S.name.map(nk); S = S[S.k.isin(keys)]
        if not len(S): continue
        R = con.execute(f"select {rid} rid, {dcol} d, {tcol} track, distance_m from {tr}").fetchdf()
        S = S.merge(R, on='rid', how='inner'); S = S[pd.to_datetime(S.d) < pd.Timestamp(before)]
        if not len(S): continue
        con.register('_k', S[['rid', 'saddlecloth']].astype({'saddlecloth': str}))
        X = con.execute(f"select x.{rid} rid, cast(x.saddlecloth as varchar) saddlecloth, x.segment_end_m e, x.split_s sp, x.{icol} cum from {tsec} x "
                        f"join _k on x.{rid} = _k.rid and cast(x.saddlecloth as varchar) = _k.saddlecloth").fetchdf()
        con.unregister('_k')
        sec = {}
        for (r_, sc), g in X.groupby(['rid', 'saddlecloth']):
            g = g.sort_values('e'); fin_m = g.e.max(); last = g[g.e == fin_m].iloc[0]
            at600 = g[g.e == fin_m - 600]
            l600 = round(float(last.cum - at600.cum.iloc[0]), 2) if len(at600) and pd.notna(last.cum) and pd.notna(at600.cum.iloc[0]) else None
            sec[(r_, str(sc))] = (l600, None if pd.isna(last.sp) else round(float(last.sp), 2))
        for _, r in S.iterrows():
            l6, l2 = sec.get((r.rid, str(r.saddlecloth)), (None, None))
            o = out.setdefault(r.k, {'held': {}, 'runs': []}); o['held'][st] = o['held'].get(st, 0) + 1
            o['runs'].append({'date': str(pd.Timestamp(r.d).date()), 'state': st, 'track': str(r.track).replace('_', ' ').replace('-', ' ').title(),
                              'distance_m': None if pd.isna(r.distance_m) else int(r.distance_m), 'finish': None if pd.isna(r.fin) else int(r.fin),
                              'time_s': round(float(r.t), 2), 'time_basis': 'derived (sum of measured sections)' if vic else 'measured',
                              'last600_s': l6, 'last200_s': l2})
    con.close()
    for o in out.values(): o['runs'] = sorted(o['runs'], key=lambda x: x['date'], reverse=True)[:per_horse]
    return out, present
