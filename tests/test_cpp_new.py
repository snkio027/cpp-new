import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CPP_NEW = REPOSITORY_ROOT / "cpp-new"


def run_cpp_new(working_directory, *arguments, executable=CPP_NEW):
    return subprocess.run(
        [str(executable), *arguments],
        cwd=working_directory,
        check=False,
        capture_output=True,
        text=True,
    )


class CppNewTests(unittest.TestCase):
    def test_generates_app_with_replaced_name_and_identifier(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)

            result = run_cpp_new(workspace, "app", "sensor-hub", "--no-git")

            self.assertEqual(result.returncode, 0, result.stderr)
            project = workspace / "sensor-hub"
            self.assertTrue((project / "CMakeLists.txt").is_file())
            self.assertFalse((project / ".git").exists())
            self.assertIn("project(sensor_hub LANGUAGES CXX)", (project / "CMakeLists.txt").read_text())
            self.assertIn("Hello from sensor-hub!", (project / "src" / "main.cpp").read_text())
            self.assertEqual(
                (project / ".cpp-new.toml").read_text(),
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

            result = run_cpp_new(workspace, "app", "demo")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((workspace / "demo" / ".git").is_dir())

    def test_accepts_an_existing_empty_destination(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            (workspace / "demo").mkdir()

            result = run_cpp_new(workspace, "app", "demo", "--no-git")

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((workspace / "demo" / "CMakeLists.txt").is_file())

    def test_rejects_invalid_names_without_creating_a_destination(self):
        invalid_names = ("Demo", "demo_app", "1demo", "demo/app", ".")

        for invalid_name in invalid_names:
            with self.subTest(name=invalid_name), tempfile.TemporaryDirectory() as temporary_directory:
                workspace = Path(temporary_directory)

                result = run_cpp_new(workspace, "app", invalid_name, "--no-git")

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

            result = run_cpp_new(workspace, "app", "demo", "--no-git")

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(sentinel.read_text(), "keep\n")
            self.assertEqual(list(destination.iterdir()), [sentinel])

    def test_rejects_an_existing_file_destination(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            destination = workspace / "demo"
            destination.write_text("keep\n")

            result = run_cpp_new(workspace, "app", "demo", "--no-git")

            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(destination.read_text(), "keep\n")

    def test_rejects_a_symbolic_link_destination(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            target = workspace / "target"
            target.mkdir()
            (workspace / "demo").symlink_to(target, target_is_directory=True)

            result = run_cpp_new(workspace, "app", "demo", "--no-git")

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symbolic link", result.stderr)
            self.assertEqual(list(target.iterdir()), [])

    def test_reports_a_missing_bundled_fixture_without_creating_a_destination(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            isolated_executable = workspace / "cpp-new"
            shutil.copy2(CPP_NEW, isolated_executable)
            isolated_executable.chmod(0o755)

            result = run_cpp_new(workspace, "app", "demo", executable=isolated_executable)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("bundled app fixture is missing", result.stderr)
            self.assertFalse((workspace / "demo").exists())

    def test_generated_app_configures_builds_and_tests(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            workspace = Path(temporary_directory)
            generation = run_cpp_new(workspace, "app", "e2e-demo", "--no-git")
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
