---
name: comment-triage
description: Triage all review comments on a GitHub PR (CodeRabbit and human), verify each against the actual source, and produce a report with a verdict (address, skip, or discuss), a value assessment, and a concrete plan per comment. For skipped CodeRabbit comments, draft replies and, after one bulk approval, post them and resolve the threads. Never auto-reply to human reviewers or change project code. The only permitted mutations are approved CodeRabbit replies and thread resolutions. Use when the user says "comment-triage," asks to triage PR comments or CodeRabbit feedback, asks what is worth fixing on a PR, or provides a PR URL or number and asks which review comments to address.
---

# Comment Triage

## Resolve the pull request

Accept a pull request URL or bare number. For a bare number, resolve the repository from the current directory:

```bash
gh repo view --json nameWithOwner --jq .nameWithOwner
```

If repository resolution fails and the user did not provide a URL, ask for the repository.

Never edit project code, commit, or push. Deliver (1) the triage report and (2) replies and resolved threads for skipped CodeRabbit comments, but only after bulk approval. These approved replies and resolutions are the workflow's only permitted mutations.

## Fetch all review context

Run these requests in parallel where possible:

```bash
# Inline review comments, including file, line, and threading metadata
gh api repos/<OWNER>/<REPO>/pulls/<NUMBER>/comments --paginate

# Conversation timeline comments
gh api repos/<OWNER>/<REPO>/issues/<NUMBER>/comments --paginate

# Review bodies, including CodeRabbit nitpick batches in collapsed sections
gh api repos/<OWNER>/<REPO>/pulls/<NUMBER>/reviews --paginate

# Pull request metadata and diff
gh pr view <NUMBER> --repo <OWNER>/<REPO> \
  --json title,url,author,headRefName,headRefOid,headRepository,headRepositoryOwner,baseRefName,body,isCrossRepository
gh pr diff <NUMBER> --repo <OWNER>/<REPO>

# Thread node ID and state, keyed by the first comment database ID
gh api graphql --paginate -f query='
  query($owner:String!, $repo:String!, $num:Int!, $endCursor:String) {
    repository(owner:$owner, name:$repo) {
      pullRequest(number:$num) {
        reviewThreads(first:100, after:$endCursor) {
          nodes {
            id
            isResolved
            isOutdated
            comments(first:1) {
              nodes { databaseId author { login } body }
            }
          }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
  }
' -F owner=<OWNER> -F repo=<REPO> -F num=<NUMBER>
```

Also fetch the current user's login so self-authored comments can be filtered:

```bash
gh api user --jq .login
```

Read a file locally only when the current repository and `HEAD` OID match the pull request head and that file has no worktree changes. Otherwise read the raw file at `headRefOid`:

```bash
gh api -H 'Accept: application/vnd.github.raw+json' \
  'repos/<HEAD_OWNER>/<HEAD_REPO>/contents/<PATH>?ref=<HEAD_OID>'
```

### Filter triage items

- Drop comments authored by the current user, CodeRabbit walkthrough or summary posts, "Actionable comments posted" review stubs, CI bot comments, and already-resolved threads. Summarize resolved items in one line at the end instead of triaging them.
- Keep every unresolved inline thread and every conversation comment that requests action.
- Expand CodeRabbit review bodies containing collapsed `<details>` nitpick sections and triage each nitpick separately. Report `Address`, `Discuss`, and non-`None` `Skip` items individually; summarize the remaining `None`-value nitpicks in one line because they have no thread to resolve.
- Flag outdated threads (`isOutdated: true`) and verify them against the current source. The concern may already be moot.

Treat `coderabbitai[bot]` and `coderabbitai` as CodeRabbit logins. Treat every other reviewer as human unless it is clearly another bot.

## Verify each comment against the source

Never trust a comment's premise or severity label. For every item, read the complete relevant source files, not only the diff hunk. Verify call sites, validations, framework guarantees, related pull request discussion, and existing implementations elsewhere in the codebase.

Treat CodeRabbit emoji prefixes such as `Potential issue`, `Refactor suggestion`, and `Nitpick` as hints, not verdicts.

Assign each comment:

