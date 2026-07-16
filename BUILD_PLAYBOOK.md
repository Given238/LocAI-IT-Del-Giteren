# LocAI Build Playbook — Phase by Phase

How to use this: run one phase at a time. Don't start the next phase until the "Verify" checks for the current one pass. If Claude Code produces something broken, fix it _within_ the phase before moving on — bugs compound fast in a vibe-coded project, and it's much harder to tell later whether a problem is in the data, the backend, or the frontend if you've skipped verification.

---

## Phase 1 — ETL pipeline (raw Excel → clean PostgreSQL)

**Goal:** Turn the messy spreadsheet into clean, queryable tables. Nothing else can start until this works.

**Prompt for Claude Code:**

```
Read CLAUDE.md for full project context.

Build the ETL pipeline: a Python script (scripts/etl.py) that reads
Dataset_Tourism.xlsx and loads it into PostgreSQL (connection string
in .env as DATABASE_URL).

Requirements:
1. Drop blank/empty rows — most sheets are 85-99% empty padding rows,
   filter these out first.
2. Create an "attractions" table by merging wisata-metadata +
   tempat-wisata-v1, deduplicating by place name (case-insensitive,
   fuzzy match for near-duplicates). Keep the richer/more complete
   record when both sheets have the same place.
3. Fix hotel-metadata: some rows are miscategorized (restaurants
   tagged as hotels, at least one row has place-type = "China" which
   is corrupted). Reclassify into separate "hotels" and "restaurants"
   tables based on place-type, or flag unclear rows in a
   "needs_review" column instead of guessing.
4. Merge resto-metadata into the "restaurants" table from step 3.
5. Normalize price fields into numeric min/max columns — source data
   has mixed formats like "5.000 - 10.000" (range) and "100000"
   (single number).
6. Parse lat-long text into separate numeric latitude/longitude columns.
7. Create a "transport" table from the transportasi sheet.
8. Create a "kuliner" table from the kuliner sheet.
9. Create "reviews" tables from wisata-v2 and resto-hotel-v2, with a
   foreign key to the matching place — use fuzzy name matching since
   exact matches only link ~72% of wisata-v2 reviews to wisata-metadata.
   Log any reviews that can't be matched to a place instead of dropping
   them silently.
10. Print a clear before/after summary: row counts per sheet before
    cleaning, and row counts per table after cleaning, plus counts of
    anything flagged as "needs_review" or "unmatched".

When done, commit and push.
```

**Verify before moving on:**

- Script runs without errors and prints the summary
- Row counts roughly match what we found in the audit: ~139 attractions, ~36 hotels (minus miscategorized ones), ~148+ restaurants, ~16 transport routes
- Spot-check 5-10 rows directly in the database (or have Claude Code print samples) — do prices, addresses, and lat-long look sane, not garbled?
- Check the "needs_review" / "unmatched" counts — if huge (hundreds), something's wrong with the matching logic, not the data

**Watch out for:**

- Claude Code silently "fixing" data by guessing (e.g. inventing a price when one is missing) — explicitly tell it to flag missing/ambiguous data instead of filling it in, or your itinerary engine will present made-up facts as real ones
- Fuzzy matching being too aggressive (merging two genuinely different places because names are similar) — spot-check a few merges

---

## Phase 2 — Backend API (constraint filter + itinerary generation)

**Goal:** A working endpoint that takes budget/duration/location/interests and returns a real itinerary, grounded in the database — no frontend yet.

**Prompt for Claude Code:**

```
Read CLAUDE.md for context. Phase 1 (ETL) is complete and the database
is populated.

Build the FastAPI backend:
1. POST /itinerary endpoint accepting: budget (IDR), duration (nights),
   start_location (text), interests (optional list, e.g. ["nature", "culinary"])
2. Query PostgreSQL to filter candidate attractions/hotels/restaurants/
   transport that fit the budget and match interests — this filtering
   happens in SQL, before any LLM call.
3. Pass the filtered candidates + constraints to an LLM to rank and
   write a day-by-day itinerary narrative. Use SEA-LION via the `openai`
   Python client pointed at `base_url=LLM_BASE_URL` (SEA-LION is
   OpenAI-compatible), auth with `LLM_API_KEY` as the bearer token,
   model id from `LLM_MODEL` — all from .env, called server-side only.
   SEA-LION's rate limit is 10 requests/minute — handle 429 responses
   with backoff/retry rather than letting the endpoint hard-fail.
4. Return structured JSON: itinerary days, each with attraction/food/
   lodging/transport picks including name, price, address — plus a
   short narrative summary.
5. If no candidates fit the budget/constraints, return a clear message
   instead of forcing a bad recommendation.
6. Add a simple /health endpoint to confirm the API and DB connection
   are alive.

Write a short scripts/test_prompts.py that sends the 5 example prompts
from the dataset's "prompt" sheet to /itinerary and prints the responses,
so we can manually check output quality.

When done, commit and push.
```

