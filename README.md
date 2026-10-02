# CiteCheck

A multi-agent research assistant that answers questions from live web sources with a citation on each sentence, then checks every claim against the source it cites.

> Work in progress. The full README (demo, results, architecture) comes in the final stage. All numbers will come from committed eval runs.

## Run locally (backend)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
copy ..\.env.example ..\.env    # then add your GEMINI_API_KEY and TAVILY_API_KEY
pytest
python scripts/smoke.py         # one real call each to Gemini and Tavily
python scripts/retrieve.py "your question"   # numbered passages; rerun = cache hit
```
Run `python scripts/write.py "your question"` for claims with citations (Stage 3).

## Evaluation

From the repo root: `backend\.venv\Scripts\python eval\run_eval.py --run-id v1` runs the benchmark (resumable; stops cleanly when the free-tier daily quota runs out). Results go to `eval/results/<run-id>/`.

## API

From `backend/`: `uvicorn app.main:app --reload --port 8000`. Endpoints: `GET /api/health`, `GET /api/examples`, `POST /api/ask` (SSE stream of `stage`, `subqueries`, `sources`, `draft`, `verdict`, `revision`, `final`, `error` events).
