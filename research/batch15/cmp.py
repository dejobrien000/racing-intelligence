import pandas as pd, numpy as np, sys, os
rng=np.random.default_rng(5); b=pd.read_parquet('/tmp/cand/res_C2_R.parquet')
for V in sys.argv[1:]:
    f=f'/tmp/cand/res_{V}_R.parquet'
    if not os.path.exists(f): print(V,'missing'); continue
    a=pd.read_parquet(f)
    for win in ['A','B']:
        x=a[a.window==win].set_index('race_id'); y=b[b.window==win].set_index('race_id')
        j=x[['lp','hit']].join(y[['lp','hit']],lsuffix='_u',rsuffix='_c',how='inner'); d=(j.lp_u-j.lp_c).values
        bs=d[rng.integers(0,len(d),(2000,len(d)))].mean(1)
        print(V, win, 'races', len(j), 'gain', round(d.mean(),5), np.percentile(bs,[2.5,97.5]).round(5).tolist(), 'top pick pts', round(100*(j.hit_u.mean()-j.hit_c.mean()),2))