- **Verdict:** `Address`, `Skip`, or `Discuss`. Use `Discuss` when the decision requires author input, product judgment, or missing context.
- **Value:** `High`, `Medium`, `Low`, or `None`, with one sentence weighing impact against effort.
  - `High`: real bug, security issue, data-integrity risk, or performance problem on a hot path.
  - `Medium`: correctness hardening or maintainability work with a clear payoff.
  - `Low`: style or marginal polish.
  - `None`: wrong, moot, or out of scope.
- **Plan:** For `Address`, name the file, the change, and how to verify it.
- **Draft reply:** For `Skip` comments authored by CodeRabbit, draft a reply as described below.

Do not mark a comment `Skip` as wrong without source evidence. Use `Discuss` when confidence is below 90 percent.

## Draft replies for skipped CodeRabbit comments

Draft a reply for every skipped CodeRabbit inline thread so the resolution remains auditable. Keep each reply factual and one or two sentences. State the counter-evidence, framework guarantee, or scope decision. Avoid apologies and filler.

Examples:

> Not an issue — `account_id` is validated as non-null in `app/models/foo.rb:12`, and the controller scopes the query by `current_account`.

> Intentional — this mirrors the pattern in `BarJob`; consistency has more value here than the proposed micro-optimization.

> Out of scope for this PR — tracked as a follow-up in [TICKET].

Human-authored comments can receive any verdict and belong in the matching report section. Never draft, post, or resolve a reply for a human reviewer. For `Skip` or `Discuss`, provide a short suggested angle so the user can respond.

## Present the report

Present the complete report before requesting approval:

```markdown
## Comment Triage: <repo>#<num> — <title>

<N> triaged (<X> CodeRabbit, <Y> human) · Address <A> · Skip <S> · Discuss <D>
Reply-ready: <R> skipped CodeRabbit inline threads
Skipped from triage: <M> resolved, <K> self/bot noise

### Address (<A>)

**1. coderabbitai — `app/models/foo.rb:42` — Potential issue**
> <quoted comment, trimmed>

**Value: High** — <impact versus effort, one line>
**Plan:** <file, change, verification>

### Skip (<S>)

**2. coderabbitai — `spec/foo_spec.rb:10` — Nitpick** _(outdated)_
> <quoted comment, trimmed>

**Value: None** — <why it is wrong or moot, one line>
**Reply:**
> <draft reply>

### Discuss / Yours to answer (<D>)

**3. <human> — `app/services/bar.rb:7`**
> <quoted comment>

**Value: Medium** — <analysis>
**Suggested angle:** <what to say or decide, one line>
```

Order items within each section from highest to lowest value.

## Request bulk approval

Ask one question: **"Post <R> replies to skipped CodeRabbit inline threads and resolve them?"** Here, `<R>` excludes human comments, conversation comments, and review-body nitpicks that have no resolvable thread. Offer these choices when structured user input is available, or ask the same question in plain chat otherwise:

1. **Post all and resolve** — post every draft as written.
2. **Let me adjust first** — let the user identify items to change or omit, then confirm once more.
3. **Do not post** — stop after the report.

Do not post or resolve anything without explicit approval.

After approval, refetch the selected threads and pull request head. Omit threads that are now resolved, and re-verify drafts if the pull request head changed after the report. Then reply first and resolve second for every remaining skipped CodeRabbit inline thread:

```bash
# Reply in-thread
gh api -X POST repos/<OWNER>/<REPO>/pulls/<NUMBER>/comments \
  -f body='<REPLY>' -F in_reply_to=<COMMENT_DATABASE_ID>

# Resolve the review thread
gh api graphql -f query='
  mutation($id:ID!) {
    resolveReviewThread(input:{threadId:$id}) {
      thread { isResolved }
    }
  }
' -F id=<THREAD_NODE_ID>
```

Match each thread node ID to the first comment database ID from the earlier GraphQL query. If a request fails, report the affected thread and continue with the rest. Finish with a list of any replies that were not posted.

Close with a short recap of what was posted and resolved, followed by the `Address` items as the user's implementation to-do list. Do not implement those fixes as part of this skill.
