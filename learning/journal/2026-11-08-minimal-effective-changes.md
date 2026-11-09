# Minimal effective changes: owner-directed adoption

Date: 2026-11-08. Status: owner-directed operating refinement and scoped implementation repairs. This is not an automatically promoted learned skill or a demonstrated improvement in live agent performance.

## Adopted guidance

[Operating guidance](../../OPERATING.md) now makes the existing simplicity principle actionable: prefer the smallest complete change that fixes the cause, preserves required behavior and remains clear to verify and maintain. Reuse capabilities, keep decisions at their owner, test a shared premise when repeated fixes fail, and retire obsolete paths only after verifying their replacement. Changed-line count alone is not quality.

[Maintenance guidance](../../MAINTENANCE.md) directs enforceable lessons into the owning check or tool rather than another instruction repeating the rule. Judgment remains in shared operating guidance, loaded through all five existing entrypoints. No new skill router or duplicated flavour instructions were added. The owner subsequently selected automatic delegation within policy and required Daphnie to own every worker contribution; the [delegation contract](../../DELEGATION.md) and [source review](../../research/2026-11-08-delegation-and-evaluation-research.md) record that addition and its runtime limits.

## Mandate check

| Daphnie mandate | Alignment |
|---|---|
| Consistent personality and judgment | CORE.md remains unchanged; it already values craft, discernment and simplicity with purpose. |
| Distinct flavours with contextual project knowledge | Mode contracts and library manifests remain unchanged; no project lesson is imported as a global goal. |
| Own useful outcomes within permission | Repairs target reproduced failures; Daphnie remains accountable for every worker’s scope, resources, supervision, verified result and recovery. |
| Improve through evidence and controlled updates | Existing evaluation, signed authorization, trial and rollback gates remain in force. No candidate is called verified merely because guidance was written. |
| Autonomy with usable resource limits | Existing task budgets only; no new app access, model allowance, schedule or background service. |
| Standalone cross-app direction | Retain the proposed runtime-first sequence. This refinement does not pretend to implement the missing supervisor, reviewer or installation migration. |

These checks compare the adopted change with [core](../../CORE.md), the [operating contract](../../OPERATING.md), [architecture](../../ARCHITECTURE.md), the original [source-to-decision record](../../research/2026-11-04-core-redesign.md) and the owner's current direction. They are a consistency review, not measured preservation of personality across live tasks.

## Lessons encoded in implementation

The [pstack review](../../research/2026-11-08-pstack-decision-review.md) reproduced two defects. Both received focused repairs:

- Procedure version validation compares an existing skill's prior path/content with its proposed path/content. Redirecting an existing ID requires a version increase; a correctly increased version can still complete the signed trial/promotion path.
- The update boundary validates the evaluation envelope before accessing its fields. Malformed input follows the CLI's existing validation-error path; no broad exception handler was added.

Regression checks establish the former failures and accepted corrected behavior. A separate check preserves authorization freshness after staging. No evaluation thresholds or evidence requirements were relaxed; efficiency-specific profiles remain proposed.

## Validation and adoption

All 93 tests pass, including the new negative/positive versioning and CLI regressions. Both original failures were observed before the repair. The package checker passes. All nine pinned model configurations and fourteen real-code replay checks pass after reviewing the source/model correspondence; the finite model still abstracts manifest and JSON details. The [rerunnable diagnostic](../../research/probes/pstack_decisions.py) reports neither reviewed defect, while retaining the final authorization check. These are control-mechanics results using synthetic evidence, not proof of live task improvement.

Operating refinement is explicitly owner-authorized in this request. It is not a claim that independent acceptance established its behavioral benefit. Actual usefulness must be assessed on later relevant tasks, including whether unnecessary work and repeated corrections decrease without loss of quality.

## Attribution

Adapted from pstack, by poteto and contributors, at commit `6b0300214a09fd6029cfb7077043125758cd1fd2`: [Laziness Protocol](https://github.com/cursor/plugins/blob/6b0300214a09fd6029cfb7077043125758cd1fd2/pstack/skills/principle-laziness-protocol/SKILL.md), [Subtract Before You Add](https://github.com/cursor/plugins/blob/6b0300214a09fd6029cfb7077043125758cd1fd2/pstack/skills/principle-subtract-before-you-add/SKILL.md), and [Encode Lessons in Structure](https://github.com/cursor/plugins/blob/6b0300214a09fd6029cfb7077043125758cd1fd2/pstack/skills/principle-encode-lessons-in-structure/SKILL.md). The owner requested adoption. Daphnie's core simplicity principle predates these sources; the later operational refinement receives this attribution. No pstack runtime or source code is copied into the package.
