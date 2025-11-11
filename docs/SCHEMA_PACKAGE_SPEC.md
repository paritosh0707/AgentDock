# AgentDock Schema Package Specification

## Purpose

The `agentdock-schema` package is the **type system and validation layer** for AgentDock. It transforms the Dockfile YAML specification into executable, type-safe Pydantic models that every service depends on.

**One sentence summary:** Schema ensures all services agree on what constitutes a valid Dockfile, catching errors before deployment instead of at runtime.

---

## Why Schema Package Exists

### The Core Problem

Without a centralized schema package:
- **CLI validates differently than Builder** → users see "valid" but deployment fails
- **Security vulnerabilities** → malicious entrypoints or regex patterns reach production
- **No IDE support** → developers guess Dockfile syntax
- **Maintenance nightmare** → 6+ services reimplementing the same validation

### The Solution

One schema package → all services use identical validation → consistency + security + developer experience.

**PRD Evidence:** Section 3.1 G-1 "Unified Deployment Contract", Section 6.3.2 "Config Parser & Schema Engine"

---

## Architecture Position

```
Schema Package (foundation)
    ↓
├─→ CLI (validates before deployment)
├─→ Builder (generates runtime from validated config)
├─→ Controller (stores validated metadata)
├─→ Runtime (creates APIs from validated schema)
└─→ Dashboard (edits validated configs)
```

**Key Point:** Schema has ZERO dependencies on other AgentDock packages. Others depend on it.

---

## What Goes in Schema Package

### 1. Pydantic Models (`dockfile_v1.py`)

Transform every Dockfile section into a validated Python object:

#### Phase 1 (MVP) - Core Models

| Model | Purpose | Critical Validation |
|-------|---------|-------------------|
| `DockSpec` | Root model | Version must be "1.0", extensible for future fields |
| `AgentConfig` | Agent metadata | Entrypoint format `module:function` prevents code injection |
| `IOSchema` | Input/output | Runtime generates `/invoke` endpoint from this |
| `Arguments` | Runtime config | Key-value pairs, flexible dict type |
| `ExposeConfig` | API exposure | Port range (1-65535), requires REST or streaming |
| `Metadata` | Optional info | Maintainer, version, tags |

#### Phase 2 (Future) - Advanced Models

| Model | Purpose | Status |
|-------|---------|--------|
| `ModelConfig` | LLM settings | **Agent-internal** - Not in Dockfile v1 |
| `Policies` | Security rules | **Deferred** - Add when policy engine ready |
| `AuthConfig` | Auth settings | **Deferred** - Add when auth service ready |
| `Observability` | Telemetry | **Deferred** - Add when telemetry integrated |

**Design Principle:** Schema uses Pydantic's `Extra.allow` or `dict[str, Any]` for future fields. New sections can be added without breaking existing deployments.

**Why in schema:** Every service needs these. Validation once, use everywhere.

---

### 2. Custom Validators (`validation.py`)

Complex validation logic extracted for reusability:

- **Entrypoint validation:** Regex + importability check (security critical)
- **Regex safety:** Compile patterns at validation time to catch ReDoS
- **Environment expansion:** `${VAR}` and `${VAR:-default}` syntax

**Why separate file:** Too complex for inline validators, needs unit testing, shared across models.

---

### 3. Error Classes (`errors.py`)

Structured exceptions with error codes (PRD Section 5.2.13):

```
DockfileError (base)
├─ InvalidSchemaError (4001)
├─ MissingFieldsError (4002)
├─ EntrypointNotFoundError (4003)
├─ InvalidIOSchemaError (4004)
├─ AuthConfigError (4005)
├─ PolicyValidationError (4006)
├─ UnsupportedFrameworkError (4007)
└─ TelemetryConfigError (4008)
```

Each error includes:
- Error code (for telemetry aggregation)
- Field path (e.g., `auth.jwt.secret_key`)
- Human-readable message
- Actionable hint (e.g., "Add: auth.jwt.secret_key: '${JWT_SECRET}'")

