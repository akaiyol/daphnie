# Local controller validation — 2026-11-05

## Scope

Functional local implementation of the [benchmark design](../evaluation/BENCHMARK_SYSTEM.md), operated through [controller commands](../evaluation/CONTROLLER.md). No scheduler, live learning loop, protected acceptance service or automatic verified release is enabled. Installed skill links were not changed.

## Controller checks

Validation result: package checker passed; **45 unit tests passed**. A temporary installation of the complete package linked all five skills and resolved every reference inside its prepared release; permanent installed links were untouched.

The package checker and Python unit suite cover package structure, scoped capture, portable links, explicit exclusions, content integrity, transactional failure and process-crash recovery, evidence grouping, separate candidates, frozen plans, bounded subprocesses, known improvement/no-change/regression fixtures, per-flavour results, invalid artifacts, one-shot execution, immutable reports, exact Git imports, non-activating fetches, release switching, installer conflicts and rollback.

These are controller tests using synthetic data and trusted fixture processes. They establish specific mechanics; they do not establish live task quality, realistic benchmark calibration, poison resistance or host isolation. The public starter suite contains one family per flavour and is development material only. Its SVG checks inspect structure and active/external content, not rendering, legibility or visual quality.

## Two authorized live attempts

The user authorized at most two live Codex attempts. Both were used for a no-change baseline/candidate smoke test on the same package snapshot:

- Source package revision: `30393cd4febb542d4fb1084f4c357cb72884ea2a`.
- Snapshot: `435617efd8e3bccff77c0b081918d55c5ee35abaca423d22716979db4dcb19cc`.
- CLI: `codex-cli 0.165.0-alpha.1.2`; model: `gpt-6.1-sol`; reasoning: `ultra`.
- Development task: `assistant-reconcile`; one task family; one attempt per arm; 120-second attempt limit.
- Plan: `77d05ac095584ad0bb48afd4596818de`.
- Report: `dda49e49166b403b9a8e0b910dd0973a`; scorer: `development-artifacts-1`.

| Measurement | Baseline | Candidate |
|---|---:|---:|
| Status | completed | completed |
| Deterministic artifact quality | 1.0 | 1.0 |
| Elapsed seconds | 6.57 | 5.77 |
| Input tokens | 11,762 | 13,295 |
| Cached input tokens | 2,688 | 6,144 |
| Output tokens | 647 | 1,058 |
| Package unchanged after attempt | true | true |

Observed quality change: zero. Report outcome: **inconclusive**, because one family cannot establish equivalence or improvement. Release eligibility: **blocked**. Token differences and timing from two attempts are descriptive, not efficiency evidence. No monetary cost was inferred. No further live attempts were made.

Actual skill loading, protected acceptance isolation, flavour fidelity, evaluator calibration and general privacy remain unverified. The two successful processes show that the local adapter can invoke Codex and score a narrow synthetic output. They do not validate an improving system. Private evidence remains outside this repository.

## Adoption boundary

The controller can manually adopt a complete package with an explicit full-ID confirmation and reason. That record always states `behavior_verified: false`. This is an operator action, not an automatic learning decision or independent authorization. Rollback restores a prior package and preserves observations; compatible private-memory rollback remains unimplemented.
