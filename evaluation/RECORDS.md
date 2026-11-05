# Private record contracts

Store completed records and acceptance data outside the public tree. All references must point to authorized, accessible evidence; do not put credentials in records. Stable IDs can reference private data without publishing its contents.

## Candidate

Required fields: ID, type, originating flavour/project, target flavour/library, information owner, permitted destinations, applicability, baseline version, exact proposed diff/hash, evidence references, prediction, risks, fixed evaluation policy, evaluator version and stopping rule. A transfer names and evaluates its destination separately.

## Paired comparison input

`scripts/evaluate.py INPUT.json --output REPORT.json` accepts a JSON object with:

- `candidate_id`: nonempty string.
- `flavour`: assistant, research, design or think.
- `change_type`: skill or retrieval.
- `policy`: `min_families` (integer >= 2), `min_improvement` (0–1), `max_regression` (0–1), `max_cost_ratio` (finite number >= 1).
- `checks`: exactly these mandatory names, each pass/fail/unknown: `evidence_integrity`, `flavour_fidelity`, `permissions`, `privacy`, `context_isolation`, `transfer`, `evaluator_calibration`.
- `runs`: nonempty list of paired records. Each has `family`, `split` (acceptance), `suite` (target or regression), `baseline`, `candidate`, `baseline_cost`, `candidate_cost`. Quality values are finite 0–1 scores from the fixed outcome rubric; costs are finite positive values in one declared unit. Family IDs belong to one suite only. Repeats share a family ID.

The reviewer rejects malformed data. Mandatory failures produce reject, unknown checks produce inconclusive, and too few target or regression families produce inconclusive. A supported gain can produce eligible_for_trial, never verified or released. The input policy is not trusted authorization: a maintainer must freeze and protect it before runs, and confirm report inputs against actual artifacts.

## Evaluation report

Contains candidate identity, flavour, type, input digest, policy, check results, family counts, paired mean improvement and bootstrap interval, worst regression, worst mean family cost ratio, decision and reasons. Preserve source runs and evaluator version with the report. Re-running the reviewer must not silently replace an existing report.

## Memory record

Required fields: ID, originating flavour/project, information owner, confidentiality, allowed destinations, applicability, source/date, status, revision history and superseded record where relevant. Explicit preferences are distinguished from inference. Missing permissions deny retrieval. Expiry, correction and deletion must propagate to retrieval indexes and restored snapshots according to the private store's policy.

## Release record

Required fields: release ID/date, candidate and exact diff/hash, target library and skill versions, accepted report references, trial evidence, owner/maintainer authorization, permitted scope, dependency versions, active retrieval configuration, compatible memory state, prior release and rollback instructions. No record is approval merely because Daphnie wrote an approver name. The host must validate authority externally.

## Local controller records

The [controller](CONTROLLER.md) stores hash-linked events, content-addressed manifests, scoped observations/bundles, candidate workspaces, frozen development plans, attempts, immutable comparisons and manual activation history in a private SQLite store. These are development records; they do not fulfill the protected acceptance and externally authorized release contracts above. A manual adoption is explicitly `behavior_verified: false`. Process interruption leaves an incomplete attempt; recovery never replays external actions.
