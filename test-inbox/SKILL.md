---
name: test-inbox
description: "Gives the agent its own email inboxes on testmail.app for testing flows that send email. Use when testing sign-up, invitations, set-password or password-reset emails, email verification, OTP codes, or any flow that needs a real address the agent can read."
---

# Test Inbox

Every address `<namespace>.<tag>@inbox.testmail.app` delivers to one testmail.app inbox, and the script reads it through the JSON API. Tags need no setup, so use a fresh one per test user. That way an app that refuses duplicate emails never blocks you, and each wait sees only that user's mail.

## Setup

The script reads `TESTMAIL_NAMESPACE` and `TESTMAIL_API_KEY` from `<skill-dir>/.env`, which is gitignored. `.env.example` lists the keys. If either is missing, the script says so; ask the user to fill in `.env`. Never ask for the key in chat, print it, or copy it into another repo.

## Commands

```bash
<skill-dir>/scripts/inbox.sh new [label]                # address and tag for a new test user
<skill-dir>/scripts/inbox.sh wait <tag> [timeout-secs]  # wait (default 120s), print the newest email and its links
<skill-dir>/scripts/inbox.sh links <tag>                # links in the newest email, no waiting
<skill-dir>/scripts/inbox.sh list [tag-prefix]          # 20 most recent emails
```

`label` names the test, e.g. `cleangor-cleaner`. `new` adds a timestamp to make the tag unique.

## Flow

1. Run `new`, and use the address wherever the app asks for an email.
2. Trigger the email in the app, then run `wait <tag>`. It returns as soon as one email matches the tag, including emails that arrived before the call.
3. Open the link or read the code from the output, and continue the flow in the browser or through the API.
4. To catch a second email for the same tag (e.g. a resend), note the `received` time of the first one, then poll `list <tag>` until a newer row appears.

If nothing arrives, check whether the app actually sent anything (server logs, a provider dashboard) before blaming the inbox. Some environments skip sending or reject unfamiliar domains. Report that as a finding instead of switching to a personal address.

Test emails are deleted after the plan's retention period (1 day on the free tier), so record what you need in the report.
