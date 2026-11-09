---
name: verify-daphnie-lifecycle
description: Check Daphnie's prepared-package adoption, rollback and recovery state machine when changing Store release functions, benchmark eligibility or the controller CLI. Run pinned TLC checks, replay witnesses against disposable real state, and check source/model synchronization.
---

# Verify Daphnie lifecycle

Read [coverage](coverage.json) and the [verification scope](README.md). This verifies a finite control model and real-code witnesses, not task quality, OS authorization or truthful production acceptance.

## Launch and run

Use the installed Java runtime and a privately cached TLA+ tools v1.7.4 JAR from its [official release](https://github.com/tlaplus/tlaplus/releases/tag/v1.7.4). Verify its SHA-256 against the runner's pinned value. The generated skill does not download or install dependencies automatically.

From the repository root, run `python3 verification/skill_lifecycle/run.py --jar /tmp/daphnie-formal-tools/tla2tools-1.7.4.jar --output "$(mktemp -d)/lifecycle"`. The output directory must not already exist. If the private JAR cache is absent, obtain that exact official release and verify its checksum before running; do not silently switch versions. TLC uses one worker. Restricted local communication can prevent TLC startup; an execution error is not an invariant violation.

Exit 0 means no recorded finding; exit 1 means findings or mismatched witness expectations; exit 2 means a source/tool/execution error. The resolved source is expected to return 0. A clean result applies only within the documented bounds. Preserve `report.json` and each raw checker log outside the public repository.

## Read the result

Six safety invariants are checked separately from content integrity and progress reachability. A counterexample to a deliberately named `No...Reachable` invariant is a positive path witness; do not report it as a product defect. A counterexample to `NoVerifiedReleaseReachable` demonstrates the implemented signed trial and promotion path. None of these checks proves eventual progress under arbitrary scheduling.

Review every content-integrity counterexample and concrete replay. External package writes are explicitly in scope. The operator lock does not lock direct writes to package files. Prepared files are mutable. Publication builds a fresh sealed generation from snapshot blobs. The atomic pointer replacement commits the selection; database history may lag and is recovered from that selection.

## Keep model and implementation aligned

[Coverage](coverage.json) maps transitions to actual functions and pins their exact source fingerprints. There is no Git checkout in the working source, so `sync_commit` is null rather than fabricated. Move to a real commit pin when the work is committed, retaining the fingerprints.

If covered functions change, review their guards, transaction boundaries, crash points, externally writable state and returned labels before updating the pins. The runner refuses changed fingerprints. Never auto-repin to make the check run, weaken an invariant to get green, or add an imagined verified-release edge absent from the implementation.

## Negative controls and replay

The runner checks removed-confirmation, removed-rollback-history and false-verification-label model variants. [Concrete replay](replay.py) applies corresponding in-memory mutations only in disposable state, verifies detection and restores the original method. It also injects the original content race, checks sealed deployment integrity, and exercises manual adoption, rollback, postpublication history recovery and signed release gates using synthetic signers. It does not replay every reachable model state or prove formal refinement of the implementation.

Run `python3 -m unittest discover -s tests -p 'test_formal_lifecycle.py'` for the fast real-code and source-drift checks. Full TLC execution is a separate step. Product files, installed skill links and external effects are untouched by replay. Keep findings visible until a separately authorized fix is validated against both model and real code.
