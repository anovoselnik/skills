---
name: file-pr
description: Publishes the current branch as a concise, review-ready GitHub pull request whose title and body explain why the change matters. Use when the user asks to file, open, create, raise, or publish a pull request.
---

# File PR

Publish exactly the work the user requested and make the pull request easy to evaluate.

## Workflow

1. Resolve the repository, current branch, remote, and default base branch. Read all applicable contribution guidance and pull request templates. Do not open a pull request from the default branch; create a topic branch when the intended changes are clearly owned, or stop if the branch choice is ambiguous.
2. Check whether an open or closed pull request already exists for the head branch. Never create a duplicate; report or update the existing pull request as appropriate.
3. Reconstruct the goal from the user's original request and the completed conversation. Compare it with:
   - `git status`
   - the complete diff against the intended base
   - branch commits not in the base
   - generated files and untracked files
4. Stop if the branch includes unexplained or unrelated work. Do not silently absorb user changes. If intended changes remain uncommitted and their ownership is clear, commit them using repository conventions.
5. Run or confirm proportional verification. Do not claim a check passed unless it ran successfully on the current content. Record material checks not run and why.
6. Inspect recent merged pull requests and commit history for title, label, and body conventions. Preserve required template sections.
7. Push the branch without rewriting published history, then create a ready-for-review pull request. Use a draft only when the user requests one or the work has a known blocker that makes review premature.
8. Refetch the created pull request and verify its base, head, title, body, draft state, and URL. If the user also asked to monitor or babysit it, continue with the `babysit-pr` skill when available.

When another publishing skill or connector is available, use it for safe commit, push, and create mechanics. This skill owns scope review, editorial quality, and ready-versus-draft policy.

## Title

Prefer a concise title that describes the outcome or value, not a file inventory or implementation mechanism. Follow the repository's prefix convention when one exists.

- Bad: `fix(server): update parser and preflight`
- Good: `fix(server): detect remote CLI version drift correctly`

Do not overstate measured improvements or user impact.

## Body

Lead with a plain-language explanation of the problem based on the user's request. Follow with how the change solves it, then verification and visual evidence when relevant. Do not begin with a list of modified files.

```markdown
## Problem
<What failed or was missing, who noticed, and why it mattered.>

## Solution
<How behavior changes, in a few sentences.>

## Verification
- `<command or manual check>`

## Evidence
<Screenshot or recording link when useful.>
```

Adapt this structure to the repository template rather than replacing it. Omit empty optional sections.

When the harness and model are known and repository policy allows provenance, add a short footer. Never guess model identity.

## Boundaries

Creating a pull request does not authorize merging it, changing repository settings, or including unrelated cleanup. Finish with the pull request URL, base and head branches, current head OID, checks run, and any known limitation.
