# pc-collect

Raw files delivered by the PC collector (pc_collector/ on main). One folder per Brisbane race date: pc/<YYYYMMDD>/.
A job manifest (morning_manifest.json, form_manifest.json, evening_manifest.json) is written LAST, only after every file it lists
has been uploaded and read back with a matching sha256. Downstream reads only files listed in a verified manifest.
Market prices in the racecard and results files are an evaluation layer only; form files carry no odds.
