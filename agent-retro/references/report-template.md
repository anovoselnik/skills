# Agent retrospective report template

```markdown
# Agent retrospective: <scope>

## Executive summary

<Three to five evidence-backed conclusions.>

## Dataset and limits

- Period: <start> to <end>
- Repositories: <list>
- Sessions: <N>
- User messages: <N>
- Tool calls: <N or unavailable>
- Harness/model coverage: <counts>
- Missing or excluded data: <list>

## Ranked patterns

### 1. <Pattern name> — <impact>, <frequency>, <confidence>

- Observed: <what happened>
- Evidence: <session IDs/timestamps and minimal excerpts>
- Likely causes: <clearly labeled inference>
- Alternative explanation: <if material>
- Recommendation: <smallest useful change and destination>
- Evaluation: <how to tell whether it helped>

## Model and harness comparison

| Model / harness | Sessions | User messages | Corrections | Per 100 messages | Tool-error rate | Notes on task mix |
|---|---:|---:|---:|---:|---:|---|

Do not rank rows with materially different task mixes as if they were controlled experiments.

## Slow-run analysis

| Run | Elapsed | Discovery | Implementation | Verification | Recovery/wait | Main avoidable cost |
|---|---:|---:|---:|---:|---:|---|

## What worked

<Behaviors worth preserving, with evidence.>

## Proposed changes

| Priority | Change | Destination | Evidence | Expected effect | How to evaluate |
|---|---|---|---|---|---|

## Unknowns

<Questions the available history cannot answer.>
```
