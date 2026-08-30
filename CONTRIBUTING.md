# Contributing

1. Fork and create a focused branch.
2. Preserve zero runtime dependencies unless a change has a compelling security reason.
3. Add positive and negative tests for every scoring or validation change.
4. Run `PYTHONPATH=src python -m unittest discover -s tests -v`.
5. Explain any change to the correlation heuristic in the pull request because threshold semantics are security-sensitive.
