# cpp-new

A small personal tool for creating clean, modern C++ projects without repeating the same setup work.

## Goal

The repository ships a small `cxx` command that should make this workflow pleasant:

```bash
cxx init robot-runtime
cd robot-runtime
cmake --workflow --preset dev
```

The generated project should be understandable without `cxx` and should use normal C++ tooling directly.

## Design priorities

1. Personal developer experience first.
2. Small, readable implementation.
3. Minimal generated files.
4. No hidden host mutation.
5. No build-system wrapper.
6. No network requirement during project creation.
7. Prefer boring, inspectable code over framework-heavy abstractions.

## Initial scope

Start with one canonical `app` template.

After it is stable, add:

```text
lib
header-only
```

Initial generated projects use:

```text
C++23
Modern target-centric CMake
CMake Presets / Workflow Presets
Ninja
clangd
clang-format
clang-tidy
CTest
ASan / UBSan where supported
compile_commands.json
```

Dependency managers, C++26, Modules, ROS, CUDA, packaging, benchmarking and fuzzing are intentionally deferred.

## Repository documents

- `AGENTS.md` — rules for Codex and other coding agents.
- `docs/architecture.md` — architecture and boundaries.
- `docs/implementation-plan.md` — current implementation sequence.

## Current implementation

The canonical `app` project is available through the minimal generator:

```bash
./cxx init robot-runtime
```

The generator directly instantiates the proven fixture. It does not provide a general template
framework, build commands or dependency management.
