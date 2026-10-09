#!/usr/bin/env bash
# Audit every linked worktree of the current repository. Read-only.
# Usage: audit.sh [base-branch]   (default: the remote's HEAD branch, else main)
set -uo pipefail

root=$(git rev-parse --path-format=absolute --git-common-dir | sed 's|/\.git$||')
cd "$root" || exit 1
base=${1:-$(git symbolic-ref --short -q refs/remotes/origin/HEAD | sed 's|^origin/||')}
base=${base:-main}
git fetch -q origin "$base" 2>/dev/null
have_gh=$(command -v gh >/dev/null && gh auth status >/dev/null 2>&1 && echo 1)

printf 'worktree\tbranch\tdirty\tuntracked\tin_%s\tage\tpr\tremote\n' "$base"
git worktree list --porcelain | awk '
  /^worktree /{p=substr($0,10)} /^branch /{print p"\t"substr($2,12)} /^detached/{print p"\t-"}' |
while IFS=$'\t' read -r path branch; do
  [ "$path" = "$root" ] && continue
  if [ ! -d "$path" ]; then printf '%s\t%s\tMISSING\n' "$path" "$branch"; continue; fi
  status=$(git -C "$path" status --porcelain)
  dirty=$(awk 'NF && !/^\?\?/' <<<"$status" | wc -l | tr -d ' ')
  untracked=$(grep '^??' <<<"$status" | wc -l | tr -d ' ')
  head=$(git -C "$path" rev-parse HEAD)
  in_base=$(git merge-base --is-ancestor "$head" "origin/$base" && echo yes || echo no)
  age=$(git -C "$path" log -1 --format=%cr)

  pr=-
  if [ -n "$have_gh" ] && [ "$branch" != - ]; then
    # tip=same means the local branch has nothing beyond the PR's last pushed commit.
    pr=$(gh pr list --head "$branch" --state all --json number,state,headRefOid \
      --jq "map(\"#\\(.number):\\(.state):tip=\\(if .headRefOid == \"$head\" then \"same\" else \"differs\" end)\") | join(\",\")")
    pr=${pr:--}
  fi

  # Only useful when nothing else explains the commit: a detached HEAD or a branch with no PR.
  remote=-
  [ "$in_base" = no ] && [ "$pr" = - ] && remote=$(git branch -r --contains "$head" 2>/dev/null | grep -v 'mq-bot\|/HEAD' | head -2 | tr -d ' ' | paste -sd, -)
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$path" "$branch" "$dirty" "$untracked" "$in_base" "$age" "$pr" "${remote:--}"
done
