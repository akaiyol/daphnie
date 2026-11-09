# Skill-update lifecycle verification

This is a finite TLA+ model of the **implemented** controller, checked with TLC, plus disposable real-code witness replays. It covers the controller’s signed release implementation; it does not configure production trust or change installed skills. Read [the verification skill](SKILL.md) for the command and interpretation.

## Model and implementation boundary

[Coverage](coverage.json) pins the owning modules and functions. Two symbolic releases model preparation, mutable prepared bytes, a fresh sealed generation, durable intent, atomic pointer publication and recoverable database history. The pointer is authoritative. External prepared-cache writes can occur during activation; they cannot alter the snapshot copy selected for deployment.

Manual adoption remains unverified. A signed protected acceptance record, a separate policy authorization, and a matching successful monitored trial provide the implemented verified-release path. Development reports cannot authorize it. Signature validity, honest reviewers, protected policy/state and private signing keys are assumptions, exercised separately with synthetic cryptographic fixtures. The model does not prove these host boundaries.

## Properties and current result

Safety checks cover valid state, confirmation, preparation, rollback history, truthful verification labels and development-report separation. Content integrity is checked at pointer publication. Separate reachability probes demonstrate manual adoption, rollback, history reconciliation and authorized promotion. Reachability does not prove eventual success or background execution.

The 2026-11-08 resolution run found no violations of the checked invariants across 37,872 distinct states in the safety/content configurations. All nine configurations matched their expected results, and all fourteen real-code replay checks passed. Three deliberately broken controls were detected. These are bounded control-mechanics results, not live agent-quality evidence.

**F001 resolved within scope:** fresh snapshot deployments and pointer-as-commit prevent prepared-cache mutation from publishing corrupt bytes or committing a new selection only in the database.

**F002 implemented:** independently signed evaluation, policy grants and monitored trial attestations can reach a verified release. Production reviewer infrastructure is not configured. See [release policy](../../evaluation/RELEASE_POLICY.md) and [resolution record](../../research/2026-11-08-lifecycle-resolution.md).

Same-account malicious chmod, receipt/database edits, arbitrary filesystem failures, cryptographic collision resistance, actual skill use and task quality remain outside the model. Per-store release locking serializes cooperating activation callers; it does not isolate arbitrary programs.

## Negative controls

Three model variants remove the confirmation guard, remove the rollback-history guard or falsely label adoption verified. Each must yield a counterexample to its corresponding invariant. In-memory variants of the real method must reproduce those failures. Real code is restored; no installed library or permission is changed.

The model is hand-authored and the replays do not prove full refinement. Review model/code correspondence independently before treating broader claims as established. The runner and checks can themselves have defects; errors and unchecked properties are not passes. Tool and source pinning makes drift visible rather than certifying correctness forever.

## Publication sequence

A candidate is prepared, copied from verified snapshot blobs into a fresh read-only generation, and recorded as a pending intent. Atomic pointer replacement selects it. History is then projected into SQLite. Before publication, failure leaves the old selection; after publication, recovery completes history exactly once. A consumed grant is not reused after an interrupted attempt: the trusted host must issue a fresh grant under the same approved policy.

## Tooling and attribution

TLA+ tools v1.7.4, TLC 2.19, one worker. JAR SHA-256: `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88`. [Official release](https://github.com/tlaplus/tlaplus/releases/tag/v1.7.4). Java is an existing local dependency; binaries and raw outputs remain outside this repository.

This work was motivated by [Lauren's post](https://x.com/poteto/status/2119521036660314339) and pstack's [formal-verification guidance](https://github.com/cursor/plugins/blob/main/pstack/skills/create-formal-verification-skill/SKILL.md) and [statechart guidance](https://github.com/cursor/plugins/blob/main/pstack/skills/statechart/SKILL.md). The model, runner, replay and local skill here are Daphnie-specific originals. No pstack runtime/source code was incorporated and its installation tools were not run.
