# Security policy

Please report security issues privately through GitHub Security Advisories when available. Do not include live credentials or sensitive agent traces.

EchoQuorum is a deterministic provenance-analysis gate. It does **not** prove semantic independence, model honesty, or correctness of evidence. Treat lineage fields as authenticated by your surrounding system; if agents can forge their own provenance, the result is advisory only. Missing provenance is handled conservatively rather than counted as independence.
