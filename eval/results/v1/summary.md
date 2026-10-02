# Eval summary: `v1`

Questions: 37 completed of 37 attempted, 36 judged. By category: {'factual': 17, 'multi_hop': 8, 'recent': 7, 'unanswerable': 5}.

## Claims by variant (independent judge)

| Variant | Claims | Supported | Partial | Unsupported | Citation precision | Removed |
|---|---|---|---|---|---|---|
| off | 141 | 99.3% | 0.0% | 0.7% | 99.7% | 0.0% |
| remove_strict | 128 | 100.0% | 0.0% | 0.0% | 100.0% | 9.2% |
| remove_lenient | 141 | 99.3% | 0.0% | 0.7% | 99.7% | 0.0% |
| revise_strict | 137 | 100.0% | 0.0% | 0.0% | 100.0% | 2.8% |
| revise_lenient | 141 | 99.3% | 0.0% | 0.7% | 99.7% | 0.0% |

## Abstention

| Variant | Correct on unanswerable | False abstentions on answerable |
|---|---|---|
| off | 80.0% | 0.0% |
| revise_strict | 80.0% | 0.0% |

## Latency and cost

End to end: p50 38.2s, p95 109.5s.

| Agent | p50 | p95 | n |
|---|---|---|---|
| planner | 7.7s | 27.4s | 36 |
| retriever | 9.0s | 47.7s | 36 |
| reviser | 14.8s | 35.7s | 11 |
| verifier | 9.2s | 29.1s | 32 |
| writer | 7.9s | 21.3s | 36 |

Mean tokens per question: 12770 (by agent: {'planner': 295, 'verifier': 4501, 'writer': 6258, 'reviser': 1716}).
Model calls: {'gemini-3.1-flash-lite': 80, 'gemini-3.6-flash': 21, 'gemini-3.8-flash': 20, 'gemini-3.7-flash': 8}.

## Agreement

- Verifier vs judge on draft claims: {'n': 141, 'exact': 0.9078, 'kappa': 0.0653, 'pass_fail': 0.9149}
- Judge vs human labels: {'n': 1, 'exact': 1.0, 'kappa': 1.0, 'pass_fail': 1.0}
