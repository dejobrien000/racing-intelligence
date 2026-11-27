import pandas as pd, numpy as np, json, sys
out={}
for lab,v in [(x.split(':')[0],x.split(':')[1]) for x in sys.argv[1:]]:
    U=pd.read_parquet(f'/tmp/cand/frames/{v}_national.parquet',columns=['race','horse','date','state','field','dyn_nat_inn','r_debut']).sort_values(['horse','date','race']); U['k']=U.groupby('horse').cumcount()
    U=U[(U.state!='QLD')&(U.date>='2024-01-01')&(U.field>=6)&U.dyn_nat_inn.notna()].copy()
    U['light']=(U.k<=2).astype(float); g=U.groupby('race'); U['n']=g.horse.transform('size'); U['sh']=(g.light.transform('sum')-U.light)/(U.n-1)
    U['maiden_like']=g.k.transform('max')<=2
    E=U[U.k>=12]; sl=np.polyfit(E.sh,E.dyn_nat_inn,1)[0]
    D=U[(U.k==0)&(U.r_debut==1)]; M=U[(U.k==0)&(U.r_debut==0)]; L=U[U.k.between(1,2)]; X=U[U.k.between(3,5)]
    out[lab]={'established_slope_per_100pct_light_rivals':round(float(sl),2),'established_mean':round(float(E.dyn_nat_inn.mean()),2),
      'genuine_debut_mean':round(float(D.dyn_nat_inn.mean()),2),'genuine_debut_in_all_inexperienced_fields':round(float(D[D.maiden_like].dyn_nat_inn.mean()),2),
      'genuine_debut_with_established_rivals':round(float(D[~D.maiden_like].dyn_nat_inn.mean()),2),'missing_career_first_held_mean':round(float(M.dyn_nat_inn.mean()),2),'n_missing_career':int(len(M)),
      'runs_1_2_mean':round(float(L.dyn_nat_inn.mean()),2),'runs_3_5_mean':round(float(X.dyn_nat_inn.mean()),2),'debut_sq_err':round(float((D.dyn_nat_inn**2).mean()),2)}
    print(lab,out[lab],flush=True)
json.dump(out,open('/tmp/refmix_out.json','w'),indent=1)
