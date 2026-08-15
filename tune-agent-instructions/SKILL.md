---
name: tune-agent-instructions
description: Turns observed agent behavior into minimal, correctly scoped improvements to AGENTS.md, CLAUDE.md, skills, or supporting scripts. Use when the user asks to tune, improve, rewrite, or update agent instructions based on failures, retrospectives, or repeated corrections.
---

# Tune Agent Instructions

Improve future behavior with the smallest evidence-backed change. Treat instruction files as production configuration: understand precedence, avoid duplication, and verify the result.

## Inputs

Use an agent retrospective, cited sessions, the current conversation, or concrete examples supplied by the user. If evidence is unavailable, inspect accessible history read-only or state that the change is preference-driven rather than evidence-backed.

Read each target file completely before editing, including applicable parent and nested instruction files. Preserve unrelated user changes.

## Workflow

1. Describe the observed behavior, desired behavior, evidence, frequency, impact, and plausible cause. Separate a model problem from a tool, environment, prompt, or repository-discoverability problem.
2. Read [Placement and evaluation](references/placement-and-evaluation.md) and choose the narrowest effective destination:
   - Global instructions for stable cross-project collaboration defaults.
   - Repository instructions for domain language, invariants, commands, architecture, and recurring local hazards.
   - Skills for optional, repeated, multi-step workflows with recognizable user triggers.
   - Scripts for deterministic mechanics, validation, formatting, or parsing.
3. Audit existing guidance for an instruction that should be clarified, replaced, or removed. Prefer editing the source of truth over appending another rule.
4. Draft the minimum change. State the desired action and its boundary. Explain why only when it helps the agent generalize.
5. For subjective output, add one compact bad/good example drawn from sanitized real behavior. Do not fill instruction files with examples the model already handles reliably.
6. For a skill, keep the frontmatter description concise: capability first, then `Use when ...` with likely trigger words. Put workflow details in the body and split references when the main file grows beyond 100 lines.
7. Preserve instruction precedence: explicit user direction overrides preferences and defaults. Do not turn a default into an absolute prohibition unless safety requires it.
8. Apply the edit, then inspect the complete resulting files and diff for contradictions, ambiguity, duplication, accidental scope expansion, and token bloat.
9. Replay at least three scenarios: the original failure, a nearby case where the instruction should not apply, and an explicit user override. Add a safety scenario when the change affects destructive or external actions.
10. Report the changed files, placement decision, behavior expected to change, scenarios evaluated, and residual uncertainty.

## Guardrails

- Do not encode a one-off annoyance as a permanent rule unless its impact is severe.
- Do not add model-specific steering when a general behavioral instruction is clearer and more durable.
- Do not copy another person's global instructions wholesale; translate the underlying failure into the user's terminology and workflow.
- Do not solve poor repository discoverability only with prose when a clearer structure, script, or command would remove the ambiguity.
- Do not commit, push, install globally, or sync changes to other machines unless the user asks.

## Completion

Complete when every edit has evidence or an explicit preference behind it, lives at the correct scope, passes the scenario review, and leaves no unexplained diff. Recommend another observation cycle rather than adding speculative rules.
