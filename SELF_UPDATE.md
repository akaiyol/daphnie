# Task-driven self-updates

Owner direction: Daphnie should identify useful skill changes, obtain evidence and advance eligible updates automatically within a policy approved once. Use existing task budgets only. This workflow is an owner-directed operating change, not a benchmark-verified learned procedure.

## Resources and responsibility

Daphnie owns the update work: inspect relevant evidence, make the smallest scoped candidate, run appropriate development checks, request protected evaluation, submit the signed bundle, and follow up on trial observations. Do not make the owner assemble records, select controller phases or approve every routine release already permitted by the host policy.

Use the active project's authorized tools, relevant source material, private evidence store, candidate workspace, controller, and remaining task allowance. Check the installed location and active version before editing. Do not fetch unrelated private histories or borrow another flavour's goals, context or allowance.

Additional model attempts must fit an explicit remaining task allowance. Count attempts before launch, including failures and retries, using the frozen plan and durable attempt history; never infer a fresh allowance from a new chat, process, candidate or model role. If no allowance is recorded, use deterministic checks and existing evidence, then save the candidate for a later authorized task. This workflow grants no new paid calls, account access, spending or background schedule. Independent reviews may consume the same task allowance; independence of judgment and access does not require an additional budget.

## Decision rules

1. Act on an observed recurring failure or a source-supported, testable opportunity. Record the expected benefit and where it may fail. A task-specific correction stays in its project; generalize only with transfer evidence.
2. Keep the exact candidate separate from the active baseline. Name the owning flavour, affected procedure, applicability, version change and rollback target. Preserve protected values, mode contracts, permissions, evaluator criteria and acceptance data.
3. Use inexpensive checks to discard broken candidates before model evaluation. Freeze comparisons and stopping criteria before acceptance. Prefer one focused candidate; do not search repeatedly against protected tasks or spend the remaining allowance merely because it exists.
4. Request acceptance and authorization from the configured trusted host within the approved policy and existing allowance. Daphnie may request review, but cannot issue the reviewer's signature, expose protected tasks to herself or treat her own confidence as acceptance.
5. Submit the resulting private signed evidence with `advance-update`. The controller decides whether to start a trial, promote, restore the original baseline after signed failure, retain an already verified version, or defer. Do not substitute manual unverified adoption to bypass a failed or unavailable gate.
6. During relevant subsequent tasks, collect scoped observations for the trusted trial reviewer. Submit updated signed observations through the same command. Existing chats may retain old instructions; count evidence only when the actual selected skill version is established.
7. If budget, evidence or a host capability is missing, retain the baseline or current unverified trial according to its stopping rules, preserve the exact candidate and next action privately, and report the specific missing resource. Ask the owner only for a policy exception, required new resource or consequential unresolved decision. Do not repeatedly ask permission already granted.

## Available controller action

From the controller checkout, use `python3 scripts/daphnie.py --state PRIVATE_STATE advance-update --bundle PRIVATE_SIGNED_BUNDLE`. This command stores private evidence and decision history and uses the [existing release policy](evaluation/RELEASE_POLICY.md). It performs no model calls and starts no background process. Valid but insufficient trial evidence defers; forged or mismatched evidence errors without promotion. Signed failure can restore the baseline even when the preceding evaluation has expired, provided the trusted policy and failure attestation remain valid.

The independent acceptance runner, authorization service and trial observer are host resources, not supplied by text instructions or this command. Check `release-status` before relying on them. If not configured, prepare the candidate and development evidence; do not fabricate independent reviewers or claim automatic production releases are running. The user should receive meaningful release, rollback or unresolved-blocker notices, not a request to direct each routine transition.
