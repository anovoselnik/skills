---
name: implement
description: Implements a supplied task, spec, or tickets through testing, review, and commit. Use when the user asks to implement defined work or another workflow needs its implementation stage completed.
---

# Implement

Turn the supplied task into verified, reviewed changes and commit within the user's requested scope. The user's instructions and repository guidance govern the work.

## Workflow

1. Read the task and applicable repository guidance. Identify acceptance criteria, relevant code, and required checks. Use the conversation as the spec when no separate document exists. Resolve routine choices from context; ask only about decisions that block correct implementation.
2. Inspect the worktree and branch. Preserve unrelated changes, choose a topic branch when needed, and record the starting commit for review. Carry any branch and base already established by the calling workflow forward.
3. Implement the complete requested behavior. Use the available `tdd` skill where appropriate, honoring any agreed test seams and repository requirements.
4. Run focused tests and relevant typechecking during implementation. Cover affected behavior and failure cases, and fix failures attributable to the change.
5. Review all intended changes with the available `code-review` skill. Supply the recorded starting commit as the fixed point and the original task as the spec. If that skill requires a committed diff and commits are within scope, make a scoped checkpoint commit first. When the user requests uncommitted changes, review the complete working-tree diff directly without checkpointing. Without the skill, review the complete diff against the task and repository standards directly.
6. Address verified review findings and rerun affected checks. Run the required full test suite once after the final changes; repeat only if subsequent edits or failures justify it. Record checks that could not run and their impact.
7. Commit the intended work using repository conventions, unless the user requested uncommitted changes. Inspect the final diff and status to ensure all requested work is accounted for and unrelated changes are preserved.

## Completion and handoff

Implementation is complete when acceptance criteria are met, review findings are addressed, and required verification passes. If that is blocked, report the precise remaining requirement rather than claiming completion.

Return the task scope, repository, branch, base or starting commit, resulting commits or uncommitted changes, verification results, and limitations to the calling workflow. Continue its next authorized stage without asking for the same authorization again. When invoked on its own, finish after this implementation handoff; publishing and monitoring belong to the caller or a separate user request.
