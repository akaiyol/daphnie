# Skill lifecycle model verification — 2026-11-08

Historical record. See [subsequent resolution](2026-11-08-lifecycle-resolution.md) for current implementation status.

Status: finite model checked and concrete witnesses replayed; **not a clean verification result**. Product controller code, installed skill libraries, background schedules and promotion permissions were not changed. No model API calls were made.

## Method

Used TLA+ tools release v1.7.4 (TLC 2.19) with the existing OpenJDK 24.0.2 runtime and one TLC worker. The binary was downloaded from the official release into private temporary storage and checked against its published release checksum; the rerun command additionally pins its SHA-256. No global tool installation or pstack runtime was used.

The [model and verification skill](../verification/skill_lifecycle/README.md) cover one baseline and one candidate, prepared packages, content validity, confirmation, rollback history, report labels, validation/transaction/pointer stages and crash/recovery actions. Checks are exhaustive over each finite reachable model graph, subject to TLC fingerprinting. They are not an unbounded proof or a proof that every implementation behavior is represented.

At the initial review, the source directory was not a Git checkout, so coverage recorded actual source-function fingerprints with a null `sync_commit`. [Current coverage](../verification/skill_lifecycle/coverage.json) also pins the committed implementation snapshot and retains those fingerprints. A commit pin does not replace source/model correspondence review.

## Results

| Configuration | Observed result | Interpretation |
|---|---|---|
| Current safety invariants | All six hold; 7,844 distinct states | The modeled guards/labels hold, within scope. |
| Content integrity at activation commit | Counterexample; 79 states explored before detection | A package may change after precheck and before commit. |
| Manual adoption reachability | Witness found | Valid explicit unverified adoption is possible. |
| Rollback reachability | Witness found | Returning to a previously active release is possible. |
| Pointer reconciliation reachability | Witness found | Pointer synchronization is possible after committed DB state. |
| Verified learned-release reachability | No path in the complete 7,844-state graph | Implementation lacks that transition; manual adoption is not a substitute. |
| Removed confirmation guard | Counterexample detected | Negative control catches missing confirmation. |
| Removed rollback-history guard | Counterexample detected | Negative control catches rollback to a never-active release. |
| False verification label | Counterexample detected | Negative control catches mislabeling manual adoption as verified. |

Deadlock checking was enabled. Reachability witnesses do not establish eventual recovery under arbitrary scheduling; no temporal fairness/liveness guarantee is claimed. Early counterexample runs stop at their first violation, so their explored counts are not full-graph sizes.

## F001 — Integrity race reproduced in real code

The shortest model witness contains four actions after initialization:

1. Prepare the package.
2. Validate the package for adoption.
3. An external writer changes its contents.
4. Commit activation without rechecking before the transaction commits.

The real-code replay injected the external file write immediately after successful validation. `Store.activate` committed its active/history records, then `reconcile_active` rejected the modified package and raised an error. In the replay, the DB named the new release while the pointer still named the previous one.

This requires package-file write access during activation. It does not demonstrate an authentication bypass or establish that the race occurred in a real user run. It shows a concrete failure of the stronger content-at-commit guarantee and a persistent state change despite the API reporting an error. The controller operator lock does not prevent direct external file writes. No invariant was weakened to hide the finding, and no product fix was made in this verification task.

## F002 — Verified learning remains an implementation gap

Development comparisons remain blocked. The offline reviewer can report eligibility from supplied records, but it grants no authorization. Manual adoption records `behavior_verified: false`. No implemented transition binds protected acceptance, externally validated authorization and a verified learned release. The model preserves that absence rather than adding an imaginary success edge.

## Concrete checks and retained evidence

The replays exercise real prepared packages, wrong confirmation rejection, never-active rollback rejection, valid manual adoption, interruption after DB commit, pointer recovery, rollback and the content race. Three in-memory broken versions of the real activation method reproduce the corresponding safety violations. The original method is restored, and production source fingerprints remain unchanged.

The complete Python suite passed **67 tests**, including the new real-code witness and source-drift checks. Package structural checks passed. These passes validate the verification harness and specific executable mechanics; they do not turn F001/F002 into successes or establish agent task quality.

Raw checker outputs, configs' digests, model/tool/source identities, witness action paths and the final report are retained privately outside the repository. The final run returns exit code **1**, correctly signaling findings. Initial parser/model-assignment diagnostics were preserved separately; they were corrected in the model without changing any product rule. A restricted local-communication startup failure was a tool-execution error, not a lifecycle counterexample.

## Next decision

Address F001 through a separately reviewed activation/immutability design with matching real-code tests. Merely moving the same unlocked precheck closer to the commit does not establish atomicity against another writer. Design the verified-release path separately, retaining independent authorization and acceptance evidence. Rerun the model, negative controls and real-code checks after either change; behavioral quality evaluation remains a separate requirement.

Attribution and tool references are in the [verification documentation](../verification/skill_lifecycle/README.md). Formal modeling complements the [evaluation protocol](../evaluation/PROTOCOL.md); it does not replace it.
