---
name: prune-worktrees
description: "Audit local git worktrees and remove the ones whose work is already merged or abandoned. Use when the user asks which worktrees to drop, wants to clean up or prune worktrees, or has too many worktrees."
---

# Prune Worktrees

Classify every linked worktree as **drop** or **keep**, show the evidence, and remove only after the user approves the list. Work from the main checkout. The scripts are bash and read-only.

## 1. Audit

```bash
<skill-dir>/scripts/audit.sh [base-branch]
```

It prints one TSV row per linked worktree:

| Column | Meaning |
| --- | --- |
| `dirty` / `untracked` | Uncommitted tracked changes and untracked files. The count skips ignored files. |
| `in_<base>` | `yes` when HEAD is an ancestor of `origin/<base>`, so every commit is already on the base branch. |
| `pr` | `#number:STATE:tip=same\|differs` for PRs whose head is this branch. `tip=same` means the local branch matches the PR's last pushed commit. |
| `remote` | Remote branches that contain HEAD, filled only when `in_<base>` is `no` and there is no PR. |

The audit is complete when every row has a verdict.

## 2. Classify

**Drop** a worktree when `dirty` and `untracked` are both 0 and one of these holds:

- `in_<base>` is `yes`.
- The PR is `MERGED` with `tip=same`. Squash merges never make HEAD an ancestor of the base branch, so `tip` is the check.
- A detached HEAD or PR-less branch whose `remote` branch belongs to a merged PR. Find the PR with `gh pr list --head <remote-branch> --state all`.
- The commits were never pushed, but the same subjects appear in a merged PR's commits (`git log <pr-head-oid>`). This is a rebased copy that the PR replaced.

**Keep** everything else, and say why: uncommitted changes, an open PR, `tip=differs` (local commits that were never pushed), or work you cannot trace to anything merged. A worktree with uncommitted changes is always the user's decision, however old.

## 3. Check scratch files

For each drop candidate, list ignored files that look hand-written:

```bash
<skill-dir>/scripts/scratch.sh <worktree-path>
```

The audit ignores these files, and `git worktree remove --force` deletes them. Name the ones that look like notes, scripts, or data (`tmp/*.md`, `*.rb`, `*.json`) in the report so the user can save them first.

## 4. Report and wait

Present two lists, **Drop** and **Keep**, with one line of evidence per worktree: the merged PR number, `in_<base>`, or the reason to keep. Group worktrees that share a reason. Mention the scratch files. Then stop until the user approves the drop list.

## 5. Remove

For each approved worktree:

1. Record the branch with `git -C <path> symbolic-ref --short -q HEAD`. It is empty for a detached HEAD.
2. Run `git worktree remove --force <path>`. Use `--force` only because step 3 already reviewed the ignored files.
3. Delete the recorded branch with `git branch -D <branch>`. `-D` is needed because squash-merged branches are not ancestors of the base branch.

Finish with `git worktree prune` and `git worktree list`. Report the counts removed and kept, and list any removal that failed. Leave remote branches alone.

Under zsh, `for f in $files` does not split words. Loop with `while read -r` or a bash script.
