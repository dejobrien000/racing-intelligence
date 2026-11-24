"""Shared research frames. next_start_frame(): one row per beaten finisher with its next start, ready for
"what happens next start" questions (used by lab.py and inv9_r9_deep.py)."""
import numpy as np, pandas as pd

def next_start_frame(path='runs_rated.parquet', level_until=None):
    d = pd.read_parquet(path).drop_duplicates(['race_id', 'horse_id'])
    for c in ['margin_l', 'distance_m', 'next_distance_m', 'next_field', 'next_win', 'l600_rank', 'settle_rel', 'gap_to_next', 'next_days_since']:
        d[c] = pd.to_numeric(d[c], errors='coerce').astype(float)
    lv = d if level_until is None else d[pd.to_datetime(d.meeting_date) <= pd.Timestamp(level_until)]
    level = lv.groupby('class_bucket')['rating'].median()               # class level in rating units (kg)
    d['class_level'] = d['class_bucket'].map(level); d['next_class_level'] = d['next_class_bucket'].map(level)
    d['class_delta'] = d['next_class_level'] - d['class_level']
    metro = {'Eagle_Farm', 'Doomben'}; prov = {'Sunshine_Coast', 'Sunshine_Coast_Poly_Track', 'TAB_Park_Gold_Coast', 'Ipswich', 'Toowoomba'}
    d['venue_tier'] = np.where(d.track.isin(metro), 'metro', np.where(d.track.isin(prov), 'provincial', 'country'))

    b = d[(d.field >= 6) & (d.next_field >= 6) & d.finished & d.l600_rank.notna() & (d.win == 0) & d.gap_to_next.between(7, 60)
          & (d.next_days_since == d.gap_to_next) & d.next_race_id.notna()].copy()        # true next start, no interstate run in between
    b['top_l600'] = (b.l600_rank == 1).astype(int)
    step = b.next_distance_m - b.distance_m
    b['step'] = pd.cut(step, [-1e9, -200, 199, 399, 1e9], right=False, labels=['down 200+', 'same (+/-199)', 'up 200-399', 'up 400+'])
    b['step_up'] = (step >= 200).astype(int); b['step_down'] = (step <= -200).astype(int)
    b['next_win'] = b['next_win'].astype(int)
    b['class_move'] = pd.cut(b.class_delta, [-99, -1.5, 1.5, 99], labels=['drops in class', 'same class', 'rises in class'])
    b['margin_band'] = pd.cut(b.margin_l, [0, 1, 2, 4, 8, 999], labels=['<=1L', '1-2L', '2-4L', '4-8L', '8L+'])
    b['dist_band'] = pd.cut(b.distance_m, [0, 1150, 1450, 1750, 9999], labels=['<=1150', '1200-1450', '1500-1750', '1800+'])
    b['fs_z'] = (b.field_strength - b.field_strength.mean()) / b.field_strength.std()
    b['strength_band'] = pd.qcut(b.field_strength, 3, labels=['weaker races', 'middle', 'stronger races'])
    b['fsp_rel'] = b.fsp - b.groupby('race_id')['fsp'].transform('median')
    b['next_fig_vs_avg3'] = b.next_rating - b.groupby('horse_id')['rating'].transform(lambda s: s.rolling(3, min_periods=1).mean())
    b['improved'] = (b.next_rating > b.rating).astype(float).where(b.next_rating.notna() & b.rating.notna())
    b['exp'] = 1 / b.next_field
    return b
