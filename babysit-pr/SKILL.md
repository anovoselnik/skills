---
name: babysit-pr
description: Keeps a GitHub pull request merge-ready by monitoring current-head CI, review feedback, conflicts, and base-branch drift, then addressing verified in-scope blockers. Use when the user asks to monitor, watch, babysit, shepherd, or keep a pull request green.
---

# Babysit PR

Keep the pull request current until it is ready for a human merge decision. Treat the user's original goal as the scope boundary.

## Boundaries

A babysitting request authorizes normal in-scope branch fixes, commits, pushes, and factual pull request replies needed to make the pull request merge-ready. It does not authorize merging, closing, force-pushing, changing repository settings, or broadening the feature. Preserve unrelated worktree changes.

Identify agent-authored replies. Include the harness and model only when known; never guess them. Do not resolve a human review thread unless the reviewer or repository convention clearly permits it.

When a more specific CI, review-comment, or branch-management skill is available, reuse it for that bounded subworkflow. This skill still owns freshness, scope, monitoring, and termination; respect any stricter mutation boundary in the specialized skill.

## Workflow

1. Resolve the repository and pull request from a URL, number, or current branch. Confirm the pull request is open and record its goal from the user's request, title, body, linked issue, and diff.
2. Record a baseline: head OID, latest commit time, base branch and OID, draft state, merge state, required approvals, checks, and unresolved review threads. Read [GitHub monitoring](references/github-monitoring.md) when exact CLI or GraphQL calls are needed.
3. Find or create a safe checkout of the head branch. Inspect `git status` before changing anything. Never overwrite a dirty worktree or check out over unrelated user changes.
4. On the first pass, triage every unresolved finding that still applies to the current source. After any push, ignore check results for older head OIDs and re-evaluate old comments against the new source before acting.
5. Verify each finding against complete relevant files, call sites, tests, and framework guarantees. A bot's premise and severity are hints, not facts.
6. Classify each blocker:
   - **Fix:** real, reproducible, and within the original goal.
   - **Explain:** false, obsolete, or intentionally out of scope; leave concise evidence.
   - **Retry:** infrastructure or service flake with no repository cause.
   - **Escalate:** ambiguous product, design, security, or compatibility decision.
7. Reproduce repository failures with the narrowest useful command, fix the cause, and run proportional verification. Group related fixes into intentional commits and push normally.
8. Watch base-branch drift and conflicts. Follow repository update conventions. Do not rewrite shared history; ask before a rebase that requires a force-push.
9. After every external update, refetch the pull request. If its head changed, discard stale conclusions and restart from the new baseline.

## Monitoring loop

Use the harness's recurring monitor or wait mechanism when available. Otherwise poll in bounded intervals and keep the user informed at least every 60 seconds while actively working. An unchanged state is expected, not a reason to stop.

Continue until one of these conditions holds:

- Current-head required checks pass, required approvals exist, conflicts are absent, and no actionable threads remain.
- The same blocker persists after evidence-backed attempts and needs user or maintainer input.
- Another change makes the pull request obsolete. Report the overlap and ask before closing it.
- The user stops monitoring.

Never let review feedback turn the pull request into a different project. Report worthwhile follow-ups separately.

## Handoff

Finish with the pull request URL and current head OID, changes pushed, comments answered, checks and approvals, base-branch status, and any remaining blocker. Do not merge unless the user separately asks.