**Why in schema:** CLI and Dashboard need structured errors for display. Pydantic's generic errors insufficient.

---

### 4. YAML Parser (`parser.py`)

End-to-end pipeline from file to validated object:

**Pipeline:**
1. Load YAML file
2. Process `!include` directives (modular configs)
3. Expand `${VAR}` environment variables
4. Fast-fail JSON Schema validation
5. Detailed Pydantic validation

**Key functions:**
- `load_dockfile(path) → DockSpec` - Complete validation
- `validate_dockfile(path) → Result` - Check only (for CLI)
- `to_yaml(spec) → str` - Serialize back (for storage)

**Why in schema:** Builder, Controller, and CLI all need to parse. Must be centralized.

---

### 5. JSON Schema Generator (`json_schema.py`)

Export Pydantic models as JSON Schema v7:

**Uses:**
- **IDE support:** VS Code autocomplete while writing Dockfiles
- **Fast validation:** JSON Schema validates before expensive Pydantic
- **OpenAPI generation:** Runtime uses this for API documentation

**Output:** `dockfile_v1_schema.json` file for editor plugins.

**Why in schema:** Multiple consumers (CLI, Dashboard, editors). Generate once, use everywhere.

---

## Dependencies & Module Integration

### External Dependencies (from PyPI)

```toml
[project]
dependencies = [
    "pydantic>=2.5",      # Core validation framework
    "pyyaml>=6.0",        # YAML parsing
    "jsonschema>=4.0"     # JSON Schema generation
]
```

**Why these only:**
- Schema must have ZERO dependencies on other AgentDock packages
- Keeps it as the foundational layer
- Allows other packages to import schema without circular dependencies

---

### Modules Schema Will Use FROM Other AgentDock Packages

**❌ NONE in MVP!**

Schema is the foundation - it depends on nothing else internal.

**Future (Phase 2+):** When adding deferred models:
- May use `common/constants.py` for `SUPPORTED_FRAMEWORKS`, `SUPPORTED_PROVIDERS` enums
- May use `common/errors.py` for base error classes (if consolidating error handling)

**Current Design (Parallel Development Strategy):**

Schema defines its own errors and constants NOW to maintain independence during MVP, but designs them for easy migration:

```python
# schema/errors.py (MVP - internal)
class DockfileError(Exception):
    """Base class - designed to match common.errors.DockfileError signature"""
    def __init__(self, message: str, code: int, field: str = None, hint: str = None):
        self.message = message
        self.code = code
        self.field = field
        self.hint = hint

# When common package is ready:
# Option 1: Replace with import
try:
    from agentdock_common.errors import DockfileError, ValidationError
except ImportError:
    # Fallback to local definitions (for backward compatibility)
    class DockfileError(Exception):
        # ... local implementation
        pass
```

