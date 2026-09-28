# Eval summary: `dev30`

Questions: 2 completed of 2 attempted, 2 judged. By category: {'factual': 2}.

## Claims by variant (independent judge)

| Variant | Claims | Supported | Partial | Unsupported | Citation precision | Removed |
|---|---|---|---|---|---|---|
| off | 6 | 100.0% | 0.0% | 0.0% | 100.0% | 0.0% |
| remove_strict | 6 | 100.0% | 0.0% | 0.0% | 100.0% | 0.0% |
| remove_lenient | 6 | 100.0% | 0.0% | 0.0% | 100.0% | 0.0% |
| revise_strict | 6 | 100.0% | 0.0% | 0.0% | 100.0% | 0.0% |
| revise_lenient | 6 | 100.0% | 0.0% | 0.0% | 100.0% | 0.0% |

## Abstention

| Variant | Correct on unanswerable | False abstentions on answerable |
|---|---|---|
| off | n/a | 0.0% |
| revise_strict | n/a | 0.0% |

## Latency and cost

End to end: p50 28.5s, p95 31.7s.

| Agent | p50 | p95 | n |
|---|---|---|---|
| planner | 8.9s | 12.5s | 2 |
| retriever | 5.3s | 5.4s | 2 |
| verifier | 6.7s | 6.8s | 2 |
| writer | 7.5s | 8.0s | 2 |

Mean tokens per question: 8668 (by agent: {'planner': 328, 'verifier': 2854, 'writer': 5486}).
Model calls: {'gemini-3.1-flash-lite': 6}.

## Agreement

- Verifier vs judge on draft claims: {'n': 6, 'exact': 1.0, 'kappa': 1.0, 'pass_fail': 1.0}
- Judge vs human labels: {'n': 0}
