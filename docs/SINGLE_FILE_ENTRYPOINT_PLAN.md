# Single-File Entrypoint & Build Include System

## Implementation Plan

This document outlines the complete implementation plan for supporting single-file entrypoints and a robust build include/exclude system in Dockrion.

---

## Table of Contents

1. [Overview](#overview)
2. [Current Behavior](#current-behavior)
3. [Required Changes Summary](#required-changes-summary)
4. [Detailed Implementation Plan](#detailed-implementation-plan)
5. [Schema Extensions](#schema-extensions)
6. [Module Detection Logic](#module-detection-logic)
7. [Build Resolution System](#build-resolution-system)
8. [Conflict Resolution Rules](#conflict-resolution-rules)
9. [Edge Cases & Handling](#edge-cases--handling)
10. [Files to Modify](#files-to-modify)
11. [Testing Requirements](#testing-requirements)
12. [User Documentation](#user-documentation)

---

## Overview

### Goals

1. **Support single-file entrypoints**: Allow `module:function` where `module.py` is a single Python file (not a package directory)
2. **Support additional includes**: Allow explicit specification of additional files/directories needed for the build
3. **Auto-detect imports**: Optionally parse Python files to detect local dependencies
4. **Robust conflict resolution**: Handle include/exclude conflicts with clear rules
5. **Match Python semantics**: Package takes precedence over file when both exist

### Entrypoint Format

```
module.path:callable_name
```

Examples:
- `agent:run_agent` → Single file `agent.py` or package `agent/`
- `app.main:build_graph` → Module `app/main.py`
- `src.app:handler` → Package `src/app/__init__.py` or module `src/app.py`

---

## Current Behavior

### Current Implementation

**`renderer.py` - `_get_agent_directories()`**:
- Extracts top-level module from entrypoint
- Always assumes it's a directory
- Returns list of directories to copy

**`Dockerfile.j2`**:
- Uses `COPY {{ dir }}/ /app/{{ dir }}/` syntax
- Only copies directories, not single files

**`path_utils.py` - `resolve_module_path()`**:
- Walks up directory tree to find module
- Doesn't distinguish between files and directories

### Current Limitations

1. Single-file modules (`module.py`) not supported
2. No way to include additional directories/files
3. No exclude patterns
4. No import auto-detection
5. Doesn't handle `__init__.py` entry points explicitly

---

## Required Changes Summary

| Component | Change |
|-----------|--------|
| Schema (`dockfile_v1.py`) | Add `BuildConfig` with `include`, `exclude`, `auto_detect_imports` |
| Renderer (`renderer.py`) | Add `_get_agent_files()`, update context building, add `BuildResolver` |
| Dockerfile template | Add logic for single files, combined includes |
| Path utils | Update to detect file vs directory |
| New module | `build_resolver.py` for conflict resolution |
| New module | `import_detector.py` for AST-based import detection |

---

## Detailed Implementation Plan

### Phase 1: Core Single-File Support

**Files to modify:**
- `packages/sdk-python/dockrion_sdk/templates/renderer.py`
- `packages/sdk-python/dockrion_sdk/templates/dockerfiles/Dockerfile.j2`
- `packages/common-py/dockrion_common/path_utils.py`

**Changes:**

1. Add `_get_agent_files()` method to detect single-file modules
2. Update `_get_agent_directories()` to exclude single-file modules
3. Add `agent_files` to template context
4. Update Dockerfile template to copy single files

### Phase 2: Build Configuration Schema

**Files to modify:**
- `packages/schema/dockrion_schema/dockfile_v1.py`

**Changes:**

1. Add `BuildIncludeConfig` model
2. Add `BuildConfig` model
3. Add `build` field to `DockSpec`

### Phase 3: Build Resolver System

**New file:**
- `packages/sdk-python/dockrion_sdk/build/resolver.py`

**Changes:**

1. Implement `BuildResolver` class
2. Implement conflict detection and resolution
3. Implement validation rules

### Phase 4: Import Auto-Detection (Optional Feature)

**New file:**
- `packages/sdk-python/dockrion_sdk/build/import_detector.py`

**Changes:**

1. Implement AST-based import parsing
2. Implement recursive dependency detection
3. Implement circular import handling

---

## Schema Extensions

### New Models

```python
# packages/schema/dockrion_schema/dockfile_v1.py

class BuildIncludeConfig(BaseModel):
    """
    Files and directories to include in Docker build.
    
    These are added to the auto-detected entrypoint module.
    """
    
    directories: List[str] = []
    """Additional directories to copy (e.g., ["utils", "models"])"""
    
    files: List[str] = []
    """Additional files to copy (e.g., ["config.yaml", "constants.py"])"""
    
    patterns: List[str] = []
    """Glob patterns to match files (e.g., ["*.json", "data/**"])"""
    
    model_config = ConfigDict(extra="allow")


class BuildConfig(BaseModel):
    """
    Build configuration for Docker image creation.
    
    Controls what gets copied into the Docker image beyond
    the auto-detected entrypoint module.
    """
    
    include: Optional[BuildIncludeConfig] = None
    """Additional files/directories to include"""
    
    exclude: List[str] = []
    """Patterns to exclude (e.g., ["tests/", "**/__pycache__"])"""
    
    auto_detect_imports: bool = False
    """If True, parse Python files to detect local imports"""
    
    model_config = ConfigDict(extra="allow")


# Update DockSpec
class DockSpec(BaseModel):
    # ... existing fields ...
    build: Optional[BuildConfig] = None  # NEW
```

### Dockfile Example

```yaml
version: "1.0"
agent:
  name: my-agent
  entrypoint: agent:process_request
  framework: custom

build:
  include:
    directories:
      - utils
      - models
      - prompts
    files:
      - config.yaml
      - constants.py
    patterns:
      - "data/*.json"
  exclude:
    - "tests/"
    - "**/__pycache__"
    - "*.pyc"
  auto_detect_imports: false

io_schema:
  input:
    properties:
      query:
        type: string
  output:
    properties:
      result:
        type: string

expose:
  port: 8080
```

---

## Module Detection Logic

### Module Type Enumeration

```python
class ModuleType(Enum):
    PACKAGE = "package"      # Directory with __init__.py
    FILE = "file"            # Single .py file
    NAMESPACE = "namespace"  # Directory without __init__.py (PEP 420)
    AMBIGUOUS = "ambiguous"  # Both file and package exist
    NOT_FOUND = "not_found"
```

### Detection Rules

| Check | Result |
|-------|--------|
| `module/` exists AND `module.py` exists | AMBIGUOUS (package wins) |
| `module/` exists with `__init__.py` | PACKAGE |
| `module/` exists without `__init__.py` | NAMESPACE |
| Only `module.py` exists | FILE |
| Neither exists | NOT_FOUND |

### Python Semantics Compliance

**Rule:** When both `module.py` and `module/` exist, Python imports the **package** (directory), not the file.

Our detection follows this rule:
- AMBIGUOUS → Copy directory, warn user
- User should rename one to avoid confusion

### Detection Function

```python
def detect_module_type(
    module_name: str,
    parent_dir: Path
) -> ModuleInfo:
    """
    Detect whether a module is a package, file, or ambiguous.
    
    Follows Python's import semantics.
    """
    dir_path = parent_dir / module_name
    file_path = parent_dir / f"{module_name}.py"
    init_path = dir_path / "__init__.py"
    
    dir_exists = dir_path.is_dir()
    file_exists = file_path.is_file()
    has_init = init_path.is_file() if dir_exists else False
    
    if dir_exists and file_exists:
        return ModuleInfo(
            name=module_name,
            type=ModuleType.AMBIGUOUS,
            path=dir_path,
            warning=f"Both '{module_name}.py' and '{module_name}/' exist. "
                    f"Package takes precedence (Python semantics)."
        )
    
    if dir_exists and has_init:
        return ModuleInfo(name=module_name, type=ModuleType.PACKAGE, path=dir_path)
    
    if dir_exists and not has_init:
        return ModuleInfo(
            name=module_name,
            type=ModuleType.NAMESPACE,
            path=dir_path,
            warning=f"'{module_name}/' is a namespace package (no __init__.py)."
        )
    
    if file_exists:
        return ModuleInfo(name=module_name, type=ModuleType.FILE, path=file_path)
    
    return ModuleInfo(
        name=module_name,
        type=ModuleType.NOT_FOUND,
        path=parent_dir / module_name,
        warning=f"Module '{module_name}' not found."
    )
```

---

## Build Resolution System

### Resolution Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    Build Include Resolution                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. ENTRYPOINT MODULE (always required)                         │
│     ├── Extract from agent.entrypoint                           │
│     ├── Extract from agent.handler                              │
│     └── Detect file vs directory                                │
│                                                                  │
│  2. AUTO-DETECT IMPORTS (if auto_detect_imports: true)          │
│     ├── Parse Python files with AST                             │
│     ├── Find local imports                                      │
│     ├── Recursively analyze dependencies                        │
│     └── Handle circular imports (skip visited)                  │
│                                                                  │
│  3. EXPLICIT INCLUDES                                            │
│     ├── build.include.directories                               │
│     ├── build.include.files                                     │
│     └── build.include.patterns (resolved to actual files)       │
│                                                                  │
│  4. COMBINE & DEDUPLICATE                                        │
│     └── Union of all sources (using sets)                       │
│                                                                  │
│  5. VALIDATION                                                   │
│     ├── Entrypoint not in exclude? (ERROR if violated)          │
│     ├── Auto-detected imports not in exclude? (ERROR)           │
│     ├── Explicit includes not in exclude? (WARNING)             │
│     └── All items exist? (WARNING if not)                       │
│                                                                  │
│  6. APPLY EXCLUDES                                               │
│     ├── Filter out matching patterns                            │
│     └── Exclude wins over explicit include (with warning)       │
│                                                                  │
│  7. FINAL OUTPUT                                                 │
│     ├── Sorted list of directories                              │
│     └── Sorted list of files                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### BuildResolver Class

```python
@dataclass
class BuildResolution:
    """Result of build include/exclude resolution."""
    directories: List[str]
    files: List[str]
    warnings: List[str]


class BuildResolver:
    """Resolves what to include in Docker build."""
    
    def __init__(self, spec: DockSpec, project_root: Path):
        self.spec = spec
        self.project_root = project_root
        self.warnings: List[str] = []
    
    def resolve(self) -> BuildResolution:
        """Resolve final list of files/directories to include."""
        all_dirs: Set[str] = set()
        all_files: Set[str] = set()
        
        # 1. Entrypoint module (required)
        ep_dirs, ep_files = self._get_entrypoint_includes()
        all_dirs.update(ep_dirs)
        all_files.update(ep_files)
        
        # 2. Auto-detect imports (if enabled)
        if self._is_auto_detect_enabled():
            auto_dirs, auto_files = self._get_auto_detected_imports()
            all_dirs.update(auto_dirs)
            all_files.update(auto_files)
        
        # 3. Explicit includes
        explicit_dirs, explicit_files = self._get_explicit_includes()
        all_dirs.update(explicit_dirs)
        all_files.update(explicit_files)
        
        # 4. Get exclude patterns
        excludes = self._get_exclude_patterns()
        
        # 5. Validate conflicts
        self._validate_entrypoint_not_excluded(ep_dirs, ep_files, excludes)
        if self._is_auto_detect_enabled():
            self._validate_auto_detected_not_excluded(auto_dirs, auto_files, excludes)
        self._warn_explicit_include_conflicts(explicit_dirs, explicit_files, excludes)
        self._validate_existence(all_dirs, all_files)
        
        # 6. Apply excludes
        final_dirs = self._apply_excludes(all_dirs, excludes)
        final_files = self._apply_excludes(all_files, excludes)
        
        return BuildResolution(
            directories=sorted(final_dirs),
            files=sorted(final_files),
            warnings=self.warnings
        )
```

---

## Conflict Resolution Rules

### Priority Table

| Conflict Type | Behavior | User Notification |
|---------------|----------|-------------------|
| Include + Exclude (same item) | **Exclude wins** | ⚠️ Warning |
| Auto-detect + Exclude | **Error** | ❌ Build fails |
| Entrypoint + Exclude | **Error** | ❌ Build fails |
| Auto-detect + Explicit Include | **Both included** (union) | None |
| Duplicate entries | **Deduplicated** | None |
| Non-existent includes | **Included anyway** | ⚠️ Warning |
| Pattern overlap | **Deduplicated** | None |
| Circular imports | **Handled** (skip visited) | None |
| Both file and dir exist | **Directory wins** | ⚠️ Warning |

### Rationale

1. **Exclude > Include**: Safety first. If user explicitly excludes something, respect it.
2. **Error on critical conflicts**: Entrypoint and auto-detected imports are required. Can't exclude them.
3. **Warning on non-critical**: Explicit includes that are also excluded get warned, not errored.
4. **Python semantics for ambiguity**: Package > file, matches Python's import behavior.

---

## Edge Cases & Handling

### Entrypoint Formats

| Entrypoint | Structure | What Gets Copied | Notes |
|------------|-----------|------------------|-------|
| `app:func` | `app.py` | `app.py` | Single file |
| `app:func` | `app/__init__.py` | `app/` | Package |
| `app:func` | Both exist | `app/` | Package wins + warning |
| `src.app:func` | `src/app/__init__.py` | `src/` | Nested package |
| `src.app:func` | `src/app.py` | `src/` | Module inside package |
| `src.app:func` | Both exist | `src/` | Package wins + warning |
| `src.app.mod:func` | `src/app/mod.py` | `src/` | Deeply nested |

### `__init__.py` Entry Points

For `src.app:build_agent` where `build_agent` is defined in `src/app/__init__.py`:

1. Parse module path: `src.app`
2. Detect `src/app/` is a package (has `__init__.py`)
3. Copy `src/` directory
4. Runtime imports `src.app` which loads `__init__.py`

### Invalid Configurations

| Configuration | Error |
|---------------|-------|
| `src.app:func` with only `src.py` | Error: Can't have dots if top-level is a file |
| Entrypoint module in exclude | Error: Cannot exclude entrypoint |
| Auto-detected import in exclude | Error: Remove from exclude or disable auto-detect |

---

## Files to Modify

### Core Changes

| File | Changes |
|------|---------|
| `packages/schema/dockrion_schema/dockfile_v1.py` | Add `BuildConfig`, `BuildIncludeConfig`, add `build` to `DockSpec` |
| `packages/sdk-python/dockrion_sdk/templates/renderer.py` | Add `_get_agent_files()`, update `build()` context, integrate `BuildResolver` |
| `packages/sdk-python/dockrion_sdk/templates/dockerfiles/Dockerfile.j2` | Add logic for `all_directories`, `all_files` |
| `packages/common-py/dockrion_common/path_utils.py` | Update `resolve_module_path()` for file detection |

### New Files

| File | Purpose |
|------|---------|
| `packages/sdk-python/dockrion_sdk/build/__init__.py` | Package init |
| `packages/sdk-python/dockrion_sdk/build/resolver.py` | `BuildResolver` class |
| `packages/sdk-python/dockrion_sdk/build/module_detector.py` | `detect_module_type()`, `ModuleType` enum |
| `packages/sdk-python/dockrion_sdk/build/import_detector.py` | AST-based import detection |
| `packages/sdk-python/dockrion_sdk/build/pattern_resolver.py` | Glob pattern resolution |

---

## Testing Requirements

### Unit Tests

1. **Module Detection** (`test_module_detector.py`)
   - Test PACKAGE detection
   - Test FILE detection
   - Test NAMESPACE detection
   - Test AMBIGUOUS detection (both exist)
   - Test NOT_FOUND handling

2. **Build Resolver** (`test_build_resolver.py`)
   - Test entrypoint extraction
   - Test explicit includes
   - Test exclude patterns
   - Test conflict detection
   - Test deduplication

3. **Import Detection** (`test_import_detector.py`)
   - Test simple imports
   - Test from imports
   - Test recursive detection
   - Test circular import handling

### Integration Tests

1. **SDK Build** (`test_sdk_build_integration.py`)
   - Build with single-file entrypoint
   - Build with package entrypoint
   - Build with explicit includes
   - Build with excludes
   - Build with auto-detect

### End-to-End Tests

1. **Docker Build** (`test_docker_e2e.py`)
   - Deploy agent with single-file entrypoint
   - Deploy agent with additional directories
   - Verify runtime imports work correctly

### Edge Case Tests

1. **Ambiguity** (`test_ambiguity.py`)
   - Both `app.py` and `app/` exist
   - Entrypoint in exclude
   - Pattern overlap

---

## User Documentation

### Entrypoint Format Guide

```markdown
## Entrypoint Configuration

The `entrypoint` field specifies how to load your agent.

### Format

```
module.path:callable_name
```

### Examples

| Your Structure | Entrypoint | What Dockrion Copies |
|----------------|------------|----------------------|
| `agent.py` | `agent:run` | `agent.py` |
| `app/__init__.py` | `app:main` | `app/` directory |
| `src/app/__init__.py` | `src.app:build` | `src/` directory |
| `src/app/graph.py` | `src.app.graph:create` | `src/` directory |

### Single-File vs Package

- **Single file**: `module.py` in project root
- **Package**: `module/` directory with `__init__.py`

If both exist, Dockrion follows Python's behavior: **package takes precedence**.
```

### Build Configuration Guide

```markdown
## Build Configuration

Control what gets copied into your Docker image.

### Basic Example

```yaml
build:
  include:
    directories:
      - utils
      - models
    files:
      - config.yaml
  exclude:
    - tests/
    - "**/__pycache__"
```

### Auto-Detect Imports

```yaml
build:
  auto_detect_imports: true
```

When enabled, Dockrion parses your Python files and automatically
includes any local modules that are imported.

### Conflict Resolution

- **Exclude wins over include** (with warning)
- **Cannot exclude entrypoint module** (error)
- **Cannot exclude auto-detected imports** (error)

### Patterns

Glob patterns are supported:
- `*.json` - All JSON files in root
- `data/**` - Everything in data/ recursively
- `**/__pycache__` - All __pycache__ directories
```

---

## Implementation Order

### Phase 1: Core (MVP)
1. Schema extension (`BuildConfig`)
2. Module detection (`detect_module_type`)
3. Renderer updates (`_get_agent_files`)
4. Dockerfile template updates
5. Basic tests

### Phase 2: Build Includes
1. `BuildResolver` class
2. Explicit include handling
3. Exclude pattern handling
4. Conflict resolution
5. Integration tests

### Phase 3: Auto-Detection
1. Import detector (`detect_local_imports`)
2. Recursive analysis
3. Circular import handling
4. E2E tests

### Phase 4: Polish
1. CLI output improvements
2. User documentation
3. Error message improvements
4. Edge case tests

---

## CLI Output Example

```
$ dockrion build

📦 Resolving build includes...

  Entrypoint: agent:process_request
    └── agent.py (single file)
    
  Auto-detected imports: (disabled)
    
  Explicit includes:
    ├── utils/ (directory)
    ├── models/ (directory)
    └── config.yaml (file)
    
  Excludes applied:
    └── tests/, **/__pycache__
    
  ⚠️  Warning: 'helpers.py' is in both include and exclude. Excluding.
  
  Final includes:
    Directories: models/, utils/
    Files: agent.py, config.yaml

🐳 Building Docker image: dockrion/my-agent:dev
   Step 1/12: FROM python:3.12-slim AS base
   ...

✅ Successfully built image: dockrion/my-agent:dev
```

---

## Acceptance Criteria

- [ ] `_get_agent_directories()` correctly detects single-file modules
- [ ] `_get_agent_files()` returns list of single-file modules
- [ ] Template context includes `agent_files`, `all_directories`, `all_files`
- [ ] Dockerfile template correctly copies single files
- [ ] `BuildConfig` schema accepted in Dockfile
- [ ] Explicit includes work correctly
- [ ] Exclude patterns filter results
- [ ] Include/exclude conflicts show warnings
- [ ] Entrypoint in exclude raises error
- [ ] Auto-detect in exclude raises error
- [ ] Package vs file ambiguity shows warning
- [ ] `__init__.py` entry points work correctly
- [ ] All existing directory-based entrypoints still work
- [ ] Unit test coverage for all new code
- [ ] Integration tests pass
- [ ] Documentation updated

---

## References

- [PEP 328 - Imports: Multi-Line and Absolute/Relative](https://peps.python.org/pep-0328/)
- [PEP 420 - Implicit Namespace Packages](https://peps.python.org/pep-0420/)
- [Python Import System Documentation](https://docs.python.org/3/reference/import.html)

