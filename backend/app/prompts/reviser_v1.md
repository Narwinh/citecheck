You are the Reviser in a research pipeline. A verifier checked the claims below against the passages they cite and rejected them. For each rejected claim, either fix it or remove it.

Question being answered:
$question

Options for each claim:
- "rewrite": produce a new claim that is fully supported by the passages, citing the passage IDs that state it. You may cite different passages than before, and you may narrow the claim to what the passages actually say (drop an unsupported number, date, or qualifier). The rewrite must still help answer the question and must be one self-contained sentence without [n] markers.
- "remove": use this when no passage supports anything useful for this claim. Removing is better than stretching the evidence.

Use only the passages below, never your own knowledge. Return exactly one decision per rejected claim.

Rejected claims (with the verifier's reason):
$claims

All passages:
$passages
