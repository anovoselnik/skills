---
name: kickoff-next-ticket
description: Picks the next ready GitHub or GitLab issue in the current repository, claims it, and starts it through Shipmate. Invoke explicitly with $kickoff-next-ticket.
disable-model-invocation: true
---

# Kickoff Next Ticket

Choose one ready issue, claim it, and hand it to Shipmate. This skill owns the choice; Shipmate owns everything after it.

## Execution scope

Invoking this skill authorizes choosing an issue, assigning it to the authenticated user, and running Shipmate on it with Shipmate's default scope. Pass explicit user limits such as "keep it local" or "skip monitoring" through to Shipmate. "What's next", "dry run", or "plan only" stop after the report in step 4: no claim, no Shipmate.

## 1. Resolve the forge

Read the `origin` remote. `github.com` or a host listed by `gh auth status` uses `gh`; `gitlab.com` or a host listed by `glab auth status` uses `glab`. Confirm the CLI is authenticated for that host and note the authenticated username. Resolve `shipmate` from the skill catalog, the host's local skill directories, or a sibling directory in this checkout. Stop and report if the forge, the CLI, or Shipmate is unavailable.

## 2. Gather candidates

List every open issue, paging until the list is exhausted:

- GitHub: `gh issue list --state open --limit 1000 --json number,title,url,body,assignees,labels,milestone,createdAt,blockedBy,closedByPullRequestsReferences,projectItems`
- GitLab: `glab issue list --opened --per-page 100 --page <p> --output json`, plus `glab mr list --opened --output json` for open merge requests.

A candidate is **ready** when all of these hold:

- Unassigned, or assigned only to the authenticated user.
- No open PR or MR claims it. On GitHub, check `closedByPullRequestsReferences` for an open PR; on GitLab, check `glab api projects/:id/issues/<n>/related_merge_requests` for an opened MR. Also match `#<n>` in open PR/MR titles and bodies.
- No label meaning blocked, waiting, on hold, duplicate, won't fix, question, or needs triage. Read the repository's label list to learn its vocabulary for these.
- No open dependency: GitHub `blockedBy`, GitLab `is_blocked_by` links (`glab api projects/:id/issues/<n>/links`), or "depends on #N" / "blocked by #N" in the body pointing at an open issue.

When the user names a filter (label, milestone, type, "next bug"), apply it before ranking.

## 3. Rank

Take the first rule that separates the candidates:

1. Assigned to the authenticated user ahead of unassigned.
2. The repository's own priority signal: priority labels (`P0`, `priority::high`, `critical`), a project board or iteration order, or the open milestone with the nearest due date. Discover which signal the repository uses; leave unused ones out.
3. Oldest first (lowest issue number).

The step is done when exactly one issue is chosen and every candidate it outranked is explained by a rule above.

## 4. Report the pick

Show the chosen issue's number, title, URL, and the rule that chose it, plus the next two candidates. If nothing is ready, list the open issues that were excluded grouped by reason and stop.

## 5. Claim and start

1. Assign the issue to the authenticated user (`gh issue edit <n> --add-assignee @me` or `glab issue update <n> --assignee +<username>`). If assignment is not permitted, note it and continue.
2. Read the full issue with its comments and pass Shipmate this brief:

   ```text
   Run $shipmate on <issue URL>.
   Repository: <owner/repo> on <GitHub|GitLab>.
   Task: <issue title, body, acceptance criteria, relevant discussion>.
   User limits: <limits from the invocation, or none>.
   Publish with a closing reference for this issue (`Closes #<n>`) when its scope is fully satisfied.
   ```

3. On GitLab, add to the brief: publish a merge request with `glab mr create`, applying `file-pr`'s scope and editorial rules to it; `babysit-pr` monitoring is GitHub-only, so Shipmate finishes after publishing and reports that monitoring did not run.

Shipmate's handoff is this skill's handoff. Return it with the chosen issue's number at the top.

## Examples

- `$kickoff-next-ticket` picks and starts the next ready issue in this repository.
- `$kickoff-next-ticket next bug in milestone v2` filters to bugs in that milestone first.
- `$kickoff-next-ticket dry run` reports the pick without claiming or starting it.
