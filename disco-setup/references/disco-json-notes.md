# Disco JSON Notes

Verified 2026-07-31 against the [Disco configuration documentation](https://disco.cloud/docs/disco-json/) and the current [daemon configuration model](https://github.com/letsdiscodev/disco-daemon/blob/main/disco/utils/discofile.py).

## Root shape

- `version`: use `"1.0"`.
- `services`: object keyed by service name.
- `images`: optional object defining repository-built images.
- `services.web`: reserved public HTTP entrypoint.

## Service fields

- `type`: `container` (default), `static`, `generator`, `cron`, `command`, or `cgi`.
- `port`: internal container port; set it explicitly for `web` container services.
- `image`: top-level image name or external registry image.
- `command`: container command override.
- `build`: build command used with `image` as a base image for a Dockerfile-free build.
- `volumes`: list of `{ name, destinationPath }`.
- `health`: `{ command }` readiness check.
- `publishedPorts`: list of `{ publishedAs, fromContainerPort, protocol }`.
- `publicPath`: generated or static content directory.
- `schedule`: five-part cron expression for `type: "cron"`.
- `timeout`: timeout in seconds for commands, generators, and cron jobs.
- `exposedInternally`: allow other projects on the Disco server to reach the service.
- `extraSwarmParams`: advanced Docker Swarm service parameters.

Prefer the current daemon model when older changelog terminology differs. Current Dockerfile-free builds use `image` plus `build`, and command/cron timeouts use `timeout`.

## Image strategies

### Root Dockerfile

Omit `image` to use the repository-root `Dockerfile` and default build context.

### Custom Dockerfile

Define the image and reference it from every service that should use it:

```json
{
  "version": "1.0",
  "services": {
    "web": { "port": 3000, "image": "app" },
    "worker": { "command": "npm run worker", "image": "app" }
  },
  "images": {
    "app": {
      "dockerfile": "apps/web/Dockerfile",
      "context": "apps/web"
    }
  }
}
```

### Prebuilt image

Set `image` to an external registry image and omit a matching top-level image definition:

```json
{
  "version": "1.0",
  "services": {
    "web": { "image": "getmeili/meilisearch:v1.13", "port": 7700 }
  }
}
```

### Dockerfile-free build

Use a base image with a build command:

```json
{
  "version": "1.0",
  "services": {
    "web": {
      "image": "node:22",
      "build": "npm ci && npm run build",
      "command": "npm start",
      "port": 3000
    }
  }
}
```

## Specialized services

- Worker: omit `type`; set `command` and the intended image.
- Cron: set `type: "cron"`, `schedule`, and `command`.
- Pre-deploy hook: name the command service `hook:deploy:start:before`.
- Post-start hook: name the command service `hook:deploy:start:after`.
- Static site: set `web.type: "static"` and `publicPath`.
- Generator: set `web.type: "generator"`, `publicPath`, and its image strategy.

Deployment hooks abort or affect deployment flow, so preserve their volumes and image strategy when updating a configuration.

## Configuration safety

Store environment variables and secrets in the Disco Dashboard or with `disco env:set`. Keep `disco.json` limited to runtime topology and non-secret configuration.
