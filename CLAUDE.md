# CiteCheck — Project Handoff for Claude Code

> Put this file in the repo root as `CLAUDE.md`. Read it fully before doing anything, and re-read the relevant section at the start of every stage.

---

## 0. Who I am and how to work with me

- I'm Naveen, a 2026 CS graduate (VIT Chennai) positioning myself as an **AI Engineer**. I'm also targeting **AI evaluation** roles and remote work through talent marketplaces (Turing, Toptal, etc.).
- This project replaces an older BERT sentiment-analysis project (EmotiScan) on my resume. It must be something I can **explain confidently in interviews**.
- My strongest existing project is **NS-Fact**, a neuro-symbolic medical claim verifier (LangChain + Gemini 2.5 Flash + Neo4j/Hetionet, 100% precision / 99% recall on a 200-query benchmark in strict mode). CiteCheck should read as the natural sequel: **"I build LLM systems that verify their own output, and I measure it."**
- I'm doing a Professional Certificate in Agentic AI & Multi-Agent Systems (Simplilearn × IIT Patna). CiteCheck is where that coursework shows up in real work.

### Working agreement (follow strictly)
1. **Build in stages** (Section 9). Do not start the next stage until the current stage's acceptance criteria pass.
2. **After each stage, stop and explain** what you built: the key design decisions, the tradeoffs, and what I should change myself to learn it. Then suggest one small modification for me to make by hand.
3. **Never fabricate metrics.** Every number in the README, UI, or resume must come from an actual run of the eval harness, and the results file must be committed.
4. **Ask before adding dependencies** that aren't listed in Section 4.
5. **Verify current APIs.** Model names, package versions, and free-tier limits change. Check the current docs for Gemini, Tavily, LangGraph, and ChromaDB before writing integration code. Don't rely on memory.
6. **Commit at the end of each stage** with a clear message. Keep `main` runnable.
7. **Secrets:** never commit API keys. Use `.env` locally, `.env.example` in the repo, and platform secrets in deployment.

---

## 1. What we're building

**Name:** CiteCheck
**One-liner:** A multi-agent research assistant that answers questions from live web sources with a citation on each sentence, then **verifies every claim against its cited source** and measures how much that verification reduces hallucinated citations.

**The problem:** Perplexity-style answer engines cite sources, but nothing checks whether the cited source actually says what the sentence claims. Citations look trustworthy even when they're wrong.

**What makes it different (lead with this everywhere):**
1. A dedicated **verifier agent** that checks each claim against its cited passage.
2. An **evaluation harness** with a benchmark and before/after numbers (verifier off vs on).
3. A UI that **shows the verification visually** instead of hiding it.

**Framing:** Never call it a "Perplexity clone." It is a *verification-focused research assistant*.

