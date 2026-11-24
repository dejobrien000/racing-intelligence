"""Make the self-contained copy of the dashboard: the same index.html with one day's JSON embedded, so it opens by
double-click (no server). The published artifact instead serves index.html + data/*.json and fetches them.
Usage: python3 ui/build_standalone.py 2026-11-25  -> ui/dist/racing_intelligence_2026-11-25.html"""
import sys, os, json
d = sys.argv[1]; html = open('ui/index.html', encoding='utf-8').read(); data = open(f'ui/data/racing_{d}.json', encoding='utf-8').read()
json.loads(data)
tag = '<script id="ri-data" type="application/json"></script>'
assert html.count(tag) == 1
out = html.replace(tag, '<script id="ri-data" type="application/json">' + data.replace('</', '<\\/') + '</script>')
os.makedirs('ui/dist', exist_ok=True); p = f'ui/dist/racing_intelligence_{d}.html'; open(p, 'w', encoding='utf-8').write(out); print(p, os.path.getsize(p))
