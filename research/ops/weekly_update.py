"""Weekly incremental master-database update (GitHub Actions). Status 25 Nov 2026: NOT YET IMPLEMENTED.
The original history was collected by browser collectors (collectors/*.js, breednet/*) running in Damo's Chrome.
They must be ported to run here (GitHub's servers reach Racing Queensland, Racing NSW FreeFields, Breednet and
racing.com: probe/results.txt). Until then this step stops with a clear message, so no partial database is published."""
import sys
sys.exit('weekly_update: incremental collectors not yet ported to GitHub Actions; master database unchanged')
