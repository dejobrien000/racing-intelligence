"""One-off structure probe for Racing Queensland stewards' reports (GitHub runner). Saves raw pages to probe_out/."""
import requests, time, os, re
UA = 'RacingIntelligence-private/0.2 (personal research; github.com/dejobrien000)'
S = requests.Session(); S.headers['User-Agent'] = UA
B = 'https://www.racingqueensland.com.au'
urls = {'calendar': B + '/racing/full-calendar',
        'cal_thoroughbred': B + '/racing/full-calendar/thoroughbred',
        'meeting_ipsw': B + '/racing/full-calendar/thoroughbred/meeting/ipsw/20260620',
        'stewards_ipsw': B + '/racing/full-calendar/thoroughbred/meeting/ipsw/20260620/stewards-report',
        'stewards_gatt_2022': B + '/racing/full-calendar/thoroughbred/meeting/gatt/20221025/stewards-report',
        'stewards_efm_2026': B + '/racing/full-calendar/thoroughbred/meeting/e%20fm/20260530/stewards-report',
        'sitemap': B + '/sitemap.xml',
        'racefields_ipsw_20260620.pdf': B + '/RacingFile.ashx?path=/ThoroughbredMeetingFiles/rfd_IPSW_20260620.pdf',
        'racefields_gcst_20261122.pdf': B + '/RacingFile.ashx?path=/ThoroughbredMeetingFiles/rfd_GCST_20261122.pdf'}
os.makedirs('probe_out', exist_ok=True)
for k, u in urls.items():
    try: r = S.get(u, timeout=60); open(f'probe_out/{k}' + ('' if k.endswith('.pdf') else '.html'), 'wb').write(r.content); print(k, r.status_code, len(r.content), r.headers.get('content-type'))
    except Exception as e: print(k, 'ERR', e)
    time.sleep(2.5)

# second pass (26 Nov 2pm): do race-fields PDFs carry gear changes?
import subprocess
for f in os.listdir('probe_out'):
    if f.endswith('.pdf'):
        try:
            import pdfplumber
            with pdfplumber.open('probe_out/' + f) as pdf: t = '\n'.join((p.extract_text() or '') for p in pdf.pages)
            open('probe_out/' + f + '.txt', 'w').write(t); print(f, 'pages', len(t), 'gear mentions', len(re.findall(r'gear|blinker|first time|tongue', t, re.I)))
        except Exception as e: print(f, 'pdf text ERR', e)
