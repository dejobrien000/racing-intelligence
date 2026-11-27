"""Batch 17 B2: integrity check of the Queensland common-framework shadows against production v2.1.3 on the same morning fields
(runner set, chance sums, rank agreement, served input coverage vs Queensland training rows). Usage: python3 batch16/b17_qld_shadow_integrity.py <root> <YYYYMMDD>"""
import pandas as pd, glob, json, numpy as np, sys
root=sys.argv[1]; D=sys.argv[2]
P=pd.read_csv('prospective/prerace/INDEX.csv'); P=P[(P.date.astype(str)==D)&P.file.str.contains('/v2_')&P.file.str.endswith('_runners.csv')].sort_values('scored_utc')
out={}
for C in ['c2','c4']:
    rows=[]
    for f in sorted(glob.glob(f'{root}/{C}/{D}/*/v2_*_runners.csv')):
        trk=f.split('/')[-2].replace('_',' '); pf=P[P.track==trk].drop_duplicates('track',keep='last').file.iloc[0]
        x=pd.read_csv(f); y=pd.read_csv(pf); j=x.merge(y[['race_no','saddlecloth','v2_chance_pct']],on=['race_no','saddlecloth'],suffixes=('','_prod'),how='outer',indicator=True); j['track']=trk; rows.append(j)
        if C=='c2' and trk=='Cairns': S=json.load(open(f.replace('_runners.csv','_manifest.json')))['settings']; print(S['engine_version'],'|',S['output'],'|',list(S['settings_files_loaded']),'|',S['rating_build']['history_frame'],'| scale',round(S['rating_scale_model_units_per_kg'],4),'|',S['rating_update_settings'])
    J=pd.concat(rows, ignore_index=True)
    sums=J.groupby(['track','race_no']).v2_chance_pct.sum()
    tp=[int(g.v2_chance_pct.idxmax()==g.v2_chance_pct_prod.idxmax()) for _,g in J.groupby(['track','race_no'])]
    out[C]={'runners': int(J.v2_chance_pct.notna().sum()), 'production_runners': int(J.v2_chance_pct_prod.notna().sum()), 'unmatched': int((J._merge!='both').sum()), 'races': len(sums), 'chance_sum_min': round(float(sums.min()),3), 'chance_sum_max': round(float(sums.max()),3),
            'corr_with_v2_1_3': round(float(J.v2_chance_pct.corr(J.v2_chance_pct_prod)),3), 'same_top_pick_share': round(float(np.mean(tp)),3), 'largest_change_pts': round(float((J.v2_chance_pct-J.v2_chance_pct_prod).abs().max()),1)}
    print(C, out[C])
    if C=='c2':
        cols=['dyn_nat','f_avgfp3','a_rec','a_best3','c_rec','g_rec','d_rec','j_surp','t_surp','age_n','female','h2h','surprise_last','dyn_traj','dist_change','wt_change','bm_change','b22_h_sd','b22_below_top3','b22_venue_step']
        Js=J[J._merge!='right_only']; served={c: round(100*float(Js[c].isna().mean()),1) for c in cols if c in Js}; print('served missing %', served)
        U=pd.read_parquet('engine/frames/national_c2.parquet'); q=U[(U.state=='QLD')&(U.date>='2025-01-01')]
        print('Qld training 2025-26 missing %', {c: round(100*float(q[c].isna().mean()),1) for c in cols if c in q}); out['served_missing_pct']=served
        print('c_rec nonzero share served', round(float((Js.c_rec.fillna(0)!=0).mean()),3), '| Qld training', round(float((q.c_rec.fillna(0)!=0).mean()),3))
json.dump(out, open(f'{root}/integrity_{D}.json','w'), indent=1)
