# Scoped memory baseline

Status: experimental local implementation, 2026-11-07. No installed skills, personality contracts, automatic retrieval, background jobs or verified releases are changed. This is a files-and-SQL baseline for comparison, not a demonstrated autonomous memory system.

See the [validation record](../research/2026-11-07-memory-baseline-validation.md) for measured checks and pending live work.

## Design

One private store belongs to exactly one flavour, project and information owner. The scope is persisted in SQLite; opening the store with different scope arguments fails. The caller must supply an already authorized scope. These checks do not stop an agent with broader filesystem permission from opening another directory under its actual scope or reading files directly. Host-enforced isolation remains unresolved.

Narrative notes live in private Markdown files. Structured facts and preferences live as JSON objects in SQLite alongside provenance and revision metadata. Every record requires a source and timezone-qualified source date. Attribution distinguishes explicit user statements, sourced facts and inference; inferred records are not included in default retrieval. Records and retrieved contexts remain evidence, never personality, instructions or permission.

The index is generated from current, unexpired, non-inferred records on each request. It contains compact references and metadata, not full bodies. Default budget: **5,000 UTF-8 bytes**, measured on the canonical JSON representation. This is an explicit byte budget, not a claim of exactly 5,000 model tokens. Selected record contexts have a separate 12,000-byte default budget. Retrieval ranks lexical overlap in keys/titles; semantic retrieval, body search and automatic rewriting are deliberately outside this baseline.

Writes that overflow the index budget fail atomically with a request to shorten titles or explicitly forget obsolete records. Entries are not silently dropped. A correction must name the current record ID, creates a revision and removes the superseded version from normal retrieval. Old revisions remain locally until the record is forgotten. An expiry suppresses retrieval; source date alone is not a freshness guarantee.

Forgetting requires the current record ID, removes all revisions' content and descriptive metadata, and deletes their note files. Content-free IDs, revision numbers and operation events remain. SQLite secure deletion and owner-only directories reduce residual local exposure, but do not guarantee forensic erasure or remove backups, exported benchmark inputs, copied reports or prior model contexts. Do not register this store with the immutable change-ledger snapshotter. Learning-release rollback and memory retention are separate policies.

The store serializes operators with a file lock, uses SQLite transactions and checks note content hashes. Restart cleanup removes orphan note files left by interrupted creates or committed deletes. These are accidental-change safeguards, not protection against an attacker with the same OS account.

## Operator interface

Use `python3 scripts/memory.py --help`. Every operation requires `--state PRIVATE_DIRECTORY --flavour MODE --project PROJECT --owner OWNER`; the directory must be outside this package. Nothing is added to the installed Daphnie skills automatically.

| Command | Behavior |
|---|---|
| `init` | Configure one private scoped store. |
| `put --record PRIVATE_JSON` | Create a record or an explicit correction. |
| `index` | Return current bounded references. |
| `get KEY` | Retrieve one current eligible record, or null. |
| `recall QUERY --limit N --budget BYTES` | Retrieve matching authorized context without silent truncation. |
| `forget KEY --confirm-record ID` | Remove every revision of the current record from this store. |
| `verify` | Check eligible index size and remaining content integrity. |

A record input has `key`, `title`, `kind` (`note`, `fact`, `preference`), `content` (text for notes, JSON object otherwise), `source`, `source_date`, optional `attribution` (`explicit_user`, `sourced`, `inferred`), optional `expires`, and optional `supersedes`. Dates include timezone offsets. A record body is limited to 3,000 UTF-8 bytes. Index budget is fixed at initialization; changing an existing store's scope/budget through constructor arguments is refused.

## Comparison protocol

`scripts/memory_experiment.py --output NEW_PRIVATE_DIRECTORY` runs the scripted control. It uses the same package snapshot and instructions in both arms. Only the frozen per-task memory context differs. Scripted outcomes check the controller and scoring pipeline; they are not evidence of agent benefit.

A live run additionally requires `--adapter codex --model MODEL --effort EFFORT --max-live-attempts 12`, and authorization for those twelve attempts. No retry or additional model run is implicit. Six development scenarios each receive one no-memory/memory pair:

| Scenario | Measured behavior |
|---|---|
| Delayed recall | Retrieve a narrative preference after reopening the store. |
| Correction | Use a corrected structured value, excluding its predecessor. |
| Stale memory | Abstain when a record is expired. |
| Deletion | Abstain after all record revisions are removed. |
| Cross-project access | Reject mismatched store scope and omit the other project's sentinel. |
| Task quality | Apply a remembered UTC offset to a supplied appointment time. |

The controller retrieves context before the model attempt. This experiment does **not** test autonomous index maintenance, tool selection, live memory writes or agent-operated SQL navigation. No inactive/private store is sent to the model. Cross-project success therefore establishes this API's filtering and absence of leakage in supplied context, not adversarial tool-access denial.

The primary score counts correct target task answers. No-memory abstention on recall-dependent tasks is appropriate but has lower information utility. A separate per-attempt check records whether the answer or abstention was appropriate for the information available in that arm. This distinguishes missing information from hallucination. Missing/failed attempts remain failures and are not silently omitted.

Expected answers remain controller-side; only contextual memories are placed in `memory-context.json`. Plan events freeze those inputs and their digest; changing the input file during execution invalidates the attempt. Reports name memory context as the comparison variable and always block verified release. Six authored examples with one attempt per arm are a development pilot, not protected acceptance, all-flavour calibration or proof of persistent improvement.

## Design influence and next decisions

[Millin Gabani's post](https://x.com/trillhause_/status/2087746105509331132) motivated testing simple files, SQL and a bounded memory index. It describes a proposed experiment, not a benchmark establishing effectiveness or an optimal index size. Daphnie's source attribution, expiry, explicit correction, scoped access checks and conservative release boundary are requirements of this project.

Revisit complexity only after measuring realistic longitudinal tasks, retrieval misses, context cost, stale-source failures and deletion propagation. Required later work includes host-enforced access, adversarial poisoning tests, independently authored holdouts, actual skill-use evidence and scoped retention across backups/exports.
