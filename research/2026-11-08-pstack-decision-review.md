# Pstack review of Daphnie's architecture decisions

Date: 2026-11-08. Scope: implementation at review time and the [proposed standalone direction](2026-11-08-architecture-direction-review.md). Historical status: two reproduced defects, with no fixes made during that review. Subsequent repairs and operating adoption are recorded in [minimal effective changes](../learning/journal/2026-11-08-minimal-effective-changes.md); the observations below preserve the original failure evidence.

## Intent and method

Daphnie should operate across apps/projects and improve scoped procedures within a standing owner policy and existing task budgets. The review challenged the proposal as well as current code, preserving owner control of core, permissions and acceptance criteria.

Applied upstream pstack instructions at commit `6b0300214a09fd6029cfb7077043125758cd1fd2`:

- [Interrogate](https://github.com/cursor/plugins/blob/6b0300214a09fd6029cfb7077043125758cd1fd2/pstack/skills/interrogate/SKILL.md): adversarial reviewers supplied executable reproductions; the root reviewer reran retained findings and merged duplicate causes. No fixes applied.
- [Attack the Premise](https://github.com/cursor/plugins/blob/6b0300214a09fd6029cfb7077043125758cd1fd2/pstack/skills/principle-attack-the-premise/SKILL.md): explicitly tested whether the quality-only gate can recognize an efficiency-only improvement. This does not claim two live improvement attempts failed or that the supplied costs were measured.
- [Boundary Discipline](https://github.com/cursor/plugins/blob/6b0300214a09fd6029cfb7077043125758cd1fd2/pstack/skills/principle-boundary-discipline/SKILL.md): tested malformed external input and distinguished input normalization from authorization freshness at publication.
- [Subtract Before You Add](https://github.com/cursor/plugins/blob/6b0300214a09fd6029cfb7077043125758cd1fd2/pstack/skills/principle-subtract-before-you-add/SKILL.md): applied as a planning pass over the proposed architecture. No code was deleted during this read-only review.

Pstack is maintained by poteto and contributors in `cursor/plugins`; credit belongs to those authors for the review methods. These methods are not external certification of Daphnie. The skill instructions were read from upstream without installing the plugin or copying its runtime/source into this package. The Daphnie-specific diagnostic is original review code.

No pstack model panel was configured. The default Claude/Grok families were unavailable in this environment; two separate contexts used the available parent model, following the runner fallback. There is no multi-model independence claim. `architect` was inspected but its implementation workflow was not run; the user requested review of decisions. The benchmark checklist was screened, but no speed comparison or new performance benchmark was run.

## Reproduce

Run from the repository root:

```sh
PYTHONPYCACHEPREFIX=/tmp/daphnie-pstack-probe-cache python3 research/probes/pstack_decisions.py
```

The diagnostic uses real current Store, release, update, evaluator and CLI code with disposable `tests/test_release.py` fixtures. It needs OpenSSL Ed25519 support. It makes no live model calls, writes no production policy/state and performs no app actions. Exit 0 means the diagnostic completed; inspect `observed_defect` fields rather than treating exit 0 as acceptance. Full raw reviewer reports and captured outputs were retained privately outside this repository.

## Retained findings

### P2: Procedure identity can change without increasing its procedure version

Location: [ReleaseAuthority.evaluation](../scripts/control/release.py), comparison of the prior skill and candidate path near lines 163–172.

Both adversarial reviewers independently reproduced this; root reran it. A baseline contains distinct `procedure.md` and inactive `alternate.md`. The candidate changes the existing skill's path to `alternate.md`, increments its library version, and leaves its procedure ID/version unchanged. Only the manifest differs between snapshots. The gate compares old/new entries at the candidate's path, so it sees an unchanged file rather than the changed active procedure.

Observed diagnostic output:

```json
{
  "before": {"id":"procedure","path":"procedure.md","version":"1.0.0"},
  "after": {"id":"procedure","path":"alternate.md","version":"1.0.0"},
  "selected_text": "Different active procedure",
  "trial": "applied",
  "promotion": "applied",
  "control_verification_label": true,
  "observed_defect": true
}
```

Required by the existing [release policy](../evaluation/RELEASE_POLICY.md): reject a changed procedure whose version did not increase, preserving the selected baseline. Increasing the library version alone does not satisfy the separately required procedure-version rule.

Impact: procedure ID/version alone cannot reliably attribute which guidance ran. Package hashes still distinguish the snapshots, signatures remain required, and no unauthorized cryptographic approval bypass was reproduced. The `true` label above is the control's result under synthetic evidence, not real behavioral verification.

Decision implication: retain immutable release snapshots, but define and validate procedure identity using the existing ID's resolved content/dependencies and version. Do not rely on path equality or a version string alone. Existing same-path tests and the finite lifecycle model do not cover this manifest semantic invariant.

### P3: Malformed evaluation input escapes the CLI error boundary

Location: [advance_update](../scripts/control/update.py), line 19; normal error handling in [CLI main](../scripts/control/cli.py), lines 206–208.

Reviewer 2 and root reproduced it using the actual host-policy loader with only its policy path relocated to a read-only disposable fixture. Supplying `evaluation: []` or `evaluation: null` causes `.get` to be called on a list or null before the signed-body type check.

Observed: `AttributeError` escapes `cli.main`; there is no normal validation error message or return value. The baseline remains selected.

Required: return the CLI's normal code 2 and a validation message without an exception escaping. No unauthorized activation or deployed daemon crash was reproduced; the latter is not implemented and is not a finding.

Decision implication: validate the complete external envelope at entry, pass a stable internal representation to decision logic, and preserve explicit error categories. Do not merely add a broad catch that disguises programming errors.

## Premise and defense checks

**Quality-only benefit is too narrow for the intended policy.** The diagnostic supplies unchanged quality of 1.0 and a cost ratio of 0.5 across three target and three regression families, with mandatory checks passing. The reviewer returns `inconclusive` because there is no quality gain above the configured threshold. This is correct under its present quality-only contract, not a code defect. It confirms that recognizing resource improvements requires a separately approved efficiency profile with quality noninferiority. The supplied costs are synthetic, not measured savings or a benchmark result.

**Final authorization validation is necessary.** The diagnostic first obtains a valid grant, stages the real deployment, then advances its controlled clock past the grant's expiry while the evaluation and policy remain valid. The final gate rejects publication and preserves the baseline. Captured fields: `staged_before_expiry: true`, `expired_grant_rejected: true`, `baseline_preserved: true`. This check crosses a time-of-use boundary; it is not redundant internal validation to delete for stylistic simplicity.

**Installation and runtime gaps remain disclosed gaps.** A read-only observation confirmed the five installed entrypoints still point to the editable canonical checkout. No managed-release migration, runtime watchdog, protected reviewer or standalone task supervisor was created by these probes. Their absence was already stated in the proposal; the review does not reclassify it as an undisclosed regression.

## Effect on the proposed direction

The reproduced evidence supports retaining the proposed runtime-first sequence, with more precise acceptance conditions:

1. Keep the initial deployment small: one trusted supervisor, restricted workers and a mediated tool surface. Do not add independently deployed signing/reviewer services until a real boundary needs them. A real protected evaluation/activation boundary remains necessary.
2. Make procedure identity and the version actually loaded by each task authoritative before relying on automatic updates. Address the P2 invariant before treating procedure-version histories as reliable evidence.
3. Introduce change-specific evaluation profiles through an owner-approved revision. Preserve critical permission/privacy checks for every applicable profile; do not bypass a failed quality gate through manual adoption.
4. Concentrate external parsing and domain invariants in explicit boundaries. Preserve freshness checks at publication, rollback history and exact snapshot validation.
5. Remove the live dependency on editable-checkout installation when deliberately migrating to managed releases. Retain development history and avoid deleting alternate paths before migration is verified.
6. Demonstrate one full failure-to-improvement cycle with actual loaded-version evidence and outcomes before expanding apps or service topology.

There was no reproduced contradiction proving that the standalone architecture or its proposed implementation order is wrong. That is not validation that the unbuilt runtime will work. Shared skill dependencies, isolation mechanisms and review calibration still require implementation-specific tests.

## Dropped and unproven items

Reviewer 1 dropped five candidates: missing watchdog, editable-checkout installation, signed claims versus actual outcomes, incomplete memory/app-effect rollback, and same-account access defeating an in-process boundary. Each was already disclosed or did not establish a new defect. Two further hypotheses—nested-trial accountability and abrupt power-loss durability—had no reproduced violation.

Reviewer 2 dropped three candidates: absent standalone integration, unobserved/expired-policy trial recovery, and installed-link migration. Two further hypotheses—insufficient worker restriction in a future implementation and an inefficient implementation order—were not demonstrated. These counts are per-reviewer and overlap; they are not eight unique defects. The duplicate P2 finding was merged. Root retained two distinct defects after rerunning them.

The reviewer also ran the existing release and update suites: all 23 tests passed while these gaps remained reproducible. Passing those suites and the earlier bounded model does not establish complete semantic coverage, live learning benefit, protected acceptance honesty or host isolation.
