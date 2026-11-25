# TAB fetch test (unattended scheduled session)

- Run: 2026-11-25 ~09:57–10:03 AEST (2026-11-24T23:57Z – 2026-11-25T00:03Z), scheduled cloud session, no user present
- Goal: can an unattended session read TAB's public racing data by following `_links` with WebFetch?
- Method: WebFetch (via the session's web-fetch agent; no direct WebFetch tool in this session). Read-only. No bets, no publishing.
- **Result: NO.** Step 1 was refused by WebFetch's permission gate (the approval prompt timed out with no one to answer it), so steps 2–4 had no URL to follow and were not attempted. No fallback (curl/Python) was used, by design.

## Step 1 — racing dates

- URL: `https://api.beta.tab.com.au/v1/tab-info-service/racing/dates?jurisdiction=NSW`
- Prompt: "Output ONLY lines: meetingDate|the full URL in _links.meetings"
- Worked: **No**
- Exact error text:

```
{"error_type":"PROVENANCE_REQUIRED","source":"target","message":"The permission request for this URL was not answered in time. Do not retry. Continue without this page and report the blocked URL in your findings."}
```

- Output: none (no content returned)

## Step 2 — meetings for 2026-11-25 (GEL, raceType R)

- URL: none — would have been the `_links.meetings` URL for 2026-11-25 from step 1
- Worked: **Not attempted** (blocked by step 1)
- Error text: n/a

## Step 3 — GEL races list

- URL: none — would have been GEL's `_links.races` URL from step 2
- Worked: **Not attempted** (blocked by step 2)
- Error text: n/a

## Step 4 — GEL race 1 runners / fixed odds

- URL: none — would have been race 1's `_links.self` URL from step 3
- Worked: **Not attempted** (blocked by step 3)
- Output: none

## Notes

- `PROVENANCE_REQUIRED` with "permission request ... was not answered in time" means WebFetch needs a person to approve `api.beta.tab.com.au` (a URL the user typed into the stored prompt was still not enough on its own in this unattended run). It is a permission gate, not a TAB-side block or a network error.
- To make this work unattended, the TAB host likely needs to be pre-approved for WebFetch (e.g. an allow rule for `api.beta.tab.com.au` in the session/project permission settings, or "Automatically approve" on the scheduled task), then re-run this test.
- `add_repo` was not available in this session; the existing clone of `dejobrien000/racing-intelligence` was used.
