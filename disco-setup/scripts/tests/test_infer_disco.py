from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "infer_disco.py"
SPEC = importlib.util.spec_from_file_location("infer_disco", SCRIPT)
assert SPEC and SPEC.loader
infer_disco = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(infer_disco)


class DiscoAnalyzerTests(unittest.TestCase):
    def write_json(self, path: Path, value: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def run_cli(self, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(SCRIPT), "--repo", str(root), *arguments],
            capture_output=True,
            text=True,
            check=False,
        )

    def make_node_app(self, root: Path, port: int = 3000) -> None:
        (root / "Dockerfile").write_text(f"FROM node:22\nEXPOSE {port}\n", encoding="utf-8")
        self.write_json(
            root / "package.json",
            {"scripts": {"start": "node server.js"}},
        )

    def test_preserves_existing_configuration_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_node_app(root)
            existing = {
                "version": "1.0",
                "services": {
                    "web": {
                        "port": 3000,
                        "publishedPorts": [
                            {
                                "publishedAs": 1234,
                                "fromContainerPort": 1234,
                                "protocol": "tcp",
                            }
                        ],
                    }
                },
            }
            self.write_json(root / "disco.json", existing)

            result = self.run_cli(root)

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads((root / "disco.json").read_text()), existing)

    def test_force_replaces_existing_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_node_app(root, port=4321)
            self.write_json(
                root / "disco.json",
                {"version": "1.0", "services": {"web": {"port": 3000, "custom": True}}},
            )

            result = self.run_cli(root, "--force")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            config = json.loads((root / "disco.json").read_text())
            self.assertEqual(config["services"]["web"], {"port": 4321})

    def test_explicit_override_wins_during_preserving_merge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_node_app(root)
            self.write_json(
                root / "disco.json",
                {"version": "1.0", "services": {"web": {"port": 3000}}},
            )

            result = self.run_cli(root, "--port", "8080")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            config = json.loads((root / "disco.json").read_text())
            self.assertEqual(config["services"]["web"]["port"], 8080)

    def test_dry_run_never_writes_output_or_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_node_app(root)
            output = root / "proposed.json"
            report = root / "analysis.md"

            result = self.run_cli(
                root,
                "--dry-run",
                "--output",
                str(output),
                "--report",
                str(report),
            )

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(output.exists())
            self.assertFalse(report.exists())

    def test_selected_app_dockerfile_takes_precedence_over_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "apps" / "web"
            app.mkdir(parents=True)
            (root / "Dockerfile").write_text("FROM node:22\nEXPOSE 9000\n", encoding="utf-8")
            (app / "Dockerfile").write_text("FROM node:22\nEXPOSE 3000\n", encoding="utf-8")
            self.write_json(app / "package.json", {"dependencies": {"next": "latest"}})

            selected, warnings, blockers = infer_disco.choose_dockerfile(
                root,
                app,
                infer_disco.discover_dockerfiles(root),
            )

            self.assertEqual(selected, app / "Dockerfile")
            self.assertEqual(warnings, [])
            self.assertEqual(blockers, [])

    def test_app_path_does_not_prefix_match_sibling(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "apps" / "web"
            sibling = root / "apps" / "website"
            app.mkdir(parents=True)
            sibling.mkdir(parents=True)
            (sibling / "Dockerfile").write_text("FROM node:22\n", encoding="utf-8")

            selected, _, blockers = infer_disco.choose_dockerfile(
                root,
                app,
                infer_disco.discover_dockerfiles(root),
            )

            self.assertIsNone(selected)
            self.assertTrue(blockers)

    def test_generator_references_nonroot_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "apps" / "web"
            app.mkdir(parents=True)
            dockerfile = app / "Dockerfile"
            dockerfile.write_text("FROM node:22\nRUN npm run build\n", encoding="utf-8")
            package = {"dependencies": {"vite": "latest"}, "scripts": {"build": "vite build"}}

            config, _ = infer_disco.build_disco_config(
                root,
                app,
                "apps/web",
                "npm",
                package,
                "vite",
                dockerfile,
                None,
            )

            self.assertEqual(config["services"]["web"]["image"], "app")
            self.assertIn("app", config["images"])

    def test_fastapi_is_detected_from_pyproject(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "pyproject.toml").write_text(
                '[project]\ndependencies = ["fastapi>=0.100"]\n',
                encoding="utf-8",
            )

            self.assertEqual(infer_disco.detect_framework(root, {}), "fastapi")

    def test_single_monorepo_app_is_auto_selected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            app = root / "apps" / "web"
            app.mkdir(parents=True)
            self.write_json(
                app / "package.json",
                {"dependencies": {"next": "latest"}, "scripts": {"start": "next start"}},
            )

            selected, app_path, warnings, blockers = infer_disco.resolve_app_root(root, None)

            self.assertEqual(selected, app)
            self.assertEqual(app_path, "apps/web")
            self.assertTrue(warnings)
            self.assertEqual(blockers, [])

    def test_multiple_monorepo_apps_are_a_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("web", "admin"):
                self.write_json(
                    root / "apps" / name / "package.json",
                    {"dependencies": {"vite": "latest"}, "scripts": {"build": "vite build"}},
                )

            _, _, _, blockers = infer_disco.resolve_app_root(root, None)

            self.assertTrue(blockers)

    def test_prebuilt_image_allows_dockerfile_free_app(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_json(root / "package.json", {"scripts": {"start": "node server.js"}})

            result = self.run_cli(root, "--image", "node:22", "--port", "3000")

            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            config = json.loads((root / "disco.json").read_text())
            self.assertEqual(config["services"]["web"]["image"], "node:22")

    def test_build_command_requires_a_base_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            result = self.run_cli(root, "--build-command", "npm ci && npm run build")

            self.assertEqual(result.returncode, 2)
            self.assertIn("requires --image", result.stdout)

    def test_blocker_prevents_output_but_writes_requested_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.write_json(root / "package.json", {"scripts": {"start": "node server.js"}})
            report = root / "analysis.md"

            result = self.run_cli(root, "--report", str(report))

            self.assertEqual(result.returncode, 2)
            self.assertFalse((root / "disco.json").exists())
            self.assertTrue(report.exists())
            self.assertIn("needs a root Dockerfile", report.read_text())

    def test_invalid_cron_interval_is_not_emitted(self) -> None:
        commands = infer_disco.detect_cron_commands(
            {"cron:every90min": "node task.js"},
            "npm",
        )

        self.assertIsNone(commands[0][2])

    def test_sensitive_fields_are_blockers_and_are_redacted_in_reports(self) -> None:
        config = {
            "version": "1.0",
            "services": {"web": {"port": 8000, "image": "example/app:latest"}},
            "apiKey": "secret-value",
        }

        _, blockers = infer_disco.validate_disco_config(config, Path("/repo"))
        report = infer_disco.render_report(
            {"facts": {}, "warnings": [], "blockers": blockers},
            config,
        )

        self.assertTrue(blockers)
        self.assertNotIn("secret-value", report)
        self.assertIn("<redacted>", report)


if __name__ == "__main__":
    unittest.main()
