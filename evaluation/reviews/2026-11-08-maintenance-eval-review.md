# Maintenance change reviewed against evaluation principles

Date: 2026-11-08. Verdict: partial alignment; behavioral value unproven. This review does not change active instructions, authorize live calls or release a candidate.

## Findings

1. **High — The shared maintenance requirement is itself an unevaluated behavioral change.** It was installed across all flavours as an owner-directed instruction. Ownership authorization establishes permission, not effectiveness. The 65 passing tests check existing implementation and package integrity, not whether this instruction improves outcomes, reduces recurring errors or justifies added work. It should be evaluated separately from the two procedure candidates before being retained as an empirically supported global improvement.
2. **High — Writing a candidate is not evidence of useful learning.** Exact patches and provenance are good artifacts, but the causal chain still needs observation: authorized relevant guidance was available, the agent actually used it appropriately, and downstream outcomes improved relative to the baseline. The current candidate records explicitly have no frozen evaluator and no protected acceptance cases.
3. **Medium — Edit pressure needs a no-change control.** Requiring follow-through is reasonable; rewarding candidate production can generate redundant instructions and overhead. Correct no-change, deferral and rejection decisions should count as successes where evidence does not justify a modification. Candidate volume and changed-file counts are not optimization targets.
4. **Medium — Repair classification requires a semantic boundary.** A behavior-preserving correction within task authorization can proceed with focused regression checks. Changes to decision policy, retrieval, flavour behavior or update criteria remain behavioral candidates regardless of which file contains them. Do not classify an instruction rewrite as a routine repair merely to avoid evaluation.
5. **Positive — Candidate scope, provenance and rollback are explicit.** Both assistant/design proposals name exact files, versions, source hashes, evidence, tests and a prior baseline. They remain inactive and do not claim verification. Core, permissions and evaluation criteria were not relaxed to activate them.
6. **Open — Enforcement remains absent.** The new instruction does not make timeouts, access restrictions, protected acceptance or approval independent of the learner. Existing mandatory unknown checks must continue to block learned release.

## Evaluation needed

First compare the baseline operating guidance with the maintenance requirement alone on matched tasks across all four flavours. Freeze model/tool configuration, task families, budgets, rubrics and stopping rules before results. Measure task quality, appropriate maintenance/no-change decisions, recurrence, regressions, active time and available usage separately. Include maintenance overhead, not just candidate-writing time. Use independently authored held-out families for acceptance, randomize order and blind subjective judgments where practical.

Then evaluate each procedure patch separately within its destination flavour. Observed project gains motivate a candidate; they do not prove broader transfer. Include irrelevant and stale lessons, cross-project/flavour boundaries, harmful updates and no-change controls. When actual experience use is uncertain, compare original evidence with condensed guidance under declared information and resource constraints.

Calibrate evaluators against independently established outcomes. A fresh model reviewer is not sufficient ground truth, and author-created public tests cannot double as protected acceptance. Predeclare useful benefit and allowed regression/cost bounds using pilot variability; do not invent a universal task count or retrospective threshold.

Only supported candidates proceed to a scoped monitored trial with explicit authorization and tested rollback. Retain no change when evidence is inconclusive. The missing live-attempt allowance remains a separate boundary.

## Research basis and limits

- [Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988v3), Gloaguen et al.: context files did not generally improve the evaluated coding-task success rates and increased average cost. Application here: added maintenance text must earn its overhead; this does not establish how it will affect Daphnie.
- [SkillsBench](https://arxiv.org/abs/2602.12670v4), Li et al.: matched skill/no-skill conditions and deterministic outcomes support measuring skill efficacy; focused skills outperformed larger bundles in that benchmark. Application here: isolate each change and measure actual artifacts, not file production.
- [Harness Updating Is Not Harness Benefit](https://aclanthology.org/2026.emnlp-main.2326/), Lin et al.: producing harness updates and benefiting from them are distinct capabilities; activation and faithful following can fail. Application here: inspect adoption, appropriate use and outcome separately.
- [Large Language Model Agents Are Not Always Faithful Self-Evolvers](https://proceedings.mlr.press/v306/zhao26aw.html), Zhao et al.: causal interventions found agents could ignore or misinterpret condensed experience in the tested systems. Application here: preserve source evidence and test causal experience use rather than assuming a summary drives behavior.

These are design implications from the cited tested settings, not research validation of this combined implementation. The [project evaluation protocol](../PROTOCOL.md) remains the governing policy. The [maintenance requirement](../../MAINTENANCE.md) is installed but behavior-unvalidated; [assistant/design candidates](../candidates/2026-11-08/records.json) are proposed and inactive.
