# Browser collectors (run in Chrome on the source site's own page)

- nsw_freefields.js  Racing NSW results pages, one request per meeting. Keeps ~4 months. Load on mdata.racingnsw.com.au.
- racingcom_results.js  racing.com results per race (NSW + VIC). Heavy pages: daily use only.
- racingcom_speed.js  racing.com Victorian speed data per race (light). Load on dxp-static.racing.com/sectionals/index.html.
- ../history/browser_bundle.js  Racing Queensland files + Betfair bundles (24 Nov load).

Each stores to IndexedDB 'racing_bundles' store 'b'; export as .jsonl.gz and load with
history/load_nsw_vic.py <bundle folder> history.duckdb (after history/load_history.py).
Never pass prices into storage. Stop on any CAPTCHA or "Are you human?" page.


## Added 24 Nov 2026
- `breednet_results.js` + `breednet_dates.js`: Breednet results, every finisher, all Australian states, from at least 2019.
  Light (plain fetch, no rendering). Date-driven: the daily index `/results/daily-results?t_date=YYYY-MM-DD` lists every
  meeting; each meeting page gives class, track rating, race time and last 600m, prize, and per runner position, margin,
  saddlecloth, weight, jockey, trainer, age, sex, sire, dam, dam's sire. No barriers, no in-running, no sectionals.
  Saved as `bnidx:DATE` and `bnm:DATE:slug`. The weight cell on the page also shows the starting price; the parser keeps
  only the number, and `history/load_breednet.py` refuses any record that still has price text.
  NSW/ACT/Vic venue slugs used for the backfill:
  albury,ararat,armidale,avoca,bairnsdale,ballarat,ballarat-synthetic,ballina,bathurst,beaumont-newcastle,benalla,bendigo,
  bowraville,burrumbeet,camperdown,canberra,canterbury,canterbury-park,casino,casterton,caulfield,caulfield-heath,cessnock,
  coffs-harbour,colac,coleraine,coonabarabran,coonamble,cootamundra,corowa,cowra,cranbourne,donald,dubbo,dunkeld,echuca,
  edenhope,flemington,forbes,geelong,geelong-synthetic,gilgandra,glen-innes,gosford,goulburn,grafton,great-western,griffith,
  gunbower,gundagai,gunnedah,hamilton,hanging-rock,hawkesbury,horsham,illawarra-grange,inverell,kembla-grange,kempsey,
  kensington,kerang,kilmore,kyneton,leeton,lismore,manangatang,mildura,moe,moonee-valley,moree,mornington,mortlake,moruya,
  mudgee,murtoa,murwillumbah,muswellbrook,narrandera,narromine,newcastle,newcastle-beaumont,nhill,nowra,orange,pakenham,
  pakenham-synthetic,parkes,penshurst,port-macquarie,queanbeyan,quirindi,randwick,randwick-kensington,rosehill,
  rosehill-gardens,royal-randwick,sale,sandown,sandown-hillside,sandown-lakeside,sapphire-coast,scone,seymour,st-arnaud,
  stawell,stony-creek,swan-hill,tamworth,taree,tatura,terang,the-valley,towong,traralgon,tumut,tuncurry,wagga,wagga-wagga,
  walcha,wangaratta,warracknabeal,warren,warrnambool,warwick-farm,wellington,werribee,wodonga,wycheproof,wyong,yarra-valley
- `nsw_allform.js`: Racing NSW FreeFields `Form.aspx` for each saved NSW race meeting: every horse's full career form lines,
  including barrier, positions at 800m and 400m, race time and race last 600m, class, prize, NSW rating ("Rtg"), and
  interstate runs. Kept about 4 months like the results pages. Saved as `nswform:KEY`; trailing price sequences removed.
  Caution: covers only horses still racing in NSW in that window (survivor bias for older seasons).
