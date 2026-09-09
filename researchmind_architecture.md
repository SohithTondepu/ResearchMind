# ResearchMind — Architecture & Decision Log

Full reference for the `search_agent` (ResearchMind) project: what exists today, what's changing, and every design decision made along the way. No code — this is the spec.

---

## 1. Current State (Before This Round of Changes)

### Stack
- `app.py` — Streamlit UI, step-machine pipeline (one stage per rerun)
- `agents.py` — Gemini LLM setup (`gemini-3.6-flash`), `writer_chain`, `critic_chain`
- `tools.py` — search + scrape functions
- `pipeline.py` — CLI mirror of the same flow
- `.env` — `GOOGLE_API_KEY`, `TAVILY_API_KEY`

### History of fixes (prior sessions)
- Fixed import mismatch (`tool.py` → `tools.py`) and missing `streamlit` dependency
- Rebuilt run loop into a real live step-machine (was previously dead code)
- Added try/except error handling with Reset button (previously left UI stuck)
- Wired `tenacity` retries (3 attempts, exponential backoff) into search/scrape
- Added `.gitignore`, `.env.example`
- Switched LLM provider: OpenAI → Google Gemini (free tier, no card required)
- Fixed empty-box UI bug (`st.markdown` div-wrapping issue → real `st.container(border=True)`)

### Architecture principle established early
- **Search and Reader are NOT LLM agents.** Originally `build_search_agent()` let an LLM pick a URL from a truncated snippet — fragile, prone to bad picks. Replaced with deterministic search + user-driven review.
- **Writer and Critic use the LLM but are not "agents.”** Each is a single LangChain chain (prompt → LLM → parser) — one prompt-in/text-out call, no tool use, no autonomous looping.

### ⚠️ Known discrepancy
Earlier session notes described a Semantic Scholar credibility-ranking upgrade (`search_papers_topk`, citation + venue-bonus scoring). **This was never actually merged into the current codebase** — `tools.py`/`agents.py`/`pipeline.py`/`app.py` still use Tavily generic web search (`search_web_topk`). The design below is what replaces Tavily with a real Semantic Scholar integration.

---

## 2. New Design — Search & Ranking

