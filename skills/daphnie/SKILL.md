---
name: daphnie
description: Route Daphnie requests to design, think, assistant or research guidance when the user invokes Daphnie without a specific mode.
---

# daphnie

Read [core](references/core.md) and the [operating contract](references/operating.md) once in the active context. Choose the mode matching the requested outcome: [design](references/design.md) for artifacts, [think](references/think.md) for decisions, [assistant](references/assistant.md) for execution, or [research](references/research.md) for evidence. Read only the selected mode. For the selected mode, read only its library manifest: [assistant](references/assistant-library/manifest.json), [research](references/research-library/manifest.json), [design](references/design-library/manifest.json), or [think](references/think-library/manifest.json). Load only relevant listed procedures. On a genuine mode switch, apply the operating contract’s bounded handoff and context-reset rules; do not blend flavour instructions.
