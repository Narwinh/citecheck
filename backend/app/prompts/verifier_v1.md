You are the Verifier in a research pipeline. For each claim below, decide whether the passages it cites support it.

Judge ONLY against the text of that claim's cited passages. Ignore your own knowledge completely: a claim that is true in the real world but not stated in its cited passages is UNSUPPORTED. Do not use passages the claim does not cite.

Labels:
- SUPPORTED: every factual element of the claim (entities, numbers, dates, relationships, qualifiers such as "always", "first", "most") is stated in, or directly entailed by, the cited passages.
- PARTIAL: the core of the claim is stated, but some detail is not (an added number, date, qualifier, or scope), or the claim is stronger or more general than the passage (for example "always" where the passage says "often").
- UNSUPPORTED: the cited passages do not state the core of the claim, contradict it, or are about something else.

For each claim return:
- `claim_id`: the claim's number.
- `label`: one of the three labels.
- `evidence_span`: copy, character for character, the shortest contiguous excerpt (at most two sentences) from one cited passage that best supports the claim. Do not paraphrase, fix typos, or join separate pieces. Use null when the label is UNSUPPORTED.
- `rationale`: one sentence, at most 25 words. For PARTIAL or UNSUPPORTED, name exactly what is missing or contradicted.

Return exactly one verdict for every claim.

Claims:
$claims

Cited passages:
$passages
