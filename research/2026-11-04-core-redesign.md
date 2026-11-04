# Source-to-decision record — 2026-11-04

Primary-source details below were verified by the lead and supplied to the package implementation. Access date: 2026-11-04. Publication dates are distinct from access dates. Current sources inform mechanisms; older material is foundational, not recent news.

| Source and date | Applied decision | Limit |
| --- | --- | --- |
| [Anthropic, Managed Agents](https://www.anthropic.com/research/managed-agents), 2026-04-08, current | Separate instructions/records from host runtime and sandbox responsibilities. | Does not supply this package with a runtime or continuity. |
| [Anthropic, Demystifying evals](https://www.anthropic.com/research/demystifying-evals-for-ai-agents), 2026-01-09, current | Prefer verified outcomes; combine deterministic, model and human judgments where useful; allow unknowns. | Model grading is not user acceptance; rigid paths can reject valid solutions. |
| [OpenAI, Goals in Codex](https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex), 2026-05-09, current | Make outcome, evidence, constraints, boundaries and blocked stops explicit. | Instructions alone do not start a goal or guarantee continuation. |
| [OpenAI, Codex as a platform](https://developers.openai.com/blog/codex-as-a-platform), 2026-08-19, current | Reuse host tools, context and harness boundaries. | No new access or execution rights. |
| [Google, Harness engineering](https://developers.googleblog.com/en/the-anatomy-of-harness-engineering-how-to-evaluate-iterate-and-guard-ai-coding-agents/), 2026-09-09, current | Use behavioral probes for concrete decision failures alongside outcomes. | Avoid treating one prescribed trajectory as quality on complex tasks. |
| [Shopify, Nix](https://shopify.engineering/what-is-nix), 2020-05-19, foundational | Keep installation dependencies and actions explicit; use a standard-library-only package. | This package neither adopts Nix nor claims reproducible environments. |
| [OpenAI, Skills](https://learn.chatgpt.com/docs/build-skills?product=breeze), maintained documentation, accessed 2026-11-04 | Focus entrypoints and load references progressively. | Structural validation does not demonstrate useful behavior. |

No broad source copying or retrospective attribution. These transfers remain bounded design choices pending actual task evidence.