**Migration Path:**
1. **MVP (Week 1-2)**: Schema has `errors.py` and inline constants
2. **Integration (Week 3+)**: When `common` package ready:
   - Replace `schema/errors.py` with `from agentdock_common.errors import ...`
   - Replace inline constants with `from agentdock_common.constants import ...`
   - Schema maintains same API (consumers don't change)
3. **Deprecation**: Remove `schema/errors.py` file, keep imports only

**Coordination with Common Package Team:**
- Share error class signatures NOW (via this spec doc)
- Ensure `common/errors.py` implements same interface:
  - `DockfileError(message, code, field, hint)`
  - `InvalidSchemaError`, `EntrypointNotFoundError`, etc.
- Common team can develop in parallel using this spec as contract

---

### Modules FROM Schema Used BY Other Packages

Schema is heavily consumed by all other packages:

| Consumer Package | What It Imports | Why |
|-----------------|-----------------|-----|
| **CLI** | `DockSpec`, `load_dockfile()`, `validate_dockfile()` | Parse and validate before deployment |
| **SDK** | `DockSpec`, `load_dockfile()`, errors | Core deployment validation |
| **Common** | `DockSpec` (type hints) | Validation functions type-hint DockSpec |
| **Adapters** | `AgentConfig` | Get framework and entrypoint info |
| **Policy-Engine** | `Policies` model (future) | Load policy config |
| **Telemetry** | `Observability` model (future) | Load telemetry config |
| **Runtime (generated)** | `IOSchema`, `ExposeConfig` | Generate API endpoints dynamically |

---

### Integration Pattern (from Developer Journey)

**From Validation Flow (Journey 1, Step 3):**

```
┌─────────────────────────────────────────┐
│ CLI validates Dockfile                   │
│ packages/cli/validate_cmd.py            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ SDK loads and parses                     │
│ packages/sdk/validate.py                │
│   spec = load_dockfile(path)  ← SCHEMA  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Schema validates structure               │
│ packages/schema/dockfile_v1.py          │
│   DockSpec.model_validate(data)         │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Schema custom validators                 │
│ packages/schema/validation.py           │
│   validate_entrypoint()                  │
│   validate_agent_name()                  │
└─────────────────────────────────────────┘
```

**From Runtime Generation (Journey 1, Step 4):**

```
┌─────────────────────────────────────────┐
│ SDK generates runtime                    │
│ packages/sdk/deploy.py                  │
│   spec = load_dockfile()  ← SCHEMA      │
│   code = render_template(spec)          │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Generated runtime uses schema            │
│ .agentdock_runtime/main.py              │
│   SPEC = {spec.model_dump()}  ← SCHEMA  │
│   ADAPTER = get_adapter(                │
│     SPEC['agent']['framework']          │
│   )                                      │
└─────────────────────────────────────────┘
```

**From Invocation (Journey 2, Step 2):**

```
┌─────────────────────────────────────────┐
│ Runtime validates input against schema   │
│ Generated main.py                        │
│   input_schema = SPEC['io_schema']      │
│   validate(request.json(), input_schema)│
└─────────────────────────────────────────┘
```

---

## What Does NOT Go in Schema

| What | Where It Belongs | Why |
|------|-----------------|-----|
| Docker builds | Builder Service | Schema validates, services execute |
| Database queries | Controller | Schema defines data, Controller stores it |
| API endpoints | Runtime Service | Schema defines structure, Runtime serves it |
| Token generation | Auth Service | Schema validates config, Auth generates tokens |
| LLM execution | Adapters | Schema defines model config, Adapter calls API |
| Business constants | Common package | Schema defines structure, common defines values |

**Principle:** Schema is pure data + validation. No side effects, no I/O, no business logic.

---

## Critical Validations (Phase 1)

Schema enforces safety at validation time (before deployment):

1. **Entrypoint Injection Prevention**
   - Validates format: `^[\w\.]+:\w+$`
   - Prevents: `os.system:eval`, `../../../etc/passwd:read`

2. **I/O Schema Validation**
   - Ensures input/output schemas are valid JSON Schema or importable classes
   - Prevents: Runtime crashes from malformed API definitions

3. **Port Range Validation**
   - Port must be 1-65535
   - Prevents: Binding failures at runtime

4. **Exposure Requirements**
   - At least REST or streaming must be enabled
   - Prevents: Deploying unreachable agents

## Future Validations (Phase 2+)

Deferred to later when corresponding services are built:

- **ReDoS Prevention** → When `Policies` model added (compiles regex patterns)
- **Auth Enforcement** → When `AuthConfig` model added (requires one auth mode)
- **Tool Gating** → When `Policies` model added (validates tool allow/deny lists)
- **Observability Keys** → When `Observability` model added (validates LangFuse config)

**Impact:** Core validations catch errors in <1 second. Future validations maintain security as features expand.

---

## Implementation Phases

### Phase 1: MVP Core Models (2-3 days)
**Deliverable:** 6 core Pydantic models - `DockSpec`, `AgentConfig`, `IOSchema`, `Arguments`, `ExposeConfig`, `Metadata`
**Blocker:** Nothing else can start without this
**Extensibility:** Use `model_config = ConfigDict(extra="allow")` to accept unknown fields for future expansion

### Phase 2: Validation + Errors (2 days)
**Deliverable:** Custom validators (entrypoint, I/O schema) and error hierarchy (4001-4004 codes for MVP)
**Value:** Clear, actionable error messages
**Note:** Error codes 4005-4008 reserved for future (auth, policy, telemetry)

### Phase 3: YAML Parser (2 days)
**Deliverable:** Load → Expand → Validate pipeline
**Value:** Users can actually use the schema package

### Phase 4: JSON Schema (1 day)
**Deliverable:** `dockfile_v1_schema.json` for IDE support
**Value:** Autocomplete while writing Dockfiles

### Phase 5: Testing (2 days)
**Deliverable:** >90% coverage for MVP models
**Value:** Schema is rock-solid foundation

### Phase 6: Documentation (1 day)
**Deliverable:** README with MVP usage examples
**Value:** Other teams can integrate quickly

### Phase 7: Integration (1-2 days)
**Deliverable:** CLI uses schema, performance validated
**Value:** End-to-end validation works

**Total:** ~2 weeks for MVP schema package (vs 3 weeks for full version)

### Future Phases (When Services Ready)
- **Phase 8:** Add `Policies` model when policy-engine package built
- **Phase 9:** Add `AuthConfig` model when auth service built  
- **Phase 10:** Add `Observability` model when telemetry integrated

---

## Success Metrics

### Technical
- ✅ Validate Dockfile in <100ms
- ✅ 100% type coverage (mypy strict)
- ✅ >90% test coverage
- ✅ Zero dependencies on other AgentDock packages

### User Experience
- ✅ Clear error: "Error 4005 at auth.jwt.secret_key: Field required when mode='jwt'. Hint: Add auth.jwt.secret_key: '${JWT_SECRET}'"
- ✅ IDE autocomplete from JSON Schema
- ✅ Errors caught in 1s vs 60s build failure

### Platform Impact
- ✅ CLI, Builder, Controller, Runtime all use same validation
- ✅ Zero deployments fail due to schema bugs
- ✅ Security rules enforced at validation time

---

## Future: Dockfile v2

When AgentDock v2 launches with multi-agent workflows:

- Add `dockfile_v2.py` alongside v1
- Parser routes based on `version: "2.0"` field
- Both versions coexist (no breaking changes)
- Consistent migration path

**Why schema owns this:** Centralized version management. One place to add v2 support.

---

## Parallel Development Strategy

Since `schema` and `common` packages are being developed simultaneously by different teams, we need a coordination strategy:

### Approach: "Define Locally, Migrate Later"

**Phase 1 (Weeks 1-2): Independent Development**
- Schema team: Define `errors.py` with error classes (4001-4004)
- Common team: Define `errors.py` with broader error classes
- Both teams use **same interface signature** (coordinated via this spec)

**Phase 2 (Week 3): Integration**
- Schema team: Replace local errors with imports from common
- Use try/except pattern for graceful fallback
- Maintain backward compatibility

**Phase 3 (Week 4+): Consolidation**
- Remove local `schema/errors.py` file
- Keep only imports from common
- Update documentation

---

### Shared Interface Contract

Both teams must implement these signatures:

```python
# Both schema/errors.py AND common/errors.py must implement:

class DockfileError(Exception):
    """Base exception"""
    def __init__(self, message: str, code: int, field: str = None, hint: str = None):
        pass
    
    def to_dict(self) -> dict:
        """Returns: {"error": ..., "code": ..., "field": ..., "hint": ...}"""
        pass

class InvalidSchemaError(DockfileError):
    """Code 4001"""
    pass

class EntrypointNotFoundError(DockfileError):
    """Code 4003"""
    pass

# Constants both must define:
SUPPORTED_FRAMEWORKS = ["langgraph", "langchain"]
```

**Why this works:**
- ✅ Teams don't block each other
- ✅ Interface ensures compatibility
- ✅ Easy to swap implementations
- ✅ Consumers unaffected by migration

---

### Implementation Pattern (for Schema Team)

```python
# schema/errors.py (MVP implementation)

"""
Error classes for schema validation.

NOTE: These will be migrated to agentdock_common.errors once that package is ready.
Interface is designed to match common.errors exactly.
"""

class DockfileError(Exception):
    """Base error - INTERFACE MUST MATCH common.errors.DockfileError"""
    def __init__(self, message: str, code: int, field: str = None, hint: str = None):
        self.message = message
        self.code = code
        self.field = field
        self.hint = hint
        super().__init__(self.format_message())
    
    def format_message(self) -> str:
        parts = [f"Error {self.code}: {self.message}"]
        if self.field:
            parts.append(f"Field: {self.field}")
        if self.hint:
            parts.append(f"Hint: {self.hint}")
        return "\n".join(parts)
    
    def to_dict(self) -> dict:
        return {
            "error": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "field": self.field,
            "hint": self.hint
        }

class InvalidSchemaError(DockfileError):
    def __init__(self, message: str, field: str = None, hint: str = None):
        super().__init__(message, code=4001, field=field, hint=hint)

# ... more error classes
```

**After common is ready, replace with:**

```python
# schema/errors.py (post-integration)

"""
Error classes imported from agentdock_common.

Maintained here for backward compatibility with existing imports.
"""

try:
    from agentdock_common.errors import (
        DockfileError,
        InvalidSchemaError,
        EntrypointNotFoundError,
        InvalidIOSchemaError,
    )
except ImportError:
    # Fallback for environments where common not installed
    # (shouldn't happen in production, but useful for development)
    import warnings
    warnings.warn("agentdock_common not found, using local error definitions")
    
    # Keep local definitions as fallback
    class DockfileError(Exception):
        # ... same implementation as before
        pass
```

---

### Communication Protocol Between Teams

**Schema Team Provides to Common Team:**
1. ✅ Error class names and codes (4001-4004)
2. ✅ Interface signatures (constructor args, methods)
3. ✅ Expected behavior (formatting, serialization)

**Common Team Provides to Schema Team:**
1. ✅ Package ready notification (when `common` can be imported)
2. ✅ Confirmation interface matches
3. ✅ Migration assistance if needed

**Shared Document:** This spec serves as the contract both teams follow.

---

## Key Architectural Principles

1. **Schema First:** Validation before execution
2. **Fail Fast:** Catch errors at parse time, not runtime
3. **Single Source of Truth:** One validation implementation
4. **Security by Default:** Dangerous patterns blocked at validation
5. **Zero Dependencies (MVP):** Schema depends on nothing internal initially
6. **Type Safe:** Every service uses `DockSpec`, not `dict`
7. **Extensible by Design:** Accept unknown fields now, validate them later when services ready
8. **Parallel Development Ready:** Define locally, migrate gracefully, maintain compatibility

---

## Why This Matters

**Without schema package:**
- Multiple services implementing different validation → inconsistencies
- Security vulnerabilities discovered in production
- No way to extend Dockfile without breaking changes

**With schema package (MVP approach):**
- 1 implementation × thoroughly tested = reliable foundation
- Core security enforced before deployment (entrypoint, I/O schema)
- Extensible design → add Policies/Auth/Observability when services ready
- No breaking changes when adding new fields

**Bottom line:** Schema package is not overhead. It's the extensible contract that makes AgentDock reliable today and tomorrow.

---

## Extensibility Strategy

**Current (MVP):**
```yaml
version: "1.0"
agent: {...}
io_schema: {...}
arguments: {...}
expose: {...}
metadata: {...}
```

**Future (when services ready):**
```yaml
version: "1.0"
agent: {...}
io_schema: {...}
arguments: {...}
expose: {...}
metadata: {...}
policies: {...}      # Added when policy-engine ready
auth: {...}          # Added when auth service ready
observability: {...} # Added when telemetry ready
```

**How it works:**
- Schema v1 accepts unknown fields (no validation errors)
- Services ignore fields they don't understand
- When service is ready, add corresponding Pydantic model
- Existing Dockfiles keep working
- New Dockfiles get new validations

**Result:** Build features incrementally without breaking existing deployments.

