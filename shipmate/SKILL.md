---
name: shipmate
description: Carries a coding task through implementation, pull request creation, and review and CI monitoring. Use when the user invokes shipmate or asks to implement work, open its PR, and babysit it through merge readiness.
---

# Shipmate

Take the supplied task, spec, or tickets through `implement`, `file-pr`, and `babysit-pr`, in that order. Keep the original task as the scope boundary throughout.

## Execution scope

A request to execute Shipmate includes implementation, verification, review, scoped commits, normal pushes, PR creation, and in-scope fixes and factual PR replies during babysitting. Continue between stages without asking for authorization already supplied by the user. Explicit limits such as "plan only," "keep it local," or "skip monitoring" override the default workflow.

The default endpoint is a PR ready for a human merge decision. Merging, deployment, closing the PR, force-pushing, and repository settings changes require separate user direction.

## Resolve the skills

Check availability of the skills needed for the user's selected stages before execution. Prefer their entries in the current skill catalog; if absent, look in the host's local skill directories or sibling directories in this skills checkout. Read each resolved `SKILL.md` when entering its stage, including references required by that stage. Reuse its instructions rather than duplicating its workflow here.

`implement` and `file-pr` are required for their respective stages. If a required skill is unavailable, identify it before starting execution; omitted stages need no dependencies. `babysit-pr` is optional: if unavailable, complete implementation and publishing, then report the PR URL and that monitoring did not run. Never claim to have used a missing skill.

## Workflow

1. Establish the requested outcome and acceptance criteria from the user's task. Resolve the repository, applicable guidance, worktree state, topic branch, and intended base. Preserve unrelated work. Keep this context and the verification results available across all stages.
2. Run `implement` with the task and branch context. Its completion criteria must be satisfied before publishing; carry unresolved blockers back to the user. An explicit request for a draft PR may authorize publishing incomplete work with its blockers disclosed.
3. Run `file-pr` with the original goal, intended diff, branch and base, commits, and verification results. Creating the PR is an intermediate milestone. Reuse an existing open PR for the intended work. If the branch's PR was closed or merged, inspect its disposition before publishing; establish a fresh topic branch for remaining work instead of reopening or duplicating the old PR automatically.
4. Pass the verified PR URL and current head commit to `babysit-pr` when available and monitoring is within the user's requested scope. If `file-pr` already entered babysitting, continue that same monitoring loop. Do not start a second monitor or stop merely because the PR was created.
5. Follow `babysit-pr` through current-head CI, verified review feedback, and conflicts until its completion or escalation condition is reached. Required human approvals that remain unavailable are a blocker to report, not permission to invent an approval or claim readiness. Use the host's supported wait or recurring mechanism; describe monitoring as active only while that mechanism or the session is running.

## Handoff

Return the PR URL, current head commit, work completed, checks and approvals, and any remaining blocker. Distinguish a merge-ready PR from one awaiting a human decision or one published without monitoring. For an explicit earlier stopping point, report the completed stage and its result instead.

## Examples

- "Shipmate issue #123" runs implementation, publishing, and available babysitting.
- "Shipmate this fix, but keep it local" completes implementation without pushing or opening a PR.
- "Plan how Shipmate would handle these tickets" produces a plan without executing the stages.
