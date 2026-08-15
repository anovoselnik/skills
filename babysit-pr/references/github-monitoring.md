# GitHub monitoring reference

Use a connected GitHub integration for ordinary metadata when it exposes the needed fields. Use `gh` for exact current-head check state, review-thread resolution state, and inline replies when connector coverage is incomplete.

## Resolve the pull request

For a number, resolve the current repository first:

```bash
gh repo view --json nameWithOwner --jq .nameWithOwner
```

For a branch with no supplied number:

```bash
gh pr view --json number,url
```

Fetch the state used by the monitoring baseline:

```bash
gh pr view <PR> --repo <OWNER/REPO> \
  --json number,url,title,body,state,isDraft,mergeStateStatus,reviewDecision,headRefName,headRefOid,headRepositoryOwner,baseRefName,commits,statusCheckRollup,reviews,comments
```

Refetch `headRefOid` before posting a conclusion or modifying code. A result associated with an older OID is stale.

## Fetch unresolved review threads

REST review comments do not expose thread resolution reliably. Use GraphQL and paginate:

```bash
gh api graphql --paginate -f query='
  query($owner:String!, $repo:String!, $num:Int!, $endCursor:String) {
    repository(owner:$owner, name:$repo) {
      pullRequest(number:$num) {
        reviewThreads(first:100, after:$endCursor) {
          nodes {
            id
            isResolved
            isOutdated
            comments(first:100) {
              nodes { databaseId author { login } body path line createdAt url }
            }
          }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
  }
' -F owner=<OWNER> -F repo=<REPO> -F num=<PR>
```

Also fetch issue conversation comments and review bodies because requests can appear outside inline threads:

```bash
gh api repos/<OWNER>/<REPO>/issues/<PR>/comments --paginate
gh api repos/<OWNER>/<REPO>/pulls/<PR>/reviews --paginate
```

Ignore walkthrough summaries, duplicate bot stubs, self-authored status comments, resolved threads, and findings that no longer apply. Do not ignore an older unresolved thread merely because a push happened; verify it against the current head first.

## Inspect checks for the current head

```bash
gh pr checks <PR> --repo <OWNER/REPO> \
  --json name,state,bucket,link,workflow

gh run list --repo <OWNER/REPO> --commit <HEAD_OID> \
  --json databaseId,name,workflowName,status,conclusion,url

gh run view <RUN_ID> --repo <OWNER/REPO> --log-failed
```

Classify failures before editing:

- **Repository:** the current change or existing base code deterministically fails.
- **Infrastructure:** runner outage, rate limit, network failure, external service failure, cancellation, or nondeterministic platform error without repository evidence.
- **Stale:** the check belongs to an older head OID.
- **Expected:** optional or explicitly non-blocking check whose result does not affect readiness.

Retry an infrastructure failure only when repository policy permits it. Do not modify code to appease an infrastructure flake.

## Reply and resolve

Reply to an inline review comment:

```bash
gh api -X POST repos/<OWNER>/<REPO>/pulls/<PR>/comments \
  -f body='<BODY>' -F in_reply_to=<COMMENT_DATABASE_ID>
```

Resolve a bot thread after replying:

```bash
gh api graphql -f query='
  mutation($id:ID!) {
    resolveReviewThread(input:{threadId:$id}) {
      thread { isResolved }
    }
  }
' -F id=<THREAD_NODE_ID>
```

Use a short attribution header for agent-authored replies:

```markdown
**Agent response** — `<harness>/<model-or-unknown>`, acting on behalf of `<user-or-PR-author>`

<Evidence-backed reply>
```

Never invent a model slug. Replies should state the fix and pushed commit, counter-evidence, or explicit scope decision. Avoid apologies, filler, and hidden reasoning.

## Base drift and obsolescence

Fetch the base branch before resolving conflicts. Prefer the repository's normal update strategy. A merge from the base is safer than rewriting shared history; rebasing requires explicit force-push authorization.

Search open pull requests and recent base changes when overlapping work is suspected. Compare affected behavior and files, not only titles. If another pull request fully supersedes this one, stop and ask before closing.
