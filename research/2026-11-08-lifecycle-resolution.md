# Lifecycle findings: resolution and validation

The earlier [verification record](2026-11-08-lifecycle-model-verification.md) identified F001, a validation/publication race, and F002, a missing verified-release transition. This record supersedes its implementation status, preserving the earlier findings as historical evidence.

## Changes

F001: activation now materializes verified snapshot blobs into a fresh read-only deployment. Atomic pointer replacement commits selection; SQLite activation records are recoverable history. An interruption before publication preserves the baseline; an interruption after publication reports the new selection and recovery finishes history exactly once. Cooperating activation callers share a release lock.

F002: an implemented path checks Ed25519-signed protected evaluation, an independent policy-bound grant and a matching monitored-trial record before verified promotion. It rejects changed core/other-flavour files, weaker criteria, stale baselines, expired or replayed grants, forged signatures and insufficient trials. Signed explicit trial failure restores the original baseline without another owner prompt. [Policy setup](../evaluation/RELEASE_POLICY.md) remains required.

## Evidence and limits

Pinned TLC 2.19 / tools v1.7.4 checked nine configurations. Safety and content-integrity configurations each explored 37,872 distinct states (213,949 generated). All expected results matched; all fourteen disposable real-code replay checks passed. Confirmation, rollback-history and false-verification negative controls were detected. Private checker logs and report were retained outside the public repository.

The package checker passed and all 81 Python tests passed, including signed trial/promotion, failure rollback, preview and host-policy setup checks.

Tests use synthetic task judgments and temporary independent signer keys. They establish release mechanics under those inputs, not reviewer honesty, useful learning, actual skill loading or protected acceptance. The finite hand-authored model is not a full implementation refinement proof. Host isolation, malicious same-account state modification and unconditional progress are outside its bound.

No production policy, signer, observer, installed-skill migration, background task or live learned release was enabled. Source/module fingerprints in [coverage](../verification/skill_lifecycle/coverage.json) bind the model review to this implementation; later source changes require another correspondence review.