### Inspiration and credit
- The core idea (query → web search → extract page text → prompt → streamed, cited answer) is inspired by [elvinagam/perplexity-ai-clone](https://github.com/elvinagam/perplexity-ai-clone), itself a fork of the open-source **clarity-ai** project (Next.js + TypeScript + OpenAI).
- **No code is copied.** Different language and architecture. If we adapt its citation-prompt pattern (numbered sources, cite as [1], [2]), check the original license and credit it in the README "Acknowledgements" section.

---

## 2. Architecture

```
                       ┌──────────────────────────────────────────────┐
  User question ──────▶│ 1. PLANNER                                   │
                       │ splits the question into 2–4 sub-queries     │
                       └───────────────┬──────────────────────────────┘
                                       ▼
                       ┌──────────────────────────────────────────────┐
                       │ 2. RETRIEVER                                 │
                       │ Tavily search per sub-query → page text →    │
                       │ chunk → embed → ChromaDB (in-memory) →       │
                       │ top-k passages, deduplicated, numbered [1..n]│
                       └───────────────┬──────────────────────────────┘
                                       ▼
                       ┌──────────────────────────────────────────────┐
                       │ 3. WRITER                                    │
                       │ drafts answer as a list of sentences, each   │
                       │ with citation IDs pointing at passages       │
                       └───────────────┬──────────────────────────────┘
                                       ▼
                       ┌──────────────────────────────────────────────┐
                       │ 4. VERIFIER                                  │
                       │ per sentence: SUPPORTED / PARTIAL /          │
                       │ UNSUPPORTED + evidence span from the passage │
                       │ unsupported → revise once using other        │
                       │ passages, else remove and flag               │
                       └───────────────┬──────────────────────────────┘
                                       ▼
                        Final answer + per-claim verdicts + sources
                        (streamed to the UI as events)
```

Orchestrated with **LangGraph** as a state graph. The verifier → writer revision loop runs **at most once** to control latency and cost.

### Shared graph state (Pydantic / TypedDict)
```python
class Passage:        id: int; url: str; title: str; text: str; score: float
class Claim:          id: int; text: str; citation_ids: list[int]
class Verdict:        claim_id: int; label: Literal["SUPPORTED","PARTIAL","UNSUPPORTED"]
                      evidence_span: str | None; rationale: str
class ResearchState:
    question: str
    mode: Literal["strict","lenient"]   # strict: PARTIAL counts as unsupported
    sub_queries: list[str]
    passages: list[Passage]
    draft_claims: list[Claim]           # writer output, before verification
    verdicts: list[Verdict]
    final_claims: list[Claim]           # after revision/removal
    revision_count: int
    timings_ms: dict[str, int]          # per-agent latency
    token_usage: dict[str, int]
```

### Agent specs
All LLM calls use **structured output** (Pydantic schemas). No regex parsing of free text.

| Agent | Input | Output | Notes |
|---|---|---|---|
| Planner | question | 2–4 sub-queries | Keep simple questions to 1–2 sub-queries |
| Retriever | sub-queries | ranked, deduplicated passages with stable IDs | Chunk ~500–800 tokens with overlap; top-k ≈ 8–12 total; dedupe by URL + similarity. No LLM call. |
| Writer | question + passages | list of claims, each with ≥1 citation ID | Every sentence must cite. It may only use the given passages. It says so when the passages don't answer the question. |
| Verifier | each claim + the passages it cites | verdict + evidence span + rationale | Judges **only** against the cited passage text, never the model's own knowledge. Batch claims per call where possible. |
| Reviser (writer, 2nd pass) | unsupported claims + all passages | rewritten claims with new citations, or removal | One pass max. Re-verify the revised claims. |

**Modes:** `strict` (PARTIAL = fail, like NS-Fact's strict mode) and `lenient` (PARTIAL = pass). Default: strict.

---

## 3. Evaluation harness (the most important part for the resume)

### Benchmark
- `eval/benchmark.jsonl`, target **~100 questions**. Start with 30 for development.
- Mix of: factual lookups, multi-hop questions, recent-events questions (need current web data), and a few **unanswerable or trick questions** (to test that the system admits when it doesn't know).
- Sources: write some by hand, and optionally adapt questions from existing open QA datasets (**check each dataset's license**, and prefer ones needing current web facts).
- Fields: `id, question, category, notes`.

### Metrics
| Metric | Definition |
|---|---|
| Claim support rate | % of final claims labeled SUPPORTED |
| Unsupported-claim rate | % of claims UNSUPPORTED, **reported before verifier vs after** |
| Citation precision | % of citations whose passage actually supports the claim |
| Removal rate | % of draft claims removed by the verifier |
| Abstention correctness | on unanswerable questions, % where the system correctly says it can't answer |
| Latency | p50 / p95 end-to-end, plus per agent |
| Tokens / cost | per question |

### Judging (make it credible)
- Use a **separate LLM-as-judge prompt** (not the verifier's own prompt) to label a claim–passage pair.
- **Hand-label a sample of 25–30 claims myself** and report judge-vs-human agreement. This is what makes the numbers defensible in an interview.
- **Ablations:** (a) verifier off vs on, (b) strict vs lenient, (c) optional: top-k 5 vs 10.

### Reproducibility and rate limits
- **Cache Tavily responses and page text** to disk (`eval/cache/`), keyed by query, so reruns are cheap, reproducible, and don't hit free-tier limits.
- Run the benchmark in small batches with backoff/retry on 429 errors.
- Save outputs to `eval/results/<timestamp>/` with `results.json`, `summary.md` (a markdown table), and a copy of the config used.
- The frontend's **Evaluation page reads a committed `summary.json`**. No hard-coded numbers anywhere.

---

## 4. Tech stack (decided)

**Backend (Python 3.11+)**
- **LangGraph** for orchestration
- **Gemini** (the Flash model tier; verify the current model name in the docs) via the official LangChain Google integration. It has a free tier, and I've used Gemini 2.5 Flash before in NS-Fact.
- **Tavily** for search. It returns clean page content, so we don't need a scraper. Fallback: DuckDuckGo search + page fetch + readability extraction, only if Tavily limits become a problem.
- **ChromaDB**, in-memory ephemeral collection per request. No separate database server needed.
- **Embeddings:** Gemini embedding API (keeps the container small). Verify the current embedding model name.
- **FastAPI** + **Server-Sent Events (SSE)** for streaming
- **Pydantic v2**, **pytest**, **ruff**
- Rate limiting: `slowapi` (or a simple in-memory limiter)

**Frontend**
- **Next.js (App Router) + TypeScript**
- **Tailwind CSS**
- **shadcn/ui** as *unstyled primitives only*. Restyle heavily; it must not look like a default shadcn template.
- **Framer Motion** for motion
- **Recharts** (or visx) for the evaluation charts
- **lucide-react** icons

> Note: an earlier plan used Streamlit and dropped FastAPI. That changed because a **professional, distinctive frontend is a hard requirement**, and Streamlit can't deliver it. Plan B, only if the timeline slips badly: ship with Streamlit + heavy custom CSS first, then migrate.

**Deployment**
- **Backend:** Hugging Face Spaces (Docker SDK). Docker avoids the old-SQLite problem ChromaDB hits on Streamlit Community Cloud. Alternative: Render free tier.
- **Frontend:** Vercel (free Hobby tier).
- Configure CORS to allow only the frontend domain.
- Free backends **sleep when idle**, so the UI needs a "warming up the research engine…" state that polls `/api/health`.
- Record a **demo GIF/video** for the README, in case the live backend is asleep when a recruiter clicks.

**Cost protection for the public demo**
- Per-IP limit (e.g. 5 questions/hour) on my keys.
- An optional **"use your own Gemini key"** field in the UI, sent as a header, never stored or logged.
- Cap question length and the number of sub-queries.

---

## 5. Backend API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | liveness and warm-up check |
| POST | `/api/ask` | body `{question, mode}` → **SSE stream** |
| GET | `/api/examples` | curated example questions for the landing page |

### SSE event types (the frontend is built around these)
```
stage        {agent: "planner"|"retriever"|"writer"|"verifier"|"reviser", status: "start"|"done", ms}
subqueries   {items: [...]}
sources      {passages: [{id, url, title, domain, favicon, snippet}]}
draft        {claims: [{id, text, citation_ids}]}
verdict      {claim_id, label, evidence_span, rationale}      # one event per claim
revision     {claim_id, action: "rewritten"|"removed", new_text?, new_citation_ids?}
final        {claims, stats: {supported, partial, unsupported, removed, total_ms, tokens}}
error        {message}
```

---

## 6. Frontend: this must look professional and distinctive

My previous Claude Code projects had **underwhelming, generic frontends**. This one must look like a real product and be interesting to watch. Treat the design as a first-class deliverable, not a wrapper.

### Design concept: "Evidence Room"
An investigative, editorial feel, like a well-designed research journal crossed with a fact-checking desk. Calm, precise, trustworthy, with **verification as the visual centerpiece**.

**Avoid:** purple/blue AI gradients, glowing orbs, generic chat bubbles, default shadcn look, emoji, centered-everything layouts, and "Powered by AI ✨" clichés.

### Visual system
- **Typography:** a characterful **serif for the answer body and headings** (e.g. Newsreader, Source Serif 4, or Fraunces) paired with a clean **monospace for metadata** (e.g. JetBrains Mono or IBM Plex Mono): agent names, timings, citation IDs, and stats. Use a sans only for small UI controls. Load via `next/font`.
- **Color:** a restrained, near-monochrome base (warm off-white paper in light mode, deep ink/charcoal in dark mode) with **exactly three semantic accent colors used only for verification states**:
  - Supported: a muted green
  - Partial: an amber/ochre
  - Unsupported / removed: a muted red
  - Plus one quiet accent for links and focus.
- Define everything as CSS variables / Tailwind theme tokens. **Light and dark mode are both required** and must be equally polished.
- Subtle texture is optional (a very faint paper grain), fine hairline rules, generous whitespace, and an editorial grid.

### Key screens and components
1. **Landing / ask page**
   - Strong headline (e.g. "Answers you can check."), a one-line explanation, and a large, well-designed question input.
   - 4–6 curated example questions as clickable cards.
   - A small "How it works" strip showing the 4 agents.
   - Mode toggle: Strict / Lenient.

2. **Live research view (the showpiece)**
   - **Agent pipeline timeline:** planner → retriever → writer → verifier shown as a horizontal (desktop) or vertical (mobile) track. Each node animates through idle → running → done with live millisecond timings in monospace. Sub-queries appear under the planner as they arrive.
   - **Answer panel:** the answer renders sentence by sentence. Each sentence carries **citation chips** ([1], [2]). When verdicts arrive, each sentence gets a verification state:
     - Supported: a subtle green underline and a check on its chip
     - Partial: an amber dotted underline
     - Unsupported: red, with the text struck through, then it animates to its revised version or collapses to a "removed" marker
   - **Evidence on hover/click:** hovering a sentence or chip highlights the source card and shows the **exact evidence span** from the passage, highlighted inside its surrounding text, plus the verifier's short rationale.
   - **Sources rail:** cards with favicon, domain, title, and snippet. The cited ones are marked, and the card lights up when its claim is hovered.
   - **Verification summary bar:** e.g. "9 claims · 7 supported · 1 revised · 1 removed · 14.2s", in monospace with small proportion bars.
   - Loading states are **skeletons plus the timeline**, never a bare spinner. Streaming progress makes a 15–40s wait feel like a feature.

3. **Evaluation page (`/eval`)**. This sells the project to technical reviewers.
   - Headline numbers as clean stat tiles (from `summary.json`).
   - A **before vs after verifier** chart (unsupported-claim rate), a strict vs lenient comparison, and a latency distribution.
   - A judge-vs-human agreement figure.
   - A browsable table of benchmark questions with per-question results.
   - Short methodology notes and limitations in prose.

4. **About / How it works (`/about`)**: an architecture diagram (a clean SVG, not a screenshot), the design decisions, and links to the GitHub repo, NS-Fact, and my portfolio (narwinh.github.io).

### Motion and polish
- Framer Motion, **subtle and purposeful**: staggered sentence reveals, smooth verdict-state transitions, layout animation when a claim is removed. Respect `prefers-reduced-motion`.
- Fully responsive (test at 375px, 768px, and 1440px). No horizontal scroll.
- Accessibility: keyboard-navigable citations, visible focus states, and verification states that **never rely on color alone** (use icons and labels too). WCAG AA contrast.
- A shareable result URL (encode the question) and a "copy answer with citations" button.
- Good empty, error, rate-limited, and backend-sleeping states, each designed rather than left as default text.
- Favicon, OpenGraph image, and page titles.

### Design process
- Before building screens, create a small **design tokens file + a component sandbox page** (`/dev/components`) showing typography, colors, chips, verdict states, and cards in both themes. Show me screenshots and get approval, then build the pages.
- Run a mock SSE event stream (`/dev/mock`) so the UI can be built and polished **without calling the APIs**.

---

## 7. Repo structure

```
citecheck/
├── CLAUDE.md
├── README.md
├── .env.example
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app, CORS, rate limit, routes
│   │   ├── sse.py               # event formatting
│   │   ├── graph.py             # LangGraph wiring
│   │   ├── state.py             # Pydantic models
│   │   ├── config.py            # settings from env
│   │   ├── agents/
│   │   │   ├── planner.py
│   │   │   ├── retriever.py
│   │   │   ├── writer.py
│   │   │   └── verifier.py
│   │   ├── prompts/             # prompt templates as files, versioned
│   │   └── services/
│   │       ├── search.py        # Tavily client + disk cache
│   │       ├── embeddings.py
│   │       └── vectorstore.py   # Chroma
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
├── eval/
│   ├── benchmark.jsonl
│   ├── human_labels.jsonl
│   ├── run_eval.py
│   ├── judge.py
│   ├── metrics.py
│   ├── cache/                   # gitignored
│   └── results/                 # committed summaries
├── frontend/
│   ├── app/                     # /, /eval, /about, /dev/*
│   ├── components/
│   ├── lib/                     # SSE client, types mirroring backend events
│   └── styles/
└── docs/
    └── architecture.svg
```

---

## 8. Scope

**Must-have (v1, which goes on the resume as complete):**
- The four agents plus a single revision pass, strict/lenient modes
- A citation on each sentence, the verifier with evidence spans
- The eval harness: ~100 questions, ablations, a human-agreement sample, committed results
- FastAPI + SSE backend, the Next.js frontend with all 4 pages, both themes
- Deployed backend + frontend, a live link, a demo GIF
- README (Section 10)

**Nice-to-have (later, as separate commits):**
- Comparing two LLMs on the same benchmark
- Persistent cache across sessions for repeated questions
- Export answer as Markdown/PDF
- Conversation follow-ups

**Out of scope:** user accounts, databases, payments, and multi-user persistence.

---

## 9. Build stages (with acceptance criteria)

Estimated total: **~3–4 weeks at 2–3 hrs/day** (the proper frontend adds about a week over the original Streamlit estimate).

| # | Stage | Acceptance criteria |
|---|---|---|
| 1 | **Setup** — repo, pyproject, `.env.example`, keys working, ruff, pytest | `pytest` passes; a smoke script calls Gemini and Tavily once |
| 2 | **Retriever** — Tavily + cache, chunking, embeddings, Chroma ranking | CLI: question → printed numbered passages with URLs; cache hit on rerun |
| 3 | **Writer** — structured claims with citations | CLI prints claims; every claim has ≥1 valid citation ID; unit test enforces it |
| 4 | **Verifier + revision** | CLI prints a verdict per claim with an evidence span; a hand-made test case with a deliberately wrong citation gets flagged |
| 5 | **LangGraph wiring + planner** | End-to-end CLI run; per-agent timings recorded |
| 6 | **Eval harness v1** (30 questions) | `python eval/run_eval.py` produces results + summary; verifier off/on ablation works |
| 7 | **FastAPI + SSE** | `curl` streams all event types in order; rate limit returns 429 |
| 8 | **Frontend foundation** — tokens, fonts, themes, `/dev/components`, mock SSE | Screenshots of both themes approved by me |
| 9 | **Live research view** | Full flow against the mock stream, then the real backend; hover evidence works |
| 10 | **Landing, Eval page, About page** | All pages responsive at 375/768/1440; Lighthouse accessibility ≥ 90 |
| 11 | **Eval to ~100 questions + human labels** | Final `summary.json` committed; the Eval page shows real numbers |
| 12 | **Deploy + README + demo GIF** | Live URLs work from a fresh browser; the README is complete |

After every stage: explain it, suggest one hands-on change for me, and commit.

---

## 10. README requirements

1. Title, one-line pitch, **live demo link**, demo GIF at the top
2. The problem (plausible-looking but wrong citations)
3. Architecture diagram + a short explanation of each agent
4. **Results table** from the committed eval run (before/after verifier, strict vs lenient, human agreement, latency)
5. How to run locally (backend, frontend, eval)
6. Design decisions and tradeoffs (why one revision pass, why in-memory Chroma, why strict mode by default, why SSE)
7. **Limitations and what I learned** (honest; this shows maturity)
8. Acknowledgements (clarity-ai / perplexity-ai-clone inspiration, with the license noted if anything was adapted)
9. Link to NS-Fact and to my portfolio

---

## 11. Resume entries (for reference; don't edit my resume files)

**While in progress (use now):**
> **CiteCheck: Multi-Agent Research Assistant with Citation Verification** *(In Progress)*
> *Python, LangGraph, Gemini, ChromaDB, Tavily, FastAPI, Next.js*
> - Building a 4-agent pipeline (planner, retriever, writer, verifier) that answers questions with a citation on each sentence from live web sources
> - Designing a verification agent that checks each generated claim against its cited source to reduce hallucinated citations
> - Developing an evaluation harness to measure citation precision and faithfulness on a custom benchmark

**When complete (fill the brackets only with real, committed numbers):**
> - Built a 4-agent LangGraph pipeline that answers questions with a citation on each sentence from live web sources, streamed to a Next.js interface
> - Designed a claim-verification agent that cut unsupported claims from [X]% to [Y]% on a [N]-question benchmark ([Z]% agreement with human labels)
> - Deployed on Hugging Face Spaces + Vercel with a live demo and a public evaluation dashboard

---

## 12. Interview readiness (help me with this as we go)
I must be able to explain:
- How the verifier decides SUPPORTED vs PARTIAL vs UNSUPPORTED, and its failure modes
- Why chunk size and top-k were chosen, and what changed when I varied them
- What happens when sources contradict each other
- Why LLM-as-judge needs a human-agreement check
- Latency and cost tradeoffs of the revision loop
- How SSE streaming works end to end

At the end of the project, write `docs/INTERVIEW_NOTES.md` with likely questions and answers based on what we actually built and measured.
