#!/usr/bin/env python3
"""Infer and safely update a Disco configuration from repository signals."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
from pathlib import Path
from typing import Any, NamedTuple

SKIP_DIRS = {
    ".git",
    ".mypy_cache",
    ".next",
    ".pytest_cache",
    ".turbo",
    ".venv",
    ".vercel",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
    "venv",
}

FRAMEWORK_DEFAULT_PORTS = {
    "nextjs": 3000,
    "node": 3000,
    "django": 8000,
    "flask": 8000,
    "fastapi": 8000,
    "go": 8080,
    "rust": 8080,
    "generic": 8000,
}

STATIC_OUTPUT_HINTS = ("out", "dist", "build", "public")
SERVICE_TYPES = {"container", "static", "generator", "command", "cron", "cgi"}
SERVICE_FIELDS = {
    "type",
    "publicPath",
    "image",
    "port",
    "command",
    "build",
    "publishedPorts",
    "volumes",
    "schedule",
    "exposedInternally",
    "timeout",
    "health",
    "extraSwarmParams",
}
ROOT_FIELDS = {"version", "services", "images"}
SENSITIVE_KEY_PATTERN = re.compile(
    r"(?:password|passwd|secret|token|api[-_]?key|private[-_]?key|environment|^env$)",
    flags=re.IGNORECASE,
)


class AnalysisError(Exception):
    """Raised when repository input cannot be analyzed safely."""


class CronCandidate(NamedTuple):
    name: str
    command: str
    schedule: str | None


def safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return ""


def read_json_object(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AnalysisError(f"Could not read valid JSON from {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise AnalysisError(f"Expected a JSON object in {path}.")
    return value


def iter_repo_files(root: Path):
    for path in root.rglob("*"):
        try:
            relative = path.relative_to(root)
        except ValueError:
            continue
        if any(part in SKIP_DIRS for part in relative.parts):
            continue
        if path.is_file():
            yield path


def path_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def relative_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def detect_package_manager(repo_root: Path, app_root: Path) -> str:
    for root in (app_root, repo_root):
        if (root / "pnpm-lock.yaml").exists():
            return "pnpm"
        if (root / "yarn.lock").exists():
            return "yarn"
        if (root / "bun.lockb").exists() or (root / "bun.lock").exists():
            return "bun"
    return "npm"


def run_script_cmd(package_manager: str, script_name: str) -> str:
    if package_manager == "yarn":
        return f"yarn {script_name}"
    if package_manager == "pnpm":
        return f"pnpm run {script_name}"
    if package_manager == "bun":
        return f"bun run {script_name}"
    return f"npm run {script_name}"


def package_scripts(package_json: dict[str, Any]) -> dict[str, str]:
    scripts = package_json.get("scripts", {})
    if not isinstance(scripts, dict):
        return {}
    return {str(name): command for name, command in scripts.items() if isinstance(command, str)}


def package_dependencies(package_json: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for field in ("dependencies", "devDependencies"):
        dependencies = package_json.get(field, {})
        if isinstance(dependencies, dict):
            names.update(str(name).lower() for name in dependencies)
    return names


def python_manifest_text(app_root: Path) -> str:
    candidates = [
        app_root / "pyproject.toml",
        app_root / "Pipfile",
        app_root / "requirements.txt",
        *sorted(app_root.glob("requirements*.txt")),
    ]
    seen: set[Path] = set()
    chunks = []
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        chunks.append(safe_read_text(path).lower())
    return "\n".join(chunks)


def has_python_dependency(manifest_text: str, name: str) -> bool:
    return bool(re.search(rf"(?<![a-z0-9_-]){re.escape(name)}(?![a-z0-9_-])", manifest_text))


def detect_framework(app_root: Path, package_json: dict[str, Any]) -> str:
    dependencies = package_dependencies(package_json)
    python_dependencies = python_manifest_text(app_root)

    if "next" in dependencies or list(app_root.glob("next.config.*")):
        return "nextjs"
    if "astro" in dependencies or list(app_root.glob("astro.config.*")):
        return "astro"
    if "vite" in dependencies or list(app_root.glob("vite.config.*")):
        return "vite"
    if (app_root / "manage.py").exists() or has_python_dependency(python_dependencies, "django"):
        return "django"
    if has_python_dependency(python_dependencies, "flask"):
        return "flask"
    if has_python_dependency(python_dependencies, "fastapi"):
        return "fastapi"
    if (app_root / "go.mod").exists():
        return "go"
    if (app_root / "Cargo.toml").exists():
        return "rust"
    if (app_root / "package.json").exists():
        return "node"
    return "generic"


def looks_like_runnable_app(app_root: Path) -> bool:
    package_json = read_json_object(app_root / "package.json") or {}
    scripts = package_scripts(package_json)
    framework = detect_framework(app_root, package_json)
    if framework not in {"generic", "node"}:
        return True
    if any(name in scripts for name in ("start", "serve", "prod")):
        return True
    return any(
        (app_root / name).exists()
        for name in ("manage.py", "go.mod", "Cargo.toml", "Procfile")
    )


def is_workspace_root(repo_root: Path) -> bool:
    package_json = read_json_object(repo_root / "package.json") or {}
    workspaces = package_json.get("workspaces")
    return bool(workspaces) or any(
        (repo_root / name).exists()
        for name in ("pnpm-workspace.yaml", "turbo.json", "nx.json")
    )


def discover_app_candidates(repo_root: Path) -> list[Path]:
    manifest_names = {
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "manage.py",
        "go.mod",
        "Cargo.toml",
        "Procfile",
    }
    parents = {path.parent for path in iter_repo_files(repo_root) if path.name in manifest_names}
    return sorted(
        (path for path in parents if path != repo_root and looks_like_runnable_app(path)),
        key=lambda path: relative_path(path, repo_root),
    )


def resolve_app_root(
    repo_root: Path,
    app_path_arg: str | None,
) -> tuple[Path, str, list[str], list[str]]:
    warnings: list[str] = []
    blockers: list[str] = []
    if app_path_arg is not None:
        app_root = (repo_root / app_path_arg).resolve()
        if not path_within(app_root, repo_root):
            raise AnalysisError("--app-path must resolve inside --repo.")
        if not app_root.exists() or not app_root.is_dir():
            raise AnalysisError(f"Application path does not exist: {app_root}")
        return app_root, relative_path(app_root, repo_root) or ".", warnings, blockers

    candidates = discover_app_candidates(repo_root)
    if looks_like_runnable_app(repo_root):
        if is_workspace_root(repo_root) and candidates:
            candidate_list = ", ".join(
                [".", *(relative_path(path, repo_root) for path in candidates)]
            )
            blockers.append(
                "A runnable workspace root and nested app candidates were found. Re-run with "
                f"--app-path set to one of: {candidate_list}."
            )
        return repo_root, ".", warnings, blockers

    if len(candidates) == 1:
        app_root = candidates[0]
        app_path = relative_path(app_root, repo_root)
        warnings.append(f"Auto-selected the only runnable app candidate: {app_path}.")
        return app_root, app_path, warnings, blockers
    if len(candidates) > 1:
        candidate_list = ", ".join(relative_path(path, repo_root) for path in candidates)
        blockers.append(
            "Multiple runnable app candidates were found. Re-run with --app-path set to one of: "
            f"{candidate_list}."
        )
    return repo_root, ".", warnings, blockers


def discover_dockerfiles(root: Path) -> list[Path]:
    return sorted(path for path in iter_repo_files(root) if path.name.startswith("Dockerfile"))


def choose_dockerfile(
    repo_root: Path,
    app_root: Path,
    dockerfiles: list[Path],
    explicit_dockerfile: str | None = None,
) -> tuple[Path | None, list[str], list[str]]:
    warnings: list[str] = []
    blockers: list[str] = []

    if explicit_dockerfile:
        selected = (repo_root / explicit_dockerfile).resolve()
        if not path_within(selected, repo_root):
            raise AnalysisError("--dockerfile must resolve inside --repo.")
        if not selected.is_file():
            raise AnalysisError(f"Dockerfile does not exist: {selected}")
        return selected, warnings, blockers

    app_dockerfile = app_root / "Dockerfile"
    if app_dockerfile in dockerfiles:
        return app_dockerfile, warnings, blockers

    app_dockerfiles = [path for path in dockerfiles if path_within(path, app_root)]
    if len(app_dockerfiles) == 1:
        warnings.append(
            "Selected the only Dockerfile under the app path; verify its build context."
        )
        return app_dockerfiles[0], warnings, blockers
    if len(app_dockerfiles) > 1:
        candidates = ", ".join(relative_path(path, repo_root) for path in app_dockerfiles)
        blockers.append(
            "Multiple Dockerfiles were found under the app path. Re-run with --dockerfile set "
            f"to one of: {candidates}."
        )
        return None, warnings, blockers

    root_dockerfile = repo_root / "Dockerfile"
    if root_dockerfile in dockerfiles:
        if app_root != repo_root:
            warnings.append("Using the repository-root Dockerfile for the selected app path.")
        return root_dockerfile, warnings, blockers

    if dockerfiles:
        candidates = ", ".join(relative_path(path, repo_root) for path in dockerfiles)
        blockers.append(
            "Dockerfiles exist outside the selected app path. Re-run with --dockerfile if one "
            f"belongs to this app: {candidates}."
        )
    return None, warnings, blockers


def resolve_build_context(
    repo_root: Path,
    selected_dockerfile: Path | None,
    explicit_context: str | None,
) -> tuple[Path | None, list[str]]:
    blockers: list[str] = []
    if not selected_dockerfile:
        if explicit_context:
            raise AnalysisError("--context requires a selected Dockerfile.")
        return None, blockers

    if explicit_context:
        context = (repo_root / explicit_context).resolve()
        if not path_within(context, repo_root):
            raise AnalysisError("--context must resolve inside --repo.")
        if not context.is_dir():
            raise AnalysisError(f"Build context does not exist: {context}")
        return context, blockers

    if selected_dockerfile == repo_root / "Dockerfile":
        return repo_root, blockers

    blockers.append(
        "A non-root Dockerfile needs an explicit build context. Re-run with --context."
    )
    return selected_dockerfile.parent, blockers


def parse_exposed_port(dockerfile_path: Path | None) -> int | None:
    if not dockerfile_path:
        return None
    content = safe_read_text(dockerfile_path)
    for match in re.finditer(
        r"^\s*EXPOSE\s+(\d+)\b",
        content,
        flags=re.MULTILINE | re.IGNORECASE,
    ):
        port = int(match.group(1))
        if 1 <= port <= 65535:
            return port
    return None


def parse_port_from_scripts(scripts: dict[str, str]) -> int | None:
    ordered_candidates = [scripts[name] for name in ("start", "serve", "prod") if name in scripts]
    ordered_candidates.extend(scripts.values())
    patterns = [
        r"\b--port(?:=|\s+)(\d+)\b",
        r"\s-p\s+(\d+)\b",
        r"\bPORT=(\d+)\b",
    ]
    for command in ordered_candidates:
        for pattern in patterns:
            match = re.search(pattern, command)
            if match:
                port = int(match.group(1))
                if 1 <= port <= 65535:
                    return port
    return None


def is_next_static_export(app_root: Path, scripts: dict[str, str]) -> bool:
    for config_file in app_root.glob("next.config.*"):
        if re.search(r"output\s*:\s*['\"]export['\"]", safe_read_text(config_file)):
            return True
    return any("next export" in command for command in scripts.values())


def detect_static_public_path(app_root: Path) -> str | None:
    for candidate in STATIC_OUTPUT_HINTS:
        candidate_path = app_root / candidate
        if candidate_path.exists() and candidate_path.is_dir():
            return candidate
    return None


def detect_health_route(app_root: Path) -> str | None:
    route_candidates = [
        ("app/api/health/route.ts", "/api/health"),
        ("app/api/health/route.js", "/api/health"),
        ("app/api/healthz/route.ts", "/api/healthz"),
        ("app/api/healthz/route.js", "/api/healthz"),
        ("app/api/status/route.ts", "/api/status"),
        ("app/api/status/route.js", "/api/status"),
        ("app/api/db-check/route.ts", "/api/db-check"),
        ("app/api/db-check/route.js", "/api/db-check"),
        ("pages/api/health.ts", "/api/health"),
        ("pages/api/health.js", "/api/health"),
        ("pages/api/healthz.ts", "/api/healthz"),
        ("pages/api/healthz.js", "/api/healthz"),
        ("pages/health.tsx", "/health"),
        ("pages/health.jsx", "/health"),
        ("healthcheck", "/health"),
    ]
    for relative, route in route_candidates:
        if (app_root / relative).exists():
            return route

    for route_file in app_root.glob("app/api/**/route.*"):
        try:
            route_relative = route_file.relative_to(app_root).as_posix()
        except ValueError:
            continue
        match = re.match(r"app/api/(.+)/route\.[^/]+$", route_relative)
        if match and any(
            token in match.group(1) for token in ("health", "status", "ready", "db-check")
        ):
            return f"/api/{match.group(1)}"
    return None


def detect_prisma_provider(app_root: Path) -> str | None:
    schema_path = app_root / "prisma/schema.prisma"
    if not schema_path.exists():
        return None
    match = re.search(
        r"datasource\s+\w+\s*\{[^}]*provider\s*=\s*\"([^\"]+)\"",
        safe_read_text(schema_path),
        flags=re.DOTALL,
    )
    return match.group(1).strip().lower() if match else None


def detect_migration_command(
    scripts: dict[str, str],
    package_manager: str,
    app_root: Path,
) -> str | None:
    for name in ("prisma:migrate:deploy", "db:migrate", "migrate:deploy", "migrate"):
        command = scripts.get(name)
        if command and "migrate" in command:
            return run_script_cmd(package_manager, name)
    for name, command in scripts.items():
        if "prisma migrate deploy" in command:
            return run_script_cmd(package_manager, name)
    if (app_root / "manage.py").exists():
        return "python manage.py migrate"
    return None


def parse_procfile(app_root: Path) -> dict[str, str]:
    processes: dict[str, str] = {}
    for raw_line in safe_read_text(app_root / "Procfile").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        name, command = line.split(":", 1)
        if name.strip() and command.strip():
            processes[name.strip()] = command.strip()
    return processes


def is_cron_script(name: str) -> bool:
    return "cron" in name.lower() or "schedule" in name.lower()


def sanitize_service_name(name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9_-]+", "-", name).strip("-").lower()
    return sanitized or "service"


def detect_worker_commands(
    app_root: Path,
    scripts: dict[str, str],
    package_manager: str,
) -> dict[str, str]:
    ignored = {"dev", "build", "start", "test", "lint", "typecheck", "format", "prepare", "postinstall"}
    workers: dict[str, str] = {}
    for name in sorted(scripts):
        if name in ignored or is_cron_script(name):
            continue
        if re.search(r"(?:worker|queue|consumer|scheduler|jobs?|beat)", name, flags=re.IGNORECASE):
            workers[sanitize_service_name(name)] = run_script_cmd(package_manager, name)

    for name, command in parse_procfile(app_root).items():
        if name == "web" or is_cron_script(name):
            continue
        if re.search(r"(?:worker|queue|consumer|scheduler|jobs?|beat)", name, flags=re.IGNORECASE):
            workers[sanitize_service_name(name)] = command
    return workers


def infer_cron_schedule(script_name: str) -> str | None:
    normalized = script_name.lower()
    if "hourly" in normalized:
        return "0 * * * *"
    if "daily" in normalized:
        return "0 0 * * *"
    if "weekly" in normalized:
        return "0 0 * * 0"
    if "monthly" in normalized:
        return "0 0 1 * *"
    match = re.search(r"every[-_:]?(\d+)[-_:]?min", normalized)
    if not match:
        return None
    minutes = int(match.group(1))
    if minutes == 60:
        return "0 * * * *"
    if 1 <= minutes <= 59:
        return f"*/{minutes} * * * *"
    return None


def detect_cron_commands(
    scripts: dict[str, str],
    package_manager: str,
) -> list[CronCandidate]:
    return [
        CronCandidate(
            name=sanitize_service_name(name),
            command=run_script_cmd(package_manager, name),
            schedule=infer_cron_schedule(name),
        )
        for name in sorted(scripts)
        if is_cron_script(name)
    ]


def attach_runtime_image(
    service: dict[str, Any],
    image: str | None,
    build_command: str | None,
) -> None:
    if image:
        service["image"] = image
    if build_command:
        service["build"] = build_command


def make_runtime_service(
    *,
    command: str,
    runtime_image: str | None,
    build_command: str | None,
    volumes: list[dict[str, str]] | None,
    service_type: str | None = None,
    schedule: str | None = None,
) -> dict[str, Any]:
    service: dict[str, Any] = {"command": command}
    if service_type:
        service["type"] = service_type
    if schedule:
        service["schedule"] = schedule
    attach_runtime_image(service, runtime_image, build_command)
    if volumes:
        service["volumes"] = volumes
    return service


def build_disco_config(
    repo_root: Path,
    app_root: Path,
    app_path_arg: str,
    package_manager: str,
    package_json: dict[str, Any],
    framework: str,
    selected_dockerfile: Path | None,
    build_context: Path | None,
    explicit_port: int | None,
    explicit_image: str | None = None,
    build_command: str | None = None,
    web_type: str | None = None,
    public_path: str | None = None,
    health_path: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    scripts = package_scripts(package_json)
    warnings: list[str] = []
    facts: dict[str, Any] = {
        "repoRoot": str(repo_root),
        "appRoot": str(app_root),
        "appPath": app_path_arg,
        "packageManager": package_manager,
        "framework": framework,
        "dockerfile": None,
    }

    services: dict[str, dict[str, Any]] = {}
    images: dict[str, dict[str, str]] = {}
    runtime_image = explicit_image

    if selected_dockerfile:
        dockerfile_relative = relative_path(selected_dockerfile, repo_root)
        facts["dockerfile"] = dockerfile_relative
        if selected_dockerfile != repo_root / "Dockerfile":
            runtime_image = "app"
            images[runtime_image] = {
                "dockerfile": dockerfile_relative,
                "context": relative_path(build_context or selected_dockerfile.parent, repo_root),
            }

    if web_type:
        mode = web_type
    elif framework == "nextjs" and is_next_static_export(app_root, scripts):
        mode = "generator"
    elif framework in {"vite", "astro"}:
        mode = "generator"
    elif not package_json and detect_static_public_path(app_root):
        mode = "static"
    else:
        mode = "container"

    web: dict[str, Any] = {}
    if mode == "static":
        web["type"] = "static"
        web["publicPath"] = public_path or detect_static_public_path(app_root) or "public"
    elif mode == "generator":
        web["type"] = "generator"
        default_public_path = "out" if framework == "nextjs" else "dist"
        web["publicPath"] = public_path or detect_static_public_path(app_root) or default_public_path
        attach_runtime_image(web, runtime_image, build_command)
    else:
        detected_port = explicit_port
        if detected_port is None:
            detected_port = parse_exposed_port(selected_dockerfile)
        if detected_port is None:
            detected_port = parse_port_from_scripts(scripts)
        if detected_port is None:
            detected_port = FRAMEWORK_DEFAULT_PORTS.get(framework, FRAMEWORK_DEFAULT_PORTS["generic"])
        web["port"] = detected_port
        attach_runtime_image(web, runtime_image, build_command)

        if not selected_dockerfile and "start" in scripts:
            web["command"] = run_script_cmd(package_manager, "start")

        route = health_path or detect_health_route(app_root)
        if route:
            route = route if route.startswith("/") else f"/{route}"
            web["health"] = {
                "command": f"curl -f http://localhost:{detected_port}{route} || exit 1"
            }
            facts["healthRoute"] = route
            warnings.append("Verify the runtime image contains curl for the inferred health command.")

        prisma_provider = detect_prisma_provider(app_root)
        if prisma_provider:
            facts["prismaProvider"] = prisma_provider
        if prisma_provider == "sqlite":
            warnings.append(
                "SQLite detected. Point DATABASE_URL at /data and confirm the sqlite-data volume name."
            )
            web["volumes"] = [{"name": "sqlite-data", "destinationPath": "/data"}]

    services["web"] = web

    migration_command = detect_migration_command(scripts, package_manager, app_root)
    if migration_command:
        services["hook:deploy:start:before"] = make_runtime_service(
            command=migration_command,
            runtime_image=runtime_image,
            build_command=build_command,
            volumes=web.get("volumes"),
            service_type="command",
        )
        facts["migrationCommand"] = migration_command

    for name, command in detect_worker_commands(app_root, scripts, package_manager).items():
        services[name] = make_runtime_service(
            command=command,
            runtime_image=runtime_image,
            build_command=build_command,
            volumes=web.get("volumes"),
        )

    ambiguous_crons: list[str] = []
    for candidate in detect_cron_commands(scripts, package_manager):
        if not candidate.schedule:
            ambiguous_crons.append(candidate.name)
            continue
        services[candidate.name] = make_runtime_service(
            command=candidate.command,
            runtime_image=runtime_image,
            build_command=build_command,
            volumes=web.get("volumes"),
            service_type="cron",
            schedule=candidate.schedule,
        )

    if ambiguous_crons:
        facts["ambiguousCronServices"] = ambiguous_crons

    disco: dict[str, Any] = {"version": "1.0", "services": services}
    if images:
        disco["images"] = images
    return disco, {"facts": facts, "warnings": warnings, "blockers": []}


def merge_missing(existing: dict[str, Any], inferred: dict[str, Any]) -> dict[str, Any]:
    """Preserve existing values while adding inferred keys that are absent."""
    merged = copy.deepcopy(existing)
    for key, inferred_value in inferred.items():
        if key not in merged:
            merged[key] = copy.deepcopy(inferred_value)
        elif isinstance(merged[key], dict) and isinstance(inferred_value, dict):
            merged[key] = merge_missing(merged[key], inferred_value)
    return merged


def apply_explicit_overrides(
    config: dict[str, Any],
    args: argparse.Namespace,
    selected_dockerfile: Path | None,
    build_context: Path | None,
    repo_root: Path,
) -> None:
    services = config.setdefault("services", {})
    web = services.setdefault("web", {})

    if args.web_type:
        if args.web_type == "container":
            web.pop("type", None)
            web.pop("publicPath", None)
        else:
            web["type"] = args.web_type
            web.pop("port", None)
    if args.port is not None:
        web["port"] = args.port
    if args.public_path:
        web["publicPath"] = args.public_path
    if args.image or args.build_command:
        for service in services.values():
            if not isinstance(service, dict):
                continue
            is_pure_static = service.get("type") == "static" and service.get("command") is None
            if is_pure_static:
                continue
            if args.image:
                service["image"] = args.image
            if args.build_command:
                service["build"] = args.build_command
    if args.health_path:
        route = args.health_path if args.health_path.startswith("/") else f"/{args.health_path}"
        port = web.get("port", args.port or 8000)
        web["health"] = {"command": f"curl -f http://localhost:{port}{route} || exit 1"}

    if args.dockerfile and selected_dockerfile and selected_dockerfile != repo_root / "Dockerfile":
        config.setdefault("images", {})["app"] = {
            "dockerfile": relative_path(selected_dockerfile, repo_root),
            "context": relative_path(build_context or selected_dockerfile.parent, repo_root),
        }
        for service in services.values():
            if not isinstance(service, dict):
                continue
            is_pure_static = service.get("type") == "static" and service.get("command") is None
            if not is_pure_static:
                service["image"] = "app"


def cron_expression_is_valid(expression: Any) -> bool:
    if not isinstance(expression, str):
        return False
    parts = expression.split()
    if len(parts) != 5:
        return False
    return all(bool(re.fullmatch(r"[0-9*/,-]+", part)) for part in parts)


def sensitive_paths(value: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if SENSITIVE_KEY_PATTERN.search(str(key)):
                found.append(path)
            else:
                found.extend(sensitive_paths(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(sensitive_paths(child, f"{prefix}[{index}]"))
    return found


def redact_sensitive(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "<redacted>" if SENSITIVE_KEY_PATTERN.search(str(key)) else redact_sensitive(child)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(child) for child in value]
    return value


def valid_port(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= 65535


def validate_service_fields(
    service_name: str,
    service: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []

    if "port" in service and not valid_port(service.get("port")):
        blockers.append(f"services.{service_name}.port must be an integer from 1 to 65535.")
    for field in ("image", "command", "build", "publicPath", "schedule"):
        if field in service and (
            not isinstance(service.get(field), str) or not service.get(field)
        ):
            blockers.append(f"services.{service_name}.{field} must be a non-empty string.")

    volumes = service.get("volumes")
    if volumes is not None:
        if not isinstance(volumes, list):
            blockers.append(f"services.{service_name}.volumes must be a list.")
        else:
            for index, volume in enumerate(volumes):
                if not isinstance(volume, dict):
                    blockers.append(f"services.{service_name}.volumes[{index}] must be an object.")
                    continue
                if not isinstance(volume.get("name"), str) or not volume.get("name"):
                    blockers.append(f"services.{service_name}.volumes[{index}].name must be a string.")
                if not isinstance(volume.get("destinationPath"), str) or not volume.get("destinationPath"):
                    blockers.append(
                        f"services.{service_name}.volumes[{index}].destinationPath must be a string."
                    )

    published_ports = service.get("publishedPorts")
    if published_ports is not None:
        if not isinstance(published_ports, list):
            blockers.append(f"services.{service_name}.publishedPorts must be a list.")
        else:
            for index, port in enumerate(published_ports):
                if not isinstance(port, dict):
                    blockers.append(
                        f"services.{service_name}.publishedPorts[{index}] must be an object."
                    )
                    continue
                if not valid_port(port.get("publishedAs")):
                    blockers.append(
                        f"services.{service_name}.publishedPorts[{index}].publishedAs must be a valid port."
                    )
                if not valid_port(port.get("fromContainerPort")):
                    blockers.append(
                        f"services.{service_name}.publishedPorts[{index}].fromContainerPort must be a valid port."
                    )
                if port.get("protocol", "tcp") not in {"tcp", "udp"}:
                    blockers.append(
                        f"services.{service_name}.publishedPorts[{index}].protocol must be tcp or udp."
                    )

    health = service.get("health")
    if health is not None and (
        not isinstance(health, dict)
        or not isinstance(health.get("command"), str)
        or not health.get("command")
    ):
        blockers.append(f"services.{service_name}.health must contain a non-empty command string.")

    timeout = service.get("timeout")
    if timeout is not None and (
        not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0
    ):
        blockers.append(f"services.{service_name}.timeout must be a positive integer.")

    exposed_internally = service.get("exposedInternally")
    if exposed_internally is not None and not isinstance(exposed_internally, bool):
        blockers.append(f"services.{service_name}.exposedInternally must be a boolean.")

    extra_swarm_params = service.get("extraSwarmParams")
    if extra_swarm_params is not None and not isinstance(extra_swarm_params, str):
        blockers.append(f"services.{service_name}.extraSwarmParams must be a string.")

    return blockers


def validate_disco_config(
    config: dict[str, Any],
    repo_root: Path,
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    blockers: list[str] = []

    unknown_root_fields = sorted(set(config) - ROOT_FIELDS)
    if unknown_root_fields:
        warnings.append(
            "Fields not present in the current Disco root schema: " + ", ".join(unknown_root_fields) + "."
        )

    if str(config.get("version")) != "1.0":
        blockers.append("Root field 'version' must be '1.0'.")

    services = config.get("services")
    if not isinstance(services, dict):
        blockers.append("Root field 'services' must be an object.")
        return warnings, blockers
    if not isinstance(services.get("web"), dict):
        blockers.append("services.web must exist and be an object.")

    images = config.get("images", {})
    if not isinstance(images, dict):
        blockers.append("Root field 'images' must be an object when present.")
        images = {}

    valid_images: set[str] = set()
    for image_name, image_config in images.items():
        if not isinstance(image_config, dict):
            blockers.append(f"images.{image_name} must be an object.")
            continue
        dockerfile = image_config.get("dockerfile", "Dockerfile")
        context = image_config.get("context", ".")
        if not isinstance(dockerfile, str) or not isinstance(context, str):
            blockers.append(f"images.{image_name} dockerfile and context must be strings.")
            continue
        dockerfile_path = (repo_root / dockerfile).resolve()
        context_path = (repo_root / context).resolve()
        if not path_within(dockerfile_path, repo_root) or not dockerfile_path.is_file():
            blockers.append(f"images.{image_name}.dockerfile does not resolve to a repository file: {dockerfile}.")
        if not path_within(context_path, repo_root) or not context_path.is_dir():
            blockers.append(f"images.{image_name}.context does not resolve to a repository directory: {context}.")
        valid_images.add(str(image_name))

    used_images: set[str] = set()
    root_dockerfile_exists = (repo_root / "Dockerfile").is_file()
    for service_name, service in services.items():
        if not isinstance(service, dict):
            blockers.append(f"services.{service_name} must be an object.")
            continue
        blockers.extend(validate_service_fields(str(service_name), service))
        unknown_service_fields = sorted(set(service) - SERVICE_FIELDS)
        if unknown_service_fields:
            warnings.append(
                f"services.{service_name} contains fields outside the current Disco schema: "
                + ", ".join(unknown_service_fields)
                + "."
            )
        service_type = service.get("type", "container")
        if service_type not in SERVICE_TYPES:
            blockers.append(f"services.{service_name}.type is not supported: {service_type!r}.")
            continue

        if service_name == "web" and service_type in {"container", "cgi"}:
            if "port" not in service:
                blockers.append("services.web.port is required for container and cgi services.")
        if service_type in {"static", "generator"} and not isinstance(service.get("publicPath"), str):
            blockers.append(f"services.{service_name}.publicPath is required for type {service_type}.")
        if service_type in {"command", "cron"} and not isinstance(service.get("command"), str):
            blockers.append(f"services.{service_name}.command is required for type {service_type}.")
        if service_type == "cron" and not cron_expression_is_valid(service.get("schedule")):
            blockers.append(f"services.{service_name}.schedule must be a five-part cron expression.")

        image = service.get("image")
        build = service.get("build")
        if isinstance(image, str):
            if image in valid_images:
                used_images.add(image)
        elif image is not None:
            blockers.append(f"services.{service_name}.image must be a string.")

        needs_runtime_image = not (service_type == "static" and service.get("command") is None)
        if build is not None and not isinstance(build, str):
            blockers.append(f"services.{service_name}.build must be a string.")
        if build and not isinstance(image, str):
            blockers.append(
                f"services.{service_name}.image must name a base image when build is used."
            )
        if needs_runtime_image and not build and image is None and not root_dockerfile_exists:
            blockers.append(
                f"services.{service_name} needs a root Dockerfile, a custom image reference, or a prebuilt image."
            )

    for unused in sorted(valid_images - used_images):
        warnings.append(f"images.{unused} is defined but no service references it.")

    for path in sensitive_paths(config):
        blockers.append(
            f"Sensitive-looking field '{path}' belongs in Disco environment settings, not disco.json."
        )
    return warnings, blockers


def unique_messages(messages: list[str]) -> list[str]:
    return list(dict.fromkeys(messages))


def render_report(metadata: dict[str, Any], disco: dict[str, Any]) -> str:
    facts = metadata.get("facts", {})
    warnings = metadata.get("warnings", [])
    blockers = metadata.get("blockers", [])

    def fmt(value: Any) -> str:
        return "none" if value in (None, "") else str(value)

    lines = [
        "# Disco Analysis Report",
        "",
        "## Detected Facts",
        f"- App root: `{fmt(facts.get('appRoot', 'n/a'))}`",
        f"- App path: `{fmt(facts.get('appPath', 'n/a'))}`",
        f"- Framework: `{fmt(facts.get('framework', 'n/a'))}`",
        f"- Package manager: `{fmt(facts.get('packageManager', 'n/a'))}`",
        f"- Dockerfile: `{fmt(facts.get('dockerfile'))}`",
        f"- Health route: `{fmt(facts.get('healthRoute'))}`",
        f"- Migration command: `{fmt(facts.get('migrationCommand'))}`",
        f"- Prisma provider: `{fmt(facts.get('prismaProvider'))}`",
        f"- Update mode: `{fmt(facts.get('updateMode', 'new'))}`",
        "",
        "## Blockers",
    ]
    lines.extend([f"- {message}" for message in blockers] or ["- None"])
    lines.extend(["", "## Warnings"])
    lines.extend([f"- {message}" for message in warnings] or ["- None"])
    lines.extend(
        [
            "",
            "## Proposed disco.json",
            "```json",
            json.dumps(redact_sensitive(disco), indent=2),
            "```",
            "",
            "## Completion Checks",
            "- Every runtime service has a resolvable image strategy.",
            "- Every custom image is referenced by the intended service.",
            "- Existing fields remain preserved unless replacement was explicit.",
            "- Secrets live in Disco environment settings.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    try:
        temporary.write_text(content, encoding="utf-8")
        temporary.replace(path)
    finally:
        if temporary.exists():
            temporary.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Infer and safely update disco.json from repository structure."
    )
    parser.add_argument("--repo", default=".", help="Repository root path")
    parser.add_argument(
        "--app-path",
        default=None,
        help="Application path inside the repository; auto-detected when omitted",
    )
    parser.add_argument("--dockerfile", default=None, help="Dockerfile path relative to --repo")
    parser.add_argument("--context", default=None, help="Build context path relative to --repo")
    parser.add_argument("--image", default=None, help="Prebuilt or base image for inferred services")
    parser.add_argument(
        "--build-command",
        default=None,
        help="Build command used with --image for Dockerfile-free builds",
    )
    parser.add_argument(
        "--web-type",
        choices=("container", "static", "generator"),
        default=None,
        help="Override inferred web service type",
    )
    parser.add_argument("--public-path", default=None, help="Override static/generator publicPath")
    parser.add_argument("--health-path", default=None, help="Override or add the HTTP health path")
    parser.add_argument("--port", type=int, default=None, help="Override web port")
    parser.add_argument("--output", default="disco.json", help="Output disco.json path")
    parser.add_argument("--report", default="", help="Optional Markdown report path")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing output configuration instead of preserving its fields",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the proposed configuration without writing any files",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo).resolve()
    if not repo_root.exists() or not repo_root.is_dir():
        print(f"[ERROR] Repository path does not exist: {repo_root}")
        return 2
    if args.port is not None and not 1 <= args.port <= 65535:
        print("[ERROR] --port must be between 1 and 65535.")
        return 2
    if args.build_command and not args.image:
        print("[ERROR] --build-command requires --image to name the base image.")
        return 2

    try:
        app_root, app_path, app_warnings, app_blockers = resolve_app_root(
            repo_root, args.app_path
        )
        package_json = read_json_object(app_root / "package.json") or {}
    except AnalysisError as exc:
        print(f"[ERROR] {exc}")
        return 2

    package_manager = detect_package_manager(repo_root, app_root)
    framework = detect_framework(app_root, package_json)
    dockerfiles = discover_dockerfiles(repo_root)

    if args.image and not args.dockerfile:
        selected_dockerfile = None
        docker_warnings = (
            ["Using the explicit image strategy; repository Dockerfiles were not selected."]
            if dockerfiles
            else []
        )
        docker_blockers: list[str] = []
    else:
        try:
            selected_dockerfile, docker_warnings, docker_blockers = choose_dockerfile(
                repo_root,
                app_root,
                dockerfiles,
                explicit_dockerfile=args.dockerfile,
            )
        except AnalysisError as exc:
            print(f"[ERROR] {exc}")
            return 2

    try:
        build_context, context_blockers = resolve_build_context(
            repo_root,
            selected_dockerfile,
            args.context,
        )
    except AnalysisError as exc:
        print(f"[ERROR] {exc}")
        return 2

    inferred, metadata = build_disco_config(
        repo_root=repo_root,
        app_root=app_root,
        app_path_arg=app_path,
        package_manager=package_manager,
        package_json=package_json,
        framework=framework,
        selected_dockerfile=selected_dockerfile,
        build_context=build_context,
        explicit_port=args.port,
        explicit_image=args.image,
        build_command=args.build_command,
        web_type=args.web_type,
        public_path=args.public_path,
        health_path=args.health_path,
    )
    metadata["warnings"].extend(app_warnings + docker_warnings)
    metadata["blockers"].extend(app_blockers + docker_blockers)

    output_path = Path(args.output)
    if not output_path.is_absolute():
        output_path = repo_root / output_path
    report_path = Path(args.report) if args.report else None
    if report_path and not report_path.is_absolute():
        report_path = repo_root / report_path

    existing: dict[str, Any] | None = None
    if output_path.exists() and not args.force:
        try:
            existing = read_json_object(output_path)
        except AnalysisError as exc:
            print(f"[ERROR] {exc} Use --force only if replacing it is intentional.")
            return 2

    if context_blockers:
        selected_relative = (
            relative_path(selected_dockerfile, repo_root) if selected_dockerfile else None
        )
        existing_images = existing.get("images", {}) if existing else {}
        existing_context_is_explicit = isinstance(existing_images, dict) and any(
            isinstance(image, dict)
            and image.get("dockerfile") == selected_relative
            and isinstance(image.get("context"), str)
            for image in existing_images.values()
        )
        if not existing_context_is_explicit:
            metadata["blockers"].extend(context_blockers)

    if existing is not None:
        final_config = merge_missing(existing, inferred)
        metadata["facts"]["updateMode"] = "preserve-existing"
    else:
        final_config = inferred
        metadata["facts"]["updateMode"] = "replace" if output_path.exists() else "new"

    apply_explicit_overrides(
        final_config,
        args,
        selected_dockerfile,
        build_context,
        repo_root,
    )
    for service_name in metadata["facts"].get("ambiguousCronServices", []):
        service = final_config.get("services", {}).get(service_name)
        if not isinstance(service, dict) or service.get("type") != "cron" or not cron_expression_is_valid(
            service.get("schedule")
        ):
            metadata["blockers"].append(
                f"Cron-like script '{service_name}' needs an explicit cron service and schedule."
            )
    validation_warnings, validation_blockers = validate_disco_config(final_config, repo_root)
    metadata["warnings"] = unique_messages(metadata["warnings"] + validation_warnings)
    metadata["blockers"] = unique_messages(metadata["blockers"] + validation_blockers)

    if args.dry_run:
        print(json.dumps(redact_sensitive(final_config), indent=2))
    elif not metadata["blockers"]:
        write_text_atomic(output_path, json.dumps(final_config, indent=2) + "\n")
        print(f"[OK] Wrote {output_path}")

    if report_path and not args.dry_run:
        write_text_atomic(report_path, render_report(metadata, final_config))
        print(f"[OK] Wrote {report_path}")

    for warning in metadata["warnings"]:
        print(f"[WARNING] {warning}")
    for blocker in metadata["blockers"]:
        print(f"[BLOCKER] {blocker}")

    if metadata["blockers"]:
        print(f"[INFO] Stopped with {len(metadata['blockers'])} blocker(s); disco.json was not written.")
        return 2
    print(f"[INFO] Completed with {len(metadata['warnings'])} warning(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
