---
name: disco-setup
description: Safely analyze a repository and create or update `disco.json` for Disco. Use when setting up or migrating a Disco deployment, preserving an existing Disco configuration, or inferring web services, workers, cron jobs, hooks, images, ports, volumes, and health checks from repository signals.
---

# Disco Setup

Produce a deployable `disco.json` from repository evidence. Preserve existing configuration and surface ambiguity as blockers.

## Steps

1. Resolve this skill's directory and analyze the target repository without writing files:

```bash
DISCO_SETUP_SKILL="/absolute/path/to/disco-setup"
python3 "$DISCO_SETUP_SKILL/scripts/infer_disco.py" \
  --repo "$PWD" \
  --dry-run
```

Complete this step when the proposed configuration, every warning, and every blocker have been inspected.

2. Resolve every blocker using repository evidence:

- Select ambiguous monorepo apps with `--app-path`.
- Select ambiguous Dockerfiles with `--dockerfile` and set the intended `--context` for non-root Dockerfiles.
- For Dockerfile-free apps, choose either a prebuilt `--image` or a base `--image` with `--build-command`.
- Set uncertain ports, web modes, public paths, and health paths with their matching overrides.
- Add cron services manually when the schedule cannot be inferred safely.
- Verify inferred health commands can run inside the selected image.

Read [Disco JSON notes](references/disco-json-notes.md) before adding fields manually or resolving a configuration branch not covered by the analyzer.

Complete this step when a dry run exits successfully with no blockers and every warning has been resolved or explicitly accepted.

3. Write the configuration and analysis report:

```bash
python3 "$DISCO_SETUP_SKILL/scripts/infer_disco.py" \
  --repo "$PWD" \
  --output "$PWD/disco.json" \
  --report "$PWD/.disco/disco-analysis.md"
```

The analyzer preserves existing values and adds only missing inferred fields. Explicit CLI overrides win. Use `--force` only when replacing the existing configuration is intentional.

4. Inspect the final diff and reconcile it with the repository:

- Account for every web process, worker, cron job, deployment hook, volume, and custom image.
- Confirm every custom image is referenced by the intended service.
- Confirm the web port matches the process inside its image.
- Keep environment values in Disco's environment settings.

Complete the skill when the report has no blockers, `disco.json` is valid JSON, all runtime processes are represented, and no secret value is stored in the file. Stop after configuration unless the user also asked to deploy.

## Useful overrides

For an explicit monorepo app and Dockerfile:

```bash
python3 "$DISCO_SETUP_SKILL/scripts/infer_disco.py" \
  --repo "$PWD" \
  --app-path apps/web \
  --dockerfile apps/web/Dockerfile \
  --context apps/web \
  --port 8080 \
  --dry-run
```

For a Dockerfile-free build using a base image:

```bash
python3 "$DISCO_SETUP_SKILL/scripts/infer_disco.py" \
  --repo "$PWD" \
  --image node:22 \
  --build-command "npm ci && npm run build" \
  --port 3000 \
  --dry-run
```

## Detection coverage

The analyzer uses package manifests, framework config, Dockerfiles, `Procfile`, scripts, health-route files, and Prisma schema signals. It detects JavaScript and Python frameworks, static generators, a single runnable monorepo app, worker commands, safe cron schedule hints, migration hooks, SQLite volumes, ports, and custom image mappings.

Treat missing or conflicting signals as blockers rather than choosing an arbitrary deployment topology.
