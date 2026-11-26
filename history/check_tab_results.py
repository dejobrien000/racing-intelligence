"""Weekly results cross-check: TAB nightly results vs Breednet (approved by Damo 26 Nov 2026, foundation step 3). It replaces the
ongoing Betfair cross-check (Betfair has no forward feed after Oct 2026); the historical Betfair validation tables (bf, bf_runner,
coverage_betfair, checks) are kept unchanged.
WHAT TAB SUPPLIES: finishing positions 1-4 only, plus each runner's betting status (scratchings). So this check validates the
first four places and the scratchings of each race. It does NOT validate positions 5+ or margins: those rest on Breednet alone,
and the report says so on every line.
Usage: python3 history/check_tab_results.py <history.duckdb>   (after load_tab_daily.py)
Table tab_results_check: one row per race in TAB results files: places compared (<= 4), agree, disagree, not yet in Breednet,
TAB-scratched horses Breednet shows as finishing (should be 0), dead heats noted."""
import sys, duckdb, pandas as pd
con = duckdb.connect(sys.argv[1])
T = con.execute("""select r.race_date, r.venue_code, r.race_no, r.saddlecloth, r.horse, regexp_replace(upper(r.name_key), '[^A-Z0-9]', '', 'g') k, r.finish_pos, r.finish_supplied,
                          lower(coalesce(r.betting_status, '')) st, r.file
                   from tab_runner r where r.kind = 'results'""").fetchdf()
B = con.execute("""select cast(meeting_date as varchar) race_date, regexp_replace(upper(name_key), '[^A-Z0-9]', '', 'g') k, finish_pos bn_pos from bn_runner""").fetchdf().drop_duplicates(['race_date', 'k'])
X = T.merge(B, on=['race_date', 'k'], how='left')
rows = []
for (d, v, rn, f), g in X.groupby(['race_date', 'venue_code', 'race_no', 'file']):
    sup = g[g.finish_supplied == 1]; inbn = g.bn_pos.notna().any()
    scr = g[g.st.str.contains('scratch')]
    rows.append({'race_date': d, 'venue_code': v, 'race_no': rn, 'file': f, 'places_supplied_by_tab': len(sup), 'race_in_breednet': bool(inbn),
                 'places_agree': int((sup.finish_pos == sup.bn_pos).sum()) if inbn else None, 'places_disagree': int(((sup.finish_pos != sup.bn_pos) & sup.bn_pos.notna()).sum()) if inbn else None,
                 'places_missing_in_breednet': int(sup.bn_pos.isna().sum()) if inbn else None, 'tab_scratched_but_finished_in_breednet': int(scr.bn_pos.notna().sum()) if inbn else None,
                 'dead_heat_in_tab': bool(sup.finish_pos.duplicated().any()), 'note': 'validates places 1-4 and scratchings only; places 5+ and margins rest on Breednet alone'})
O = pd.DataFrame(rows)
con.register('o_', O); con.execute('create or replace table tab_results_check as select * from o_')
c = O[O.race_in_breednet]
print(f"tab results check: races {len(O)} | in Breednet {len(c)} (rest not yet collected) | places compared {int(c.places_supplied_by_tab.sum()) if len(c) else 0}, "
      f"agree {int(c.places_agree.sum()) if len(c) else 0}, disagree {int(c.places_disagree.sum()) if len(c) else 0} | scratched-but-finished {int(c.tab_scratched_but_finished_in_breednet.sum()) if len(c) else 0}")
