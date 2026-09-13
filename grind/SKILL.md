---
name: grind
description: Ships an ordered queue of GitHub issues through fresh Shipmate subagents, merging each PR and completing its issue before starting the next. Use when the user invokes grind or asks to implement and merge a batch of tickets one by one.
---

# Grind

Run one issue at a time: fresh Shipmate agent, verified merge, completed issue, then the next ticket. The parent owns the queue and merges; each child owns Shipmate through merge readiness.

## Execution scope

A request to run Grind authorizes delegation, Shipmate's implementation and publishing stages, normal merges of the resulting ready PRs, and marking the requested issues complete. Carry that authorization through the run without asking again at each stage. Shipmate's usual human merge handoff returns to the parent, which executes the already-requested merge.

Apply explicit user limits first and pass them to every child. A planning request performs no execution. For an earlier endpoint such as "keep it local," "do not merge," or "skip monitoring," follow Shipmate's applicable stages for the first unfinished issue, then report the remaining queue as pending. Automatic merging requires monitoring. Deployment, force-pushing, bypassing branch protections, and repository settings changes are outside this workflow.

## Prepare the queue

1. Resolve the repository and intended base from the request and checkout. Accept issue URLs, an ordered list, or an inclusive range such as `#64–#75`. Expand ranges, remove duplicates while preserving order, and fetch every entry to verify it is an issue in the selected repository. Surface missing issues or PR numbers before starting implementation. Preserve the supplied order; a dependency requiring a different order is a blocker unless the user permits reordering.
2. Resolve `shipmate` and the skills needed for the selected stages from the skill catalog, host's local skill directories, or siblings in this checkout. Read Shipmate and let it own its stage instructions. A full Grind run requires `implement`, `file-pr`, and `babysit-pr`, including monitoring even though standalone Shipmate permits its absence. Verify GitHub access and a supported way to start a child without inherited conversation history. If a required capability is missing, report the specific blocker before execution; do not silently substitute an inline Shipmate run.
3. Inspect applicable repository guidance, worktrees, existing PRs, and issue completion conventions. Preserve unrelated local work. Create a durable, untracked progress record, for example `grind/<run-id>.md` under the absolute Git common directory. Record the repository, base, ordered queue, user limits and authorization, and each issue's status, worktree/branch, agent ID, PR URL, checked head, merge commit, completion state, and blocker as these become known. Report the record's path and update it at each transition.

## Process the current issue

Complete these steps for the first unfinished issue before dispatching the next.

1. **Reconcile GitHub state.** Read the issue, relevant discussion, dependencies, and linked PRs. Reuse an existing open PR for the same work. If its implementation is already merged, verify scope and finish the completion step below. A closed issue alone is not evidence of shipped work; canceled, duplicate, or otherwise unimplemented issues need a disposition from the user. Inspect a closed unmerged PR before choosing a fresh branch for remaining work.
2. **Prepare its checkout.** Fetch the intended base after the preceding merge. For new work, create a dedicated worktree and topic branch from that current remote base. For an existing PR, use its head in a safe worktree and let Shipmate reconcile base drift. Give the child an explicit working directory; fresh conversation context does not isolate the filesystem.
3. **Dispatch a fresh child.** Start a new subagent with no conversation-history fork (`fork_turns="none"` when supported). Supply only the current issue's brief, relevant constraints, and the handoff below. Reuse that child for fixes to this issue; create a different child for the next issue. One issue worker may be active at a time; Shipmate can still delegate its own bounded reviews.
4. **Wait through Shipmate.** Keep the parent active using the host's supported wait or recurring mechanism and communicate progress at least every 60 seconds. A created PR or a quiet CI interval is an intermediate state. Follow up with the same child on missing evidence or verified in-scope blockers. If it exits unexpectedly, reconcile remote state before resuming or replacing it, and ensure the old worker is stopped before another writes to its branch.
5. **Verify readiness independently.** Refetch the PR and compare its repository, base, scope, and current head with the child's handoff. Require a non-draft PR, successful current-head required checks, required approvals, no conflicts, and no actionable unresolved review feedback. Use `babysit-pr` to resolve uncertainty; missing monitoring, pending approvals, or unknown mergeability are not readiness. If the head or base changed, return to monitoring and validation before attempting the merge.
6. **Merge the verified revision.** Use the repository's normal permitted merge method and a head precondition, such as `gh pr merge <url> --match-head-commit <verified-head> <method>`. Follow existing repository conventions when choosing the method. A stale-head rejection returns to readiness checks. With auto-merge or a merge queue, wait until GitHub actually reports the PR merged; enabling or enqueueing a merge is not completion. Reconcile GitHub state before retrying an uncertain merge result.
7. **Complete the issue.** Verify the PR's merged state and merge commit. Prefer the PR's closing reference to complete the issue automatically; if it remains open and the merged work meets its acceptance criteria, close it as completed. Verify the issue is closed with the completed reason. If the user's requested "Done" maps to an existing project status or repository convention, apply and verify that state too; discover the actual field rather than inventing labels or changing unrelated boards. If tracking cannot be updated, record the merged PR and the completion blocker without starting the next issue.
8. **Advance.** Record the verified PR, merge commit, and issue completion. Release the finished child, fetch the updated base, and start the next unfinished issue automatically. Retain worktrees with uncommitted or unpushed work; cleanup must not discard evidence needed to resume.

## Child handoff

Provide concrete values for this brief, adapting the authorized stages and endpoint to the user's limits and keeping other tickets' history out of the child's context:

```text
Run $shipmate using <resolved SKILL.md> for <issue URL> only.
Repository: <owner/repo>; worktree: <absolute path>.
Branch: <topic branch>; intended base: <base branch and fetched commit>.
Task: <issue text, acceptance criteria, relevant discussion/dependencies>.
Guidance: <applicable repository instruction paths>.
Existing PR, if any: <verified URL and current head>.
User limits and decisions: <applicable instructions>.
Authorized stages and endpoint: <selected Shipmate stages after applying limits>.

Complete the authorized Shipmate stages. When publishing, include a closing
reference for this issue if its scope is fully satisfied.
The parent owns merging, issue completion, and dispatching the next ticket.
Return the PR URL, current head and base commits, acceptance-criteria coverage,
verification results, checks/approvals, review disposition, and any blocker.
```

## Blockers, resumption, and completion

Keep repairing verified in-scope failures through Shipmate. Pause the queue when progress needs user or maintainer input, unavailable permissions, an unresolved dependency, or a product decision. Report the current issue, evidence, work already merged, remaining queue, and the precise input needed. Do not skip a blocked issue or lower merge requirements to finish the batch.

On resumption, read the progress record and reconcile issue, PR, and branch state with GitHub before any mutation. Reattach to a live worker when possible; otherwise resume the unfinished issue in a fresh child. Previously verified completed issues need no new PR. A record is a checkpoint, not proof that remote state is unchanged.

Finish only when every requested issue has a verified merged implementation and verified completion state, or the user chose an earlier endpoint. Return a compact issue-to-PR table with merge commits and completion states; distinguish full completion from a paused or intentionally shortened run. Describe monitoring as active only while the session or a supported recurring mechanism is running.

## Examples

- `$grind #64–#75` ships that inclusive range in the current repository.
- `$grind #18, #21, #19 in owner/repo` preserves that explicit order.
- `Resume Grind from <progress-record path>` reconciles state and continues the unfinished queue.
- `Plan a Grind for #64–#75` prepares a plan without starting workers or changing GitHub.
