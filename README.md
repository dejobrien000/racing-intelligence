# Staged Racing SA tracking (NOT in the master database; not read by production)
Built from branch raw-racingsa-tracking by history/stage_sa_tracking.py (main). Tables have the Queensland tracking shape:
sa_race ~ race, sa_starter ~ starter, sa_sectional ~ sectional (+ SA extras), plus sa_race_checks (use races with pass = true),
sa_problems, sa_file_format, sa_files. Report: sa_tracking_report.md. Loading into the master database is a separate release decision.
Rebuild: python3 history/stage_sa_tracking.py <raw dir> <master history.duckdb> <out.duckdb> <report.md>
