import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
UV = shutil.which("uv")


class WheelReleaseTests(unittest.TestCase):
    def run_checked(self, command, *, cwd, env=None):
        result = subprocess.run(
            command,
            cwd=cwd,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def test_installed_wheel_generates_a_working_project(self):
        self.assertIsNotNone(UV, "uv is required for the installed-wheel release test")

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            dist = root / "dist"
            environment = os.environ.copy()
            environment.update(
                {
                    "UV_CACHE_DIR": str(root / "uv-cache"),
                    "UV_NO_PROGRESS": "1",
                    "UV_OFFLINE": "1",
                    "UV_TOOL_BIN_DIR": str(root / "bin"),
                    "UV_TOOL_DIR": str(root / "tools"),
                }
            )

            self.run_checked(
                [UV, "build", "--no-sources", "--out-dir", str(dist)],
                cwd=REPOSITORY_ROOT,
                env=environment,
            )

            wheel = dist / "cxx_init-0.1.0-py3-none-any.whl"
            source_distribution = dist / "cxx_init-0.1.0.tar.gz"
            self.assertTrue(wheel.is_file())
            self.assertTrue(source_distribution.is_file())

            fixture_root = REPOSITORY_ROOT / "src" / "cxx_init" / "fixtures" / "canonical-app"
            expected_fixture_files = {
                str(Path("cxx_init/fixtures/canonical-app") / path.relative_to(fixture_root))
                for path in fixture_root.rglob("*")
                if path.is_file()
            }

            with zipfile.ZipFile(wheel) as archive:
                wheel_files = set(archive.namelist())
                metadata = archive.read("cxx_init-0.1.0.dist-info/METADATA").decode()
                entry_points = archive.read("cxx_init-0.1.0.dist-info/entry_points.txt").decode()
            self.assertTrue(expected_fixture_files.issubset(wheel_files))
            self.assertIn("cxx_init-0.1.0.dist-info/licenses/LICENSE", wheel_files)
            self.assertIn("License-Expression: MIT\n", metadata)
            self.assertIn("Requires-Python: >=3.10\n", metadata)
            self.assertNotIn("Requires-Dist:", metadata)
            self.assertEqual(entry_points.rstrip(), "[console_scripts]\ncxx = cxx_init.cli:main")

            with tarfile.open(source_distribution, "r:gz") as archive:
                source_files = set(archive.getnames())
            source_prefix = "cxx_init-0.1.0/"
            self.assertTrue(
                {source_prefix + "src/" + path for path in expected_fixture_files}.issubset(
                    source_files
                )
            )
            self.assertIn(source_prefix + "LICENSE", source_files)
            self.assertIn(source_prefix + "pyproject.toml", source_files)

            self.run_checked(
                [UV, "tool", "install", "--python", sys.executable, str(wheel)],
                cwd=root,
                env=environment,
            )

            executable = root / "bin" / ("cxx.exe" if os.name == "nt" else "cxx")
            version = self.run_checked([str(executable), "--version"], cwd=root)
            self.assertEqual(version.stdout, "cxx 0.1.0\n")

            workspace = root / "workspace"
            workspace.mkdir()
            generation = self.run_checked(
                [str(executable), "init", "release-smoke", "--no-git"],
                cwd=workspace,
            )
            self.assertIn("Created C++ project: release-smoke", generation.stdout)

            project = workspace / "release-smoke"
            self.assertEqual(
                (project / ".cxx.toml").read_text(),
                'schema = 1\ntemplate = "app"\nlanguage = "c++23"\n',
            )

            self.run_checked(["cmake", "--workflow", "--preset", "dev"], cwd=project)
            self.run_checked(["cmake", "--workflow", "--preset", "san"], cwd=project)

            commands = json.loads((project / "build" / "dev" / "compile_commands.json").read_text())
            compiled_sources = {Path(command["file"]).name for command in commands}
            self.assertEqual(compiled_sources, {"main.cpp", "smoke_test.cpp"})


if __name__ == "__main__":
    unittest.main()
