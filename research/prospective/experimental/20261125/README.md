# EXPERIMENTAL - not the official prediction
Written 2026-11-25T01:03:43Z, before Ipswich race 1 (1:02pm Brisbane, 03:02 UTC), on exactly the same fields as the official
7:56am set (RQ snapshot 20261124T215130Z, after final scratchings).

Why: the Queensland pre-race scorer gives the national dynamic rating zero weight. History rows never receive their Qld ids,
so the rating's development spread is blank and every live value becomes 0 (prerace/score_prerace.py, UN = concat(...)).
The fix keeps the Qld ids on history rows; the rebuilt spread is 2.939 kg, identical to the frozen research value (2.9392).
v2 (experimental) = official v2 score - official v1 score + fixed v1 score; chance = softmax within race. Calibrated columns
use benchmarks/engine_v2/runner_calibration.json. The official published set is unchanged.
