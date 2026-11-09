# Whole-lifecycle validation — 2026-11-05

## Scope and method

This test connects the implemented steps in one temporary environment using the real Daphnie package: capture → correction → scoped consolidation → candidate → paired development evaluation → blocked verified promotion → explicit test adoption → installation → rollback → recovery → fetch/import → history verification.

The repeatable [integration test](../tests/test_lifecycle.py) drives the public CLI as subprocesses. Its normal unit-test run uses deterministic fixture programs and makes no model calls. Run it with:

```sh
python3 -m unittest discover -s tests -p 'test_lifecycle.py'
```

The complete suite passed **46 tests**, and the package checker passed. A separately authorized live run uses eight Codex attempts: one baseline/candidate pair per flavour. All state, candidate edits, test installations and evidence remain outside the public tree. Actual installed user skills and schedules are untouched.

The candidate changes only the assistant library manifest and task-recovery procedure, adding explicit preservation of untouched structured fields and ordering. Core, operating contract, mode contracts and the other three libraries remain unchanged. This candidate is test material, not an adopted improvement to Daphnie.

## Implemented lifecycle checks

| Stage | Observed result |
|---|---|
| Capture | Baseline snapshot created; unchanged rescan deduplicated. |
| Correction | Synthetic correction recorded with exact project, flavour and topic. |
| Consolidation | Assistant evidence grouped without research evidence; wrong-project access rejected. |
| Candidate | Separate workspace created; cross-flavour bundle transfer rejected; only two assistant-library files changed. |
| Plan | Exact snapshots, development suite, adapter configuration and eight-attempt budget frozen. |
| Evaluation gate | Four flavour results retained separately; mandatory unknown checks block verified release; no activation follows a report. |
| Repeated execution | Running the same plan again is rejected; reading the comparison retains its original report ID. |
| Operator adoption | Wrong confirmation and rollback to a never-active release rejected. Explicit scratch adoption remains behavior-unverified. |
| Installation | Five temporary skill links follow the stable release pointer without relinking. |
| Rollback | Previously active procedure bytes restored; newer observations retained. |
| Recovery | Deleted active pointer reconstructed from committed state; external actions not replayed. |
| Update import | Local Git fetch and exact-commit import leave checkout and active release unchanged. |
| Integrity/history | Ledger verified; comparison retained; HTML export has owner-only permissions. |

Operator adoption is performed solely to exercise mechanics in scratch state. It does not override the failed eligibility gate for any real deployment. The integration test does not execute another model task after switching installed links; it verifies link targets and actual procedure bytes.

## Live results

All **8/8 authorized live attempts completed**, passed their deterministic artifact checks and left their frozen packages unchanged. The subsequent adoption, installation, rollback, recovery, fetch/import and integrity checks also completed in the same scratch environment. No additional model attempts were made.

| Flavour | Baseline quality | Candidate quality | Baseline seconds | Candidate seconds | Decision |
|---|---:|---:|---:|---:|---|
| assistant | 1.0 | 1.0 | 15.2 | 16.87 | Inconclusive |
| research | 1.0 | 1.0 | 17.93 | 22.63 | Inconclusive |
| think | 1.0 | 1.0 | 21.21 | 16.55 | Inconclusive |
| design | 1.0 | 1.0 | 66.47 | 69.92 | Inconclusive |

Quality change was zero for every flavour. Each had only one independent family, so the result is **inconclusive**, not demonstrated equivalence or improvement. Timing is descriptive; eight attempts do not establish an efficiency result. Design scoring checked SVG structure and required text; rendered quality and human acceptance were not established.

- Model: `gpt-6.1-sol`; reasoning: `ultra`.
- Host: `codex-cli 0.165.0-alpha.1.2`; scorer: `development-artifacts-2`.
- Plan: `cb67e7fb7e4f4c6da151eb69eb5a7148`; report: `162c73971dbf432ead45bfad224c0f9f`.
- Baseline snapshot: `271c2245860636d0828b06adfba32082b91a9564fdb6070bf2da3a4b0743bb89`.
- Candidate snapshot: `47a3da1b39e0faece93d48effe651223370ab026b84903ae3e8c9ec44a444379`.
- Suite digest: `70edba19b430319da713208793d93233d83b76a13eb9ff01f3b19152a7f04698`.
- Ledger: consistent, 36 events at completion.

Release eligibility remained **blocked**. The manual scratch adoption records explicitly state behavior-unverified. Production skill links, public library contents and background schedules were not changed. Private output files and attempt evidence are retained outside the repository; temporary evidence requires an explicit private archival destination for long-term retention.

## Remaining target-lifecycle gaps

The implemented operational loop can be exercised end to end. The complete verified-learning architecture cannot yet be validated end to end because these components are absent or unresolved:

- Protected acceptance tasks and independently calibrated evaluators.
- Verified actual skill loading and behavioural router selection.
- Personality/flavour fidelity, bounded handoff and fresh-context enforcement.
- Host-denied cross-project access and adverse-memory/poisoning resistance.
- Independently authenticated learned-release authority and monitored production trials.
- Compatible private-memory rollback, correction/deletion propagation and retention enforcement.

Passing this lifecycle drill does not establish autonomous learning or improvement. Synthetic scope filtering is distinct from enforced model/tool isolation. A continuous chat cannot demonstrate erasure of prior context.
