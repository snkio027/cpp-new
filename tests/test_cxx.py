import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CLI = REPOSITORY_ROOT / "src" / "cxx_init" / "cli.py"


def run_cxx(working_directory, *arguments, executable=CLI):
    return subprocess.run(
        [sys.executable, str(executable), *arguments],
        cwd=working_directory,
        check=False,
        capture_output=True,
        text=True,
    )


class CxxTests(unittest.TestCase):
    def test_reports_version(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            result = run_cxx(Path(temporary_directory), "--version")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "cxx 0.1.0\n")

    def test_rejects_the_previous_app_command(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)

            result = run_cxx(workspace, "app", "demo", "--no-git")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid choice: 'app'", result.stderr)
            self.assertFalse((workspace / "demo").exists())

    def test_generates_app_with_replaced_name_and_identifier(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)

            result = run_cxx(workspace, "init", "sensor-hub", "--no-git")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                result.stdout,
                "Created C++ project: sensor-hub\n\n"
                "Next:\n"
                "  cd sensor-hub\n"
                "  cmake --workflow --preset dev\n",
            )
            project = workspace / "sensor-hub"
            self.assertTrue((project / "CMakeLists.txt").is_file())
            self.assertFalse((project / ".git").exists())
            self.assertIn("project(sensor_hub LANGUAGES CXX)", (project / "CMakeLists.txt").read_text())
            self.assertIn("Hello from sensor-hub!", (project / "src" / "main.cpp").read_text())
            self.assertEqual(
                (project / ".cxx.toml").read_text(),
                'schema = 1\ntemplate = "app"\nlanguage = "c++23"\n',
            )

            generated_text = "\n".join(
                generated_file.read_text()
                for generated_file in project.rglob("*")
                if generated_file.is_file()
            )
            self.assertNotIn("robot-runtime", generated_text)
            self.assertNotIn("robot_runtime", generated_text)

    def test_initializes_git_by_default(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)

            result = run_cxx(workspace, "init", "demo")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((workspace / "demo" / ".git").is_dir())

    def test_accepts_an_existing_empty_destination(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            (workspace / "demo").mkdir()

            result = run_cxx(workspace, "init", "demo", "--no-git")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((workspace / "demo" / "CMakeLists.txt").is_file())

    def test_rejects_invalid_names_without_creating_a_destination(self):
        invalid_names = ("Demo", "demo_app", "1demo", "demo/app", ".")

        for invalid_name in invalid_names:
            with self.subTest(name=invalid_name), tempfile.TemporaryDirectory() as temporary_directory:
                workspace = Path(temporary_directory)

                result = run_cxx(workspace, "init", invalid_name, "--no-git")

                self.assertNotEqual(result.returncode, 0)
                self.assertIn("invalid project name", result.stderr)
                self.assertEqual(list(workspace.iterdir()), [])

    def test_rejects_a_nonempty_destination_without_overwriting_it(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            destination = workspace / "demo"
            destination.mkdir()
            sentinel = destination / "keep.txt"
            sentinel.write_text("keep\n")

            result = run_cxx(workspace, "init", "demo", "--no-git")

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(), "keep\n")
            self.assertEqual(list(destination.iterdir()), [sentinel])

    def test_rejects_an_existing_file_destination(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            destination = workspace / "demo"
            destination.write_text("keep\n")

            result = run_cxx(workspace, "init", "demo", "--no-git")

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(destination.read_text(), "keep\n")

    def test_rejects_a_symbolic_link_destination(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            target = workspace / "target"
            target.mkdir()
            (workspace / "demo").symlink_to(target, target_is_directory=True)

            result = run_cxx(workspace, "init", "demo", "--no-git")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symbolic link", result.stderr)
            self.assertEqual(list(target.iterdir()), [])

    def test_reports_a_missing_bundled_fixture_without_creating_a_destination(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            isolated_executable = workspace / "cli.py"
            shutil.copy2(CLI, isolated_executable)

            result = run_cxx(workspace, "init", "demo", executable=isolated_executable)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("bundled app fixture is missing", result.stderr)
            self.assertFalse((workspace / "demo").exists())

    def test_generated_app_configures_builds_and_tests(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            generation = run_cxx(workspace, "init", "e2e-demo", "--no-git")
            self.assertEqual(generation.returncode, 0, generation.stderr)

            project = workspace / "e2e-demo"
            workflow = subprocess.run(
                ["cmake", "--workflow", "--preset", "dev"],
                cwd=project,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(workflow.returncode, 0, workflow.stdout + workflow.stderr)
            compilation_database = project / "build" / "dev" / "compile_commands.json"
            commands = json.loads(compilation_database.read_text())
            compiled_sources = {Path(command["file"]).name for command in commands}
            self.assertEqual(compiled_sources, {"main.cpp", "smoke_test.cpp"})


if __name__ == "__main__":
    unittest.main()
