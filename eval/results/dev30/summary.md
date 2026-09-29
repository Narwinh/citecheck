# Eval summary: `dev30`

Questions: 14 completed of 30 attempted, 11 judged. By category: {'factual': 8, 'multi_hop': 5, 'recent': 1}.

## Claims by variant (independent judge)

| Variant | Claims | Supported | Partial | Unsupported | Citation precision | Removed |
|---|---|---|---|---|---|---|
| off | 41 | 100.0% | 0.0% | 0.0% | 100.0% | 0.0% |
| remove_strict | 38 | 100.0% | 0.0% | 0.0% | 100.0% | 7.3% |
| remove_lenient | 41 | 100.0% | 0.0% | 0.0% | 100.0% | 0.0% |
| revise_strict | 39 | 100.0% | 0.0% | 0.0% | 100.0% | 4.9% |
| revise_lenient | 41 | 100.0% | 0.0% | 0.0% | 100.0% | 0.0% |

## Abstention

| Variant | Correct on unanswerable | False abstentions on answerable |
|---|---|---|
| off | n/a | 0.0% |
| revise_strict | n/a | 0.0% |

## Latency and cost

End to end: p50 37.1s, p95 78.5s.

| Agent | p50 | p95 | n |
|---|---|---|---|
| planner | 8.6s | 31.6s | 13 |
| retriever | 9.2s | 18.4s | 13 |
| reviser | 15.4s | 20.8s | 6 |
| verifier | 7.8s | 21.0s | 13 |
| writer | 7.7s | 21.5s | 13 |

Mean tokens per question: 14179 (by agent: {'planner': 311, 'verifier': 5102, 'writer': 6231, 'reviser': 2535}).
Model calls: {'gemini-3.1-flash-lite': 45, 'gemini-3.6-flash': 4, 'gemini-3.8-flash': 4, 'gemini-3.7-flash': 1}.

## Agreement

- Verifier vs judge on draft claims: {'n': 41, 'exact': 0.9268, 'kappa': 0.0, 'pass_fail': 0.9268}
- Judge vs human labels: {'n': 0}
