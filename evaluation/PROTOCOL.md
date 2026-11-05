# Evaluation and release protocol

## Status and tools

This protocol governs proposed learning. `scripts/evaluate.py` reviews paired outcome records and produces an offline eligibility report; it does not invoke a model, verify the truth of submitted scores, grant authorization or activate a release. `tests/test_evaluate.py` checks the review logic with synthetic records. No live learning, personality preservation or host isolation has yet been demonstrated.

## Before evaluation

1. Record the failure evidence, candidate type, target flavour/library, applicable projects, exact diff, baseline version, predicted benefit, failure modes and rollback state.
2. Fix the model configuration, tools, starting state, resource budgets, outcome rubric, minimum useful improvement, maximum tolerated regressions and stopping rule before seeing acceptance results. Keep authorization outside the learner's control.
3. Split task families into development, validation and protected acceptance sets. Related variants stay in one partition. Limit acceptance submissions and replenish independently authored tasks; do not tune repeatedly on the same held-out set.
4. Execute baseline and frozen candidate in isolated environments with independent memory snapshots. Randomize order and blind subjective reviewers to version identity. Use controlled tools and fixtures before trials with live effects. Do not perform unauthorized real actions to test boundary compliance.

A first pilot can use 40–60 task families across the four flavours to discover scoring defects and variability. This is a planning range, not a reliability claim or an automatic promotion threshold. Set the eventual acceptance size using observed variance and the importance of the decision. Repeats within a family do not count as new independent families.

## Checks by change type

| Type | Required evidence |
|---|---|
| Knowledge | Source fidelity, date/freshness, contradiction revision, correct retrieval and applicability |
| Preference | Accurate attribution, explicit vs inferred status, correction/deletion support and scope |
| Skill | Paired task outcomes, unseen-family transfer, flavour fidelity, regressions and efficiency |
| Retrieval | Authorized relevant selection plus downstream quality; resist irrelevant, stale or incorrect records |
| Core, flavour contract, permissions, evaluator | Owner-controlled review; ordinary learning cannot promote these changes |

## Outcomes and diagnosis

Record task success, accuracy, attribution, correction recurrence, transfer, flavour fidelity, boundary violations, cost and latency separately. Assess the flavour's actual role and decision behavior, not stock wording. Subjective work uses a declared rubric and blinded human calibration; model agreement alone is not correctness.

The primary comparison is current approved version vs candidate. For memory diagnosis, additionally compare no relevant memory, original supporting evidence, condensed candidate, irrelevant memory and stale/incorrect memory. Correct selective use matters: unchanged behavior can be appropriate, and sensitivity to false memory is not a success. Preserve information availability and budgets when comparing representations.

For privacy and poisoning, test flavour switching, cross-project retrieval and direct access, malicious source instructions, overgeneralized lessons, contradictory evidence, retention selection and consolidation order. A record may be authentic and still be inapplicable. Evaluate at the retrieval, action and output layers.

## Validate the evaluator

Use protected calibration tasks with independently established improvements, known regressions, permission failures, cosmetic changes and inconclusive differences. Measure false approval, false rejection, reviewer disagreement and sensitivity to output order or version labels. Human-review subjective judgments and disagreements. Known answers must not be supplied to the candidate builder. Synthetic tests of the report code are necessary but do not calibrate an LLM judge or establish task realism.

Do not release on an evaluator whose known errors could reverse the decision. Keep the evaluator version and calibration evidence with each report.

## Decision and uncertainty

Critical permission/privacy violations block promotion regardless of average quality. Unknown mandatory checks block eligibility. Candidate quality must exceed the predeclared useful-improvement threshold with adequate uncertainty bounds; regressions and resource use must remain within predeclared limits. Insufficient evidence means inconclusive and retains the baseline.

The offline reviewer averages repeats within task families, then gives each family equal weight. It uses a deterministic family bootstrap for a 95% interval over paired quality changes. Its interval describes the submitted sample, not unseen domains; small or unrepresentative samples remain weak evidence. The configured minimum family count and benefit threshold must be justified before evaluation. It separately checks each regression family, cost ratios and required checks. It supports procedural skill/retrieval comparisons only; use evidence review for knowledge/preferences.

## Controlled release and recovery

An eligible candidate still needs authorized activation and a limited trial. Freeze a report and release record naming the exact candidate, target library, versions, evidence, approver, scope, prior state and trial stopping conditions. Limit rollout to that scope; do not modify other libraries implicitly. Shared changes require all-flavour regression evidence.

Monitor later task outcomes, recurrence, drift, new failures, resources and interventions. Revert on critical violations or predefined trial failure. Restore the prior skills, retrieval configuration and compatible memory snapshot; reverting files alone may leave learned effects behind. Test recovery in isolation before relying on it.

The implementation milestone is an observed end-to-end cycle on a narrow real task family, followed by held-out transfer, adverse-memory checks, evaluator calibration, limited trial and demonstrated rollback. Individual passes do not establish reliability across years or interacting updates.