### Retrieval
- **Semantic Scholar Graph API**, bulk search endpoint — fully deterministic, no LLM involved in query formation, ranking, or URL selection.
- Confirmed free: unauthenticated use works with no key (~100 requests / 5 min); optional `SEMANTIC_SCHOLAR_API_KEY` for higher limits. Academic/research use intended; commercial use needs separate permission. (Verify exact current limits against Semantic Scholar's own docs at implementation time.)

### Fields pulled per paper
`title, abstract, authors, year, venue, citationCount, externalIds, openAccessPdf, publicationTypes, fieldsOfStudy, url`

### User-facing parameters
- `topic` — query text
- `k` — max 10
- Bucket split ratio (default **60% established / 40% recent**, user-adjustable)

### Bucketing logic
| Bucket | Window | Citation floor | Ranking | Notes |
|---|---|---|---|---|
| **Established** | everything else | none | default citation-based score | **excludes** any paper already in the recent bucket (no overlap/duplication) |
| **Recent** | under **1.5 years** | 0 | **S2 relevance score** | citations-per-year shown for context, not used to rank (too noisy at low absolute counts for very young papers) |

### Why not a single blended ranking formula
Rejected: raw citation count (buries good recent work), pure citations-per-year (overweights very young papers with 1–2 lucky citations), percentile-within-cohort (more API calls for fairness benefit that mainly matters at large K). **Chosen: two explicit labeled buckets** — makes the impact-vs-recency tradeoff visible and adjustable instead of hidden inside formula constants.

### Presentation order
Established papers listed/reviewed before recent ones. *(Open item — see Section 6.)*

---

## 3. New Design — Review Flow

### Review card (identical structure for every paper, open-access or closed)
- **Metadata block:** title, authors (first 3 + "et al." if more), venue + year, citation count (+ citations/year if from recent bucket), open-access status (🔒 if closed), field of study, bucket label
- **Abstract:** cleaned (no boilerplate/line-break artifacts), sentence-safe truncation with expand — **never raw full text at review stage**, even for open-access papers. Full text is only used later, for report generation.

### Review loop — full redesign
- User goes through **all K candidates**, one at a time, marking each **satisfied / reject**.
- **Loop never exits early** — no more "stop at first accept." Every candidate gets a decision.
- Every paper marked **satisfied** gets its own **independent full report** — not one blended multi-source report. N accepted papers → N separate reports for the user to compare and choose from.
- **No cap** on how many satisfied papers get full reports (up to K=10 max even worst case).

---

## 4. New Design — Report Generation

### Source depth by access type
- **Open-access:** full scraped PDF/page text used for the report.
- **Closed (abstract-only):** before generating, show an explicit warning — *"This paper doesn't have full text available — the report will be based on the abstract only."* Proceed only on confirmation.

### Critic-revision loop
| Source type | Passes | Score | Notes |
|---|---|---|---|
| **Open-access** | **2** (Writer v1 → Critic v1 → Writer v2 → Critic v2) | Yes, shown each pass | Fixed passes regardless of score — not score-gated. All passes visible to user. |
| **Closed / abstract-only** | **1** (Writer → Critic) | **No numeric score** | Qualitative feedback only. |

### Faithfulness / grounding check (new critic responsibility)
- **Open-access:** deep-dive — critic checks report claims against actual full source text, across both passes.
- **Closed:** lighter, best-effort check against the abstract only (inherently shallow — abstracts don't cover most detail), within the single pass.
- **Output structure:** separate **"Factual Accuracy"** section in critic output — not folded into Strengths/Areas to Improve. Subjective quality notes and verifiable factual claims need to stay distinguishable.
- **Specificity:** claim-level and quoted/named, not general language (e.g. "Claim X is not supported by the source" — not "some claims may be weak"). Needed so the next Writer pass can target the actual problem.
- **Unresolved issues after final pass:** surfaced explicitly to the user as a flag near the report (e.g. "⚠ Unresolved accuracy concerns from final review") — not silently left buried in critic prose. Consistent with the project's general stance of not trusting unchecked LLM output.

### Generation timing (Streamlit-specific decision)
- Review loop for **all K candidates completes first**.
- **Then** reports for satisfied papers generate **sequentially**, each **rendering in the UI as soon as it completes** — incremental display, so the user isn't stuck waiting for all N reports before seeing any.
- **Rejected: true parallel/background generation** (starting a report the moment a paper is accepted, while review continues). Reason: Streamlit's rerun-per-interaction execution model makes real concurrency against shared session state risky (race conditions) and a much bigger architectural change than anything else in this project's pattern so far.

---

## 5. Agent Boundary — Where LLM Autonomy Is and Isn't Used

| Component | Uses LLM? | Agentic? |
|---|---|---|
| Search (Semantic Scholar) | No | No — deterministic API call |
| Bucketing / ranking | No | No — plain code/math |
| Reader (scrape) | No | No — plain function |
| Human review (accept/reject) | No | No — user decision |
| Writer | **Yes** | No — single prompt→text chain |
| Critic (single pass) | **Yes** | No — single prompt→text chain |
| **Critic-revision loop** | **Yes** | **Yes** — the one agentic component: bounded multi-pass loop with structured faithfulness-check responsibility |

No component performs autonomous tool selection or open-ended query/URL decisions — that was deliberately removed early in the project's history and the new design preserves it.

---

## 6. Open Items (Not Yet Resolved)

1. **Established-first vs recent-fallback mechanics** — now that review goes through *all* K candidates regardless, this mostly collapses into "established listed before recent" (pure display order). Simplest resolution: established papers simply appear first in the review sequence, recent papers after — no special fallback-only-if-empty logic needed. **Not yet explicitly confirmed by user.**
2. Exact Semantic Scholar rate limits — approximate numbers used above from third-party sources, not Semantic Scholar's own docs; confirm at implementation time.

---

## 7. Status

**Design phase: complete.** No code has been written for any of the above — implementation has not started. Awaiting explicit go-ahead and a decision on format (written function-level spec first, vs. direct edits to `tools.py` / `agents.py` / `app.py` / `pipeline.py`).
