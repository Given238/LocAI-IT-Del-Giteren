# LocAI Build Playbook — Phase by Phase

Run one phase at a time. Don't start the next phase until the "Verify" checks for the current one pass.

**Status: Phases 1-3 complete and verified.** This update adds Phase 4 (geospatial + locale features) before deployment.

---

## Phase 1 — ETL pipeline ✅ DONE

Raw Excel → clean PostgreSQL. Verified: 143 attractions, 33 hotels, 151 restaurants, 16 transport, 12 kuliner, ~22k reviews loaded. `needs_review` flags in place for corrupted/implausible rows instead of silent guessing. See CLAUDE.md "Dataset" section for full verified numbers.

## Phase 2 — Backend API ✅ DONE

FastAPI `/itinerary` (SQL-filter → SEA-LION rank/narrate → ID re-resolution) and `/health`. Verified against all 5 sample prompts. Feasibility bug (NULL prices passing budget filter) found and fixed. Rate-limit backoff and JSON-parse retry implemented.

## Phase 3 — Frontend ✅ DONE

React + Vite, desktop-first, wired to the real backend. Structured data (name/price/address) is primary content; narrative is secondary, generic supporting text. Loading state, two distinct error states (infeasible budget vs. hard failure) both verified via real browser testing (Playwright), including killing the backend mid-request.

**Reminder:** always open the app via the Vite dev server URL (`npm run dev`, typically `http://localhost:5173`), never via Live Server or another static-file server — Vite/React needs its own dev server to bundle and serve the app correctly.

---

## Phase 4 — Geospatial distance + locale-tone dropdown (current)

**Goal:** Add two scoped, low-risk features — distance-from-start-location and a SEA-locale tone dropdown — without touching the anti-hallucination guarantees already built.

**Prompt for Claude Code:**
```
Read CLAUDE.md for full context, including the "New Features" section.

Add two features to the existing app:

1. GEOSPATIAL DISTANCE
   - Create a hardcoded lookup table (Python dict or small JSON file) 
     mapping ~15-20 known Toba-region towns/hubs to lat/long coordinates: 
     Medan, Sibolga, Parapat, Balige, Silangit Airport, Tuktuk, Samosir, 
     and other locations that appear as start_location values in the 
     5 sample prompts or are common real entry points to Toba.
   - Implement haversine distance calculation (pure Python, no external 
     API/library needed) between the user's matched start location and 
     each candidate's lat/long.
   - If the user's typed start_location doesn't match any entry in the 
     lookup table, do not guess — return the itinerary without distance 
     data for that request rather than picking the nearest-sounding name.
   - Add distance (in km) to each place in the /itinerary response.
   - Update the frontend to display "X km from [start location]" on 
     each place card.

2. LOCALE-TONE DROPDOWN
   - Add a dropdown to the frontend form (near the results, similar 
     placement/style to a model-picker dropdown) listing a handful of 
     SEA locales/origins (e.g. Indonesian, Malaysian, Singaporean, 
     Filipino, Thai, Vietnamese — adjust the list to whatever makes 
     sense, this is a tone parameter, not a translation system).
   - Pass the selected locale into the existing SEA-LION narrative 
     system prompt as a parameter, instructing it to adjust tone/
     phrasing/language familiarity accordingly.
   - This must ONLY affect the narrative text generation step — do NOT 
     let it touch the SQL filtering, candidate selection, or the 
     ID-based fact resolution. The structured data (name/price/address) 
     must remain identical regardless of locale selection.
   - Default to a neutral/general tone if no locale is selected.

Write or update a test script that runs a couple of the 5 sample 
prompts with different locale selections, so I can compare the 
narrative tone side by side, and with/without a recognized start 
location to confirm the "no guessing" fallback works.

When done, commit and push.
```

**Verify before moving on:**
- Distances shown are directionally sane — spot check 2-3 against a real map mentally (e.g. Parapat to a Samosir attraction should be a short distance, not hundreds of km)
- Try a start_location NOT in the lookup table — confirm it returns the itinerary without fabricated distance data, not a guessed nearest match
- Run the same prompt with 2-3 different locale selections — confirm the narrative tone actually changes, but the structured data (names/prices/addresses) is byte-for-byt identical across all of them
- Confirm this didn't slow down response time meaningfully past your ~5s target

**Watch out for:**
- Claude Code being tempted to "fuzzy-match" an unrecognized start location to the nearest lookup entry — this is the same kind of silent-guessing risk you already caught once in the ETL price parsing. Explicitly block it, as the prompt above does.
- Locale selection leaking into anything beyond narrative tone — if you notice different place recommendations appear when only the locale (not budget/interests) changes, something's wrong with the separation between retrieval and generation.

---

## Phase 5 — Full end-to-end test

- Run all 5 sample prompts through the browser, now including locale and distance display
- Have Partner 2 and Partner 3 try it too
- Decide here whether there's time for the NLP sentiment-extraction stretch goal (review sentiment scoring), or whether to prioritize deployment/deliverables instead — don't add it if it puts the required deliverables at risk

## Phase 6 — Deployment

**Prompt for Claude Code:**
```
Deploy the app: frontend to Vercel, backend to [Vercel serverless 
functions or a small host of your choice], database already on Neon. 
Make sure DATABASE_URL and SEA-LION credentials (LLM_API_KEY, 
LLM_BASE_URL, LLM_MODEL) are set as environment variables on the 
hosting platform, not committed to the repo. Confirm .env is in 
.gitignore. Give me the live URL when done.
```

**Verify before moving on:**
- Open the live URL on a phone AND a laptop
- Run the 5 sample prompts against the live deployed version
- Check no institution name appears anywhere (page title, footer, meta tags, code comments)

## Phase 7 — Android port

Only start once Phase 6 is stable and demoed successfully. Discuss React Native vs. Capacitor with Claude Code when you get here — Capacitor (wraps the existing React web app) is likely faster given the "ASAP" priority, but confirm with current project state before committing.

---

## Remaining required deliverables (not code, but on the critical path)

These are not phases in the technical sense but are required for submission and currently at zero progress per last check-in:

- **LaporanAnalisis.pdf** — full written report (structure per challenge doc §8)
- **Ringkasan Penggunaan Data** — dataset usage/cleaning summary (you already have all the real numbers for this from the Phase 1 verification reports)
- **Rencana Implementasi** — post-hackathon plan; **include the deferred open-ended chatbot here** as planned future work
- **Slide Pitching deck**
- **Video Demo** (5-10 min)

Recommend checking in with Partner 2/3 on these now, in parallel with Phase 4-5 — they don't block your coding work, but they do block submission.

---

## General rules for the whole build

- Commit after every phase, not just at the end
- Test in layers — isolate whether a problem is data, backend, or frontend before debugging
- Don't let Claude Code guess at missing/ambiguous data — flagging is always better than fabricating
- Keep the 5 sample prompts as your constant test set
- Always access the frontend via its actual dev server URL, never a generic static-file server