**Verify before moving on:**

- `/health` returns OK
- Run `scripts/test_prompts.py` — read all 5 responses yourself. Do the recommended places, prices, and totals actually make sense against the budget stated in each prompt?
- Every place named in a response should be a real row in your database — spot check 2-3 by looking them up directly
- Try one deliberately impossible prompt (e.g. absurdly low budget) — does it fail gracefully instead of hallucinating?

**Watch out for:**

- The LLM inventing details not in the candidate set it was given (prices, hours, names) — if you see this, the prompt sent to the LLM needs to more strongly constrain it to only use provided data
- Response times — if itinerary generation takes >10s, note it now; it'll be worse once a UI is waiting on it

---

## Phase 3 — Frontend (React, desktop-first)

**Goal:** A usable UI wired to the real backend from Phase 2 — do not build this against fake/hardcoded data.

**Prompt for Claude Code:**

```
Read CLAUDE.md for context. Backend API from Phase 2 is live at
[your local/deployed URL].

Build the React frontend, desktop-first:
1. A form: budget, duration, starting location, interest checkboxes
2. Submit calls POST /itinerary on the real backend (no mock data)
3. Results view: day-by-day itinerary cards showing place name, price,
   address, and the narrative text
4. Loading state while waiting for the API (can take several seconds)
5. Error state if the API fails or returns "no candidates fit"

Keep it clean and simple — this needs to demo well, not be feature-rich.

When done, commit and push.
```

**Verify before moving on:**

- Submit all 5 sample prompts through the actual UI, not just the API test script
- Loading and error states both actually trigger and look reasonable (test by disconnecting the backend briefly)
- Check it still looks correct at a normal desktop width — no broken layout

**Watch out for:**

- Silent mock data — check the network tab in browser devtools to confirm the frontend is actually calling your backend, not showing hardcoded placeholder content left over from scaffolding

---

## Phase 4 — Full end-to-end test

**Goal:** Confirm the whole system works together before you deploy or add extra AI features.

- Run through all 5 sample prompts start to finish in the browser
- Have Partner 2 and Partner 3 (non-coders) try it too — if they get confused or hit an error, that's a real UX problem, not just a "they don't code" issue
- This is the point to decide if you have time/need for the RAG/NLP enrichment (semantic search, review sentiment) mentioned in CLAUDE.md, or if the constraint-filter + LLM approach is already solid enough to prioritize deployment and polish instead

**Watch out for:**

- Don't add the NLP/RAG enrichment layer until this core flow is rock solid — it's a nice-to-have for the AI-quality score, not a requirement, and a broken core demo scores worse than a simple, working one

---

## Phase 5 — Deployment

**Prompt for Claude Code:**

```
Deploy the app: frontend to Vercel, backend to [Vercel serverless
functions or a small host of your choice], database already on Neon.
Make sure DATABASE_URL and the LLM API key are set as environment
variables on the hosting platform, not committed to the repo.
Confirm .env is in .gitignore. Give me the live URL when done.
```

**Verify before moving on:**

- Open the live URL on a phone AND a laptop, not just localhost
- Run the 5 sample prompts against the live deployed version — deployment often breaks env vars or CORS even when local worked fine
- Check no institution name appears anywhere (page title, footer, meta tags) — required by the rules

---

## Phase 6 — Android port

Only start this once Phase 5 is stable and demoed successfully at least once. Options to discuss with Claude Code when you get here: React Native (rewrite, more native feel) vs Capacitor (wraps your existing React web app, much faster). Given the "ASAP" priority, Capacitor is likely the pragmatic choice — flag this decision back to me when you're ready and I'll help you think it through with more context on where you're at.

---

## General rules for the whole build

- **Commit after every phase**, not just at the end — if something breaks later, you want to know exactly which phase introduced it
- **Test in layers** — don't debug the frontend for a problem that's actually in the backend or the data. Use the phase checkpoints to isolate where things break
- **Don't let Claude Code guess at missing data** — flagging is always better than fabricating, both for correctness and because judges are scoring how you handled messy data
- **Keep the 5 sample prompts as your constant test set** from Phase 2 onward — every phase should be checked against them
