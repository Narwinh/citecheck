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
