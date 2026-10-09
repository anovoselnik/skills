#!/usr/bin/env bash
# List ignored files in a worktree that look hand-written (notes, scripts, data),
# skipping dependency, build, cache, and generated secret files. Read-only.
# Usage: scratch.sh <worktree-path>
set -uo pipefail
cd "$1" || exit 1
git status --porcelain --ignored --untracked-files=all |
  sed -n 's/^!! //p' |
  grep -vE '(^|/)(node_modules|\.bundle|vendor/bundle|dist|build|coverage|public/vite[^/]*|storage|\.ruby-lsp|\.husky/_|test-results|playwright-report|\.next|\.turbo|__pycache__|__generated__)/' |
  grep -vE '(^|/)(log/|tmp/(cache|pids|sockets|storage)/)' |
  grep -vE '(\.log$|\.eslintcache$|\.tsbuildinfo$|\.DS_Store$|/\.keep$|tmp/development_[^/]*\.txt$|tmp/local_secret\.txt$|tmp/restart\.txt$)'
