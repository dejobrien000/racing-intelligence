# TAB fetch test 2 (unattended scheduled session)

- Run: 2026-11-25 ~10:05–10:10 AEST (2026-11-25T00:05Z – 00:10Z), scheduled cloud session, no user present
- Goal: same as test 1, but with WebFetch called **directly** by the session (no web-fetch agent / subagent).
- Read-only. No bets, no publishing, no other tasks touched.
- **Result: NO.** WebFetch could not be called directly, because this session has no direct WebFetch tool. The test forbids a subagent, so step 1 was never sent, and steps 2–3 were not attempted (stop at first failure). No curl/Python fallback was used.

## Was WebFetch called directly?

**No.** It was not available to call.

- WebFetch was not among the session's loaded tools, and it was not on the deferred-tool list either.
- `ToolSearch` with query `select:WebFetch` returned exactly:

```
No matching deferred tools found
```

- A keyword `ToolSearch` (`web fetch url`) returned only `WebSearch`, `ArtifactComments`, `ArtifactData`, `Monitor` and `SuggestConnectors`. It did not return WebFetch.
- The only fetch route the session offered was the `web-fetch` agent type, which wraps WebFetch inside a subagent. Test 1 used that route. This test's instructions forbid it, so it was not used.

## Step 1: racing dates

- URL: `https://api.beta.tab.com.au/v1/tab-info-service/racing/dates?jurisdiction=NSW`
- Prompt: "Output ONLY lines: meetingDate|the full URL in _links.meetings"
- Worked: **No**, not sent. There was no direct WebFetch tool to send it with.
- Exact error text: no fetch error. The blocking result was the ToolSearch response above (`No matching deferred tools found`).
- Output: none

## Step 2: meetings for 2026-11-25 (raceType R, venueMnemonic GEL)

- URL: none. It would have been the 2026-11-25 `_links.meetings` URL returned by step 1.
- Prompt (planned): "Output ONLY the line for the meeting with raceType R and venueMnemonic GEL: meetingName|venueMnemonic|its races link URL"
- Worked: **Not attempted**, because step 1 failed
- Error text: n/a
- Output: none

## Step 3: GEL race 1 runners / fixed odds

- URL (planned): `https://api.beta.tab.com.au/v1/tab-info-service/racing/dates/2026-11-25/meetings/R/GEL/races/1?jurisdiction=NSW`
- Prompt (planned): "Output ONLY: RACE|raceNumber|fixedOddsUpdateTime|hasFixedOdds then runnerNumber|runnerName|fixedOdds.returnWin per runner"
- Worked: **Not attempted**, because step 1 failed
- Error text: n/a
- Output: none

## Comparison with test 1

| | Test 1 (`tab-fetch-test`) | Test 2 (this run) |
|---|---|---|
| Fetch route | web-fetch agent (WebFetch inside a subagent) | direct WebFetch required |
| Step 1 outcome | WebFetch ran; refused by its permission gate (`PROVENANCE_REQUIRED`, approval prompt timed out) | WebFetch not available as a direct tool; nothing sent |
| TAB reached? | No | No |

## Notes

- In this environment, the scheduled cloud session exposes WebFetch only through the `web-fetch` agent, not as a tool the main session can call. A "call WebFetch directly" test can't run here until a direct WebFetch tool is enabled for these sessions.
- Even with a direct tool, test 1 suggests the next blocker would be WebFetch's per-URL permission prompt, because no one is present to approve it. Pre-approving `api.beta.tab.com.au` for WebFetch, or turning on automatic approval for the scheduled task, is probably needed as well.
- The existing clone of `dejobrien000/racing-intelligence` was used. Branch `tab-fetch-test-2` was cut from `origin/main` (6b0b387).
