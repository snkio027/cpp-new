# Implementation Plan

This plan intentionally starts small.

Do not implement future extensibility before the basic developer experience is proven.

## Milestone 0 — Repository baseline

Keep only the minimum project documentation and source/test structure required by the chosen implementation language.

Do not add CI, release automation or packaging until there is executable behavior worth validating.

Exit condition:

- architecture is readable;
- first implementation task is unambiguous.

## Milestone 1 — Canonical app template

Build one C++ application template manually before writing general generator logic.

Expected project shape should stay small, roughly:

```text
CMakeLists.txt
CMakePresets.json
.clangd
.clang-format
.clang-tidy
.gitignore
.cpp-new.toml
src/main.cpp
tests/
cmake/
```

Avoid helper CMake modules unless they remove real duplication or isolate compiler-specific logic.

Required validation:

```bash
cmake --workflow --preset dev
```

Where supported:

```bash
cmake --workflow --preset san
```

Also verify:

```text
compile_commands.json exists
CTest finds and runs the smoke test
clangd can consume the development compilation database
```

Do not implement `lib` or `header-only` yet.

## Milestone 2 — Minimal generator

Implement only what is needed to instantiate the proven app template:

```text
parse command
validate project name
derive canonical identifier
check destination
copy/render files
write provenance
optionally git init
report next command
```

Generation must be offline.

Prefer simple token replacement over a template framework.

Required command:

```bash
cpp-new app <name>
```

Optional:

```bash
--no-git
```

Nothing else is required.

## Milestone 3 — End-to-end verification

Test the generated artifact:

```text
generate
 -> configure
 -> build
 -> test
```

Also test failure cases:

```text
invalid name
non-empty destination
unsafe path
missing bundled template resource
```

A failed generation must not overwrite existing user files.

## Milestone 4 — Add library template

Only after the app flow is stable.

Add:

```bash
cpp-new lib <name>
```

The library must have real library semantics:

```text
public headers
compiled implementation
namespaced CMake alias
consumer test
```

Do not redesign the generator unless the library exposes a concrete problem in the existing implementation.

## Milestone 5 — Add header-only template

Add:

```bash
cpp-new header-only <name>
```

Use CMake interface-library semantics.

Again, extend the existing implementation narrowly.

## After v0.1

Evaluate actual personal usage before adding features.

Potential next additions, only if they solve observed friction:

```text
vcpkg profile
Conan profile
better inspect command
release packaging
```

C++26, Modules, ROS and CUDA remain separate decisions.

## v0.1 Definition of Done

`cpp-new` is successful when:

```bash
cpp-new app demo
cd demo
cmake --workflow --preset dev
```

works predictably, the generated project is pleasant to edit, and the implementation is small enough to understand in one sitting.

The goal is not feature count.

The goal is removing repetitive C++ project setup without creating a new layer of tooling complexity.
