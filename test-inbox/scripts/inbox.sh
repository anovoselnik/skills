#!/usr/bin/env bash
# Disposable test inboxes on testmail.app. Reads TESTMAIL_NAMESPACE and
# TESTMAIL_API_KEY from the skill's .env.
#
# Usage:
#   inbox.sh new [label]                 print a fresh address and its tag
#   inbox.sh wait <tag> [timeout-secs]   wait for the newest email, print it and its links
#   inbox.sh links <tag>                 print the links in the newest email
#   inbox.sh list [tag-prefix]           list recent emails
set -euo pipefail

case "${1:-}" in
  new|wait|links|list) ;;
  *) sed -n '5,9p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac

skill_dir=$(dirname "$(dirname "$(readlink -f "$0")")")
if [ -f "$skill_dir/.env" ]; then
  set -a; . "$skill_dir/.env"; set +a
fi
: "${TESTMAIL_NAMESPACE:?missing; set it in $skill_dir/.env}"
: "${TESTMAIL_API_KEY:?missing; set it in $skill_dir/.env}"

api() {
  curl -sS -L --get "https://api.testmail.app/api/json" \
    --data-urlencode "apikey=$TESTMAIL_API_KEY" \
    --data-urlencode "namespace=$TESTMAIL_NAMESPACE" "$@" |
    jq -e 'if .result == "success" then . else error(.message // "request failed") end'
}

# URLs from the text and HTML bodies, minus sentence punctuation, with &amp; decoded.
links_of() {
  jq -r '.emails[0] | (.text // ""), (.html // "")' |
    grep -oE 'https?://[^][[:space:]"<>'"'"')]+' |
    sed 's/[.,;:!?]*$//; s/&amp;/\&/g' | awk '!seen[$0]++' || true
}

cmd=$1; shift
case "$cmd" in
  new)
    label=$(printf '%s' "${1:-test}" | tr 'A-Z' 'a-z' | tr -c 'a-z0-9-' '-' | sed 's/^-*//; s/-*$//')
    tag="${label:-test}-$(date +%s)-$RANDOM"
    printf 'address\t%s.%s@inbox.testmail.app\ntag\t%s\n' "$TESTMAIL_NAMESPACE" "$tag" "$tag"
    ;;
  wait)
    tag=${1:?usage: inbox.sh wait <tag> [timeout-secs]}
    timeout=${2:-120}
    # livequery answers as soon as one email matches; curl follows the API's
    # 307 retries, and --max-time bounds the whole wait.
    if ! res=$(api --max-time "$timeout" --max-redirs 1000 \
      --data-urlencode "tag=$tag" --data-urlencode "livequery=true" --data-urlencode "limit=1"); then
      echo "no email for tag '$tag' within ${timeout}s" >&2
      exit 1
    fi
    jq -r '.emails[0] | "from\t\(.from)\nsubject\t\(.subject)\nreceived\t\(.timestamp / 1000 | todate)\n\n\(.text // "(no text body)")"' <<<"$res"
    printf '\nlinks:\n'
    links_of <<<"$res"
    ;;
  links)
    tag=${1:?usage: inbox.sh links <tag>}
    api --data-urlencode "tag=$tag" --data-urlencode "limit=1" | links_of
    ;;
  list)
    args=(--data-urlencode "limit=20")
    [ -n "${1:-}" ] && args+=(--data-urlencode "tag_prefix=$1")
    api "${args[@]}" |
      jq -r '.emails[] | [(.timestamp / 1000 | todate), .tag, .from, .subject] | @tsv'
    ;;
esac
