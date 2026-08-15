# Placement and evaluation

## Choose the destination

### Global instructions

Use for durable preferences that should affect nearly every project:

- Communication style and collaboration posture.
- Read-only versus mutation expectations.
- Destructive-action and user-data boundaries.
- General verification philosophy.
- Delegation and worktree safety defaults.

Avoid framework commands, repository paths, product vocabulary, and temporary model workarounds.

### Repository instructions

Use for knowledge that makes changes in one codebase safer and more accurate:

- A short operational description of the product.
- A glossary matching the maintainer's domain language.
- Product qualities that changes must not compromise.
- Architecture boundaries and where code lives.
- Supported surfaces, providers, entry points, contracts, reverse actions, and documentation audiences.
- Exact commands and recurring environmental hazards.
- Proportional verification expected in that repository.

Do not repeat the README. Focus on what an agent must know before changing the code.

### Skills

Use when all are true:

- The workflow recurs.
- The user expresses a recognizable intent or trigger.
- Several ordered decisions or tool actions are required.
- Loading the procedure for unrelated tasks would waste context.

Split skills when trigger intent, authorization, lifecycle, or stopping conditions differ. Examples: filing a pull request versus monitoring it; auditing history versus editing instructions; reading an artifact versus publishing one.

### Scripts

Use for repeatable mechanics with objective inputs and outputs: parsing logs, validating schemas, formatting generated data, uploading artifacts, or checking configuration. Keep policy and judgment in the skill; keep deterministic work in the script.

### No persistent change

Choose no change when the event was isolated, caused by a uniquely ambiguous prompt, already covered by clear guidance, or unlikely to recur. A critical safety failure is the exception.

## Drafting heuristics

- Prefer direct positive behavior with an explicit boundary.
- Use the user's vocabulary and name concrete objects.
- Remove obsolete guidance when behavior or tools change.
- Avoid duplicated rules at multiple levels unless the narrower file adds necessary context.
- Keep defaults defeasible by explicit user requests.
- Use bad/good examples for taste, not for objective commands.
- Never put the full workflow in a skill description; make it easy to trigger.

## Scenario review

For each change, write expected behavior before evaluating:

1. **Failure replay:** the original situation now produces the desired behavior.
2. **Non-trigger:** a similar task outside the intended scope is unaffected.
3. **Override:** explicit user direction safely supersedes the default.
4. **Safety boundary:** destructive or external action remains appropriately gated, when relevant.

Check whether a plausible literal reading produces an unintended action. If so, tighten the boundary rather than adding more general prose.

## Diff review

Ask of every added line:

- Which observed failure or explicit preference justifies it?
- Is this the narrowest scope that can fix the behavior?
- Does an existing line already say it?
- Could it conflict with user intent or another instruction?
- Will it remain true when models and tools change?
- Can a script or clearer repository structure solve it more reliably?

Remove lines without a defensible answer.
