---
name: agent-retro
description: Audits coding-agent history to identify evidence-backed failure patterns, time sinks, and differences between models or harnesses without modifying files. Use when the user asks to audit or analyze agent history, recurring agent mistakes, corrections, tool usage, slow runs, or model performance.
---

# Agent Retro

Turn real interaction history into a defensible account of what helps and hurts. This skill is read-only: do not edit instructions, skills, code, or external records.

## Scope and privacy

Infer the repository, time range, harnesses, and models from the request and accessible history. State assumptions and blind spots. Discover histories through known harness indexes or configuration before searching broadly.

Treat transcripts as sensitive user data. Keep analysis local, never upload raw history, redact secrets and personal data, and quote only the minimum needed to support a finding.

## Workflow

1. Inventory the available sessions, dates, repositories, task types, harnesses, and model identifiers. Never infer a model identifier that is absent.
2. Define denominators before counting: sessions, user messages, tool calls, elapsed active time, or pull requests. Preserve raw counts alongside normalized rates.
3. Read [Failure taxonomy](references/failure-taxonomy.md). Identify candidate events, then inspect their surrounding prompt, actions, tool results, correction, and outcome before counting them.
4. Separate observed facts from inferred causes. A nonzero command exit, user follow-up, long duration, or abandoned branch is not automatically an agent failure.
5. For slow or expensive runs, group tool calls into discovery, implementation, verification, recovery/retry, waiting, and redundant work. Explain which groups were necessary in context.
6. Compare models or harnesses only after showing sample sizes and task mix. Normalize correction counts per 100 user messages and label small or skewed samples as low confidence.
7. Look for successes as well as failures: one-pass completion, concise scope, good escalation, useful verification, and communication the user accepted without correction.
8. Map each supported recommendation to the narrowest future destination: global instruction, repository instruction, skill, deterministic script, tool/environment fix, or no change.
9. Produce the report using [Report template](references/report-template.md). Include traceable session identifiers or timestamps without exposing private content.

## Evidence standard

Rank a pattern only when examples share the same underlying behavior. Keep isolated expensive incidents visible, but do not present them as frequent. Explain alternative interpretations and confidence.

Do not claim causation from correlation between model identity and outcomes. Account for task difficulty, prompt quality, repository familiarity, tool availability, and instruction changes.

## Completion

Finish with prioritized findings, representative evidence, denominators, confidence, and proposed experiments. Do not update `AGENTS.md`, `CLAUDE.md`, or any skill; hand those proposals to `tune-agent-instructions` only when the user asks for changes.
