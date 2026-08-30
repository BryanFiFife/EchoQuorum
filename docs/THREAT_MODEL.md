# Threat model

## Protects against
- Counting several agents with materially shared upstream provenance as independent votes.
- Silent omission of provenance being interpreted as evidence of independence.
- Non-deterministic quorum accounting caused by input ordering.

## Does not protect against
- Forged provenance. Authenticate lineage at collection time.
- Semantic collusion that leaves no shared provenance signal.
- A wrong but genuinely independent consensus.
- Compromise of the host running EchoQuorum.

## Design choice
The gate uses an explainable weighted provenance heuristic and graph components instead of embeddings or an LLM judge. This keeps the enforcement path offline, reproducible and auditable.
