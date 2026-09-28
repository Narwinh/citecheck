You are an annotator for a research-quality study. You will label whether sentences produced by an AI system are backed by the sources they cite. Your labels are used to measure the system, so be careful and consistent.

For each item you get a sentence and the IDs of the source passages it cites. The passages are listed at the end.

Step 1. For EACH cited passage separately, decide `supports`: true if that passage by itself states at least part of what the sentence claims, false if it says nothing relevant to the sentence or contradicts it.

Step 2. Give the sentence an overall `label` using all of its cited passages together:
- SUPPORTED: everything the sentence asserts (names, numbers, dates, relationships, and strength words like "always", "only", "first") can be found in the cited passages.
- PARTIAL: the main point is in the cited passages, but at least one detail is missing, or the sentence states it more strongly or broadly than the passages do.
- UNSUPPORTED: the main point is not in the cited passages, or the passages contradict it.

Guidelines:
- Use only the passage text. Do not use your own knowledge. A sentence that is true in the real world but absent from its passages is UNSUPPORTED.
- Paraphrase is fine. Reasonable, direct inferences are fine; speculative leaps are not.
- Judge every item independently.

Return one judgment per item key, with one `supports` entry per cited passage.

Items:
$items

Passages:
$passages
