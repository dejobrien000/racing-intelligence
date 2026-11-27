"""Engine Performance tab data (display only; requested by Damo 27 Nov 2026). Reuses what already exists: the release lineage
(benchmarks/engine_lineage.json, copied from the release notes and gates) and the prospective evaluation ledger
(outputs/prospective_eval.csv, written by ops/evaluate_prospective.py from saved pre-race predictions). Reads no prices and
feeds no rating, coefficient or model decision.

build(day) -> dict for the day file's 'engine_performance' key (engine/export_ui.py calls it).
CLI (from research/): python3 engine/engine_performance.py <YYYYMMDD>   refreshes that key in ui/data/racing_<date>.json in place
(the daily run calls this after the evaluation ledger is updated, so the tab includes yesterday's races)."""
import os, sys, json, math
import pandas as pd

LINEAGE = 'benchmarks/engine_lineage.json'
LEDGER = 'outputs/prospective_eval.csv'
MIN_RACES = 300      # below this a per-race difference of ~0.01 cannot be told from noise (per-race sd of the difference is about 0.15)


def _fit(g):
    return round(100 * (1 - g.log_lik.sum() / g.null_log_lik.sum()), 2) if len(g) and g.null_log_lik.sum() != 0 else None


def _summary(g):
    return {'races': int(len(g)), 'days': int(g.date.nunique()), 'from': str(g.date.min()), 'to': str(g.date.max()), 'fit': _fit(g),
            'top_pick_pct': round(100 * g.top_pick_won.mean(), 1), 'top3_pct': round(100 * g.winner_in_top3.mean(), 1)}


def _status(n, lo, hi):
    if n < MIN_RACES: return f'Too few races to judge ({n} so far; about {MIN_RACES}+ needed before a difference of 0.01 per race shows)'
    if lo > 0: return 'Ahead of production, beyond noise'
    if hi < 0: return 'Behind production, beyond noise'
    return 'No clear difference yet'


def _paired(prod, other):
    k = ['date', 'meeting', 'race']
    j = prod[k + ['log_lik', 'top_pick_won', 'winner_in_top3']].merge(other[k + ['log_lik', 'top_pick_won', 'winner_in_top3']], on=k, suffixes=('_p', '_o'))
    n = len(j)
    if n == 0: return None
    d = j.log_lik_o - j.log_lik_p
    m = float(d.mean()); se = float(d.std(ddof=1) / math.sqrt(n)) if n > 1 else float('nan')
    lo, hi = (m - 1.96 * se, m + 1.96 * se) if n > 1 else (float('nan'), float('nan'))
    return {'races': int(n), 'gain_per_race': round(m, 4), 'lo': None if lo != lo else round(lo, 4), 'hi': None if hi != hi else round(hi, 4),
            'top_pick_pts': round(100 * (j.top_pick_won_o.mean() - j.top_pick_won_p.mean()), 1), 'top3_pts': round(100 * (j.winner_in_top3_o.mean() - j.winner_in_top3_p.mean()), 1),
            'status': _status(n, -1 if lo != lo else lo, 1 if hi != hi else hi)}


def build(day):
    L = json.load(open(LINEAGE))
    E = pd.read_csv(LEDGER) if os.path.exists(LEDGER) and os.path.getsize(LEDGER) > 0 else pd.DataFrame(columns=['date', 'prediction', 'engine', 'state', 'meeting', 'race', 'log_lik', 'null_log_lik', 'top_pick_won', 'winner_in_top3'])
    E['date'] = E.date.astype(str); E['fam'] = (E.state.astype(str) == 'QLD').map({True: 'QLD', False: 'NAT'})
    E = E[E.date < f'{day[:4]}-{day[4:6]}-{day[6:]}']                 # only races settled before this day's file
    fams = []
    for f in L['families']:
        e = E[E.fam == f['key']]; prod = e[e.prediction == 'production']
        cur = prod[prod.engine.astype(str).str.startswith(f['production_label_prefix']) & (prod.date >= f['production_from'])]
        prev = e[(e.prediction == 'previous_engine') & e.engine.astype(str).str.startswith(f['predecessor_label_prefix'])]
        by_engine = [{'engine': str(k), **_summary(g)} for k, g in prod.groupby('engine', sort=False)]
        by_engine.sort(key=lambda r: r['from'])
        fams.append({**{k: f[k] for k in ['key', 'label', 'production', 'production_from', 'predecessor', 'predecessor_status', 'change', 'chain']}, 'comparison_basis': f.get('comparison_basis'),
                     'identical_races': f.get('identical_races'), 'cumulative_note': f.get('cumulative_note'),
                     'since_release': _summary(cur) if len(cur) else None,
                     'vs_predecessor': _paired(cur, prev) if len(cur) and len(prev) else None,
                     'production_by_engine': by_engine,
                     'production_all': _summary(prod) if len(prod) else None})
    cands = []
    for c in L['candidates']:
        row = dict(c)
        if c.get('ledger_label_prefix'):
            e = E[E.fam == c['family']]; sh = e[(e.prediction == 'shadow') & e.engine.astype(str).str.startswith(c['ledger_label_prefix'])]
            prod = e[e.prediction == 'production']
            row['prospective'] = _summary(sh) if len(sh) else None
            row['vs_production'] = _paired(prod, sh) if len(sh) else None
        cands.append(row)
    return {'updated': L['updated'], 'ledger_races_to': str(E.date.max()) if len(E) else None, 'families': fams, 'candidates': cands, 'checkpoints': L.get('checkpoints_proposed'),
            'notes': ['Fit = how much better than random the winner\'s chance was (log-likelihood against a field-size baseline), as in every research table. '
                      'Gains are log-likelihood per race on identical races, with a 95% interval.',
                      'Prospective = saved pre-race predictions judged on races run after the engine went live; never refitted on those races. '
                      'Shadows and previous engines are scored before racing too, but are never shown as tips.',
                      'Historical figures are research results on past races, not live performance.']}


if __name__ == '__main__':
    D = sys.argv[1]; p = f'ui/data/racing_{D[:4]}-{D[4:6]}-{D[6:]}.json'
    J = json.load(open(p)); J['engine_performance'] = build(D)
    tmp = p + '.tmp'; json.dump(J, open(tmp, 'w'), separators=(',', ':'), allow_nan=False); os.replace(tmp, p)
    ep = J['engine_performance']; print('engine performance refreshed |', p, '| ledger to', ep['ledger_races_to'], '|',
                                        '; '.join(f"{f['label']}: {f['production']} {(f['since_release'] or {}).get('races', 0)} races since release" for f in ep['families']))
