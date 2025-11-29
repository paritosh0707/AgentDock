# Dockrion Package Responsibilities & Boundaries

**Version:** 1.0  
**Last Updated:** November 11, 2024  
**Status:** Living Document

## Purpose

This document defines the clear separation of responsibilities for each Dockrion package to prevent overlap, ensure maintainability, and guide future development decisions.

---

## Guiding Principles

1. **Single Responsibility**: Each package has one primary purpose
2. **Clear Boundaries**: No overlapping functionality between packages
3. **Minimal Dependencies**: Packages depend only on what they absolutely need
4. **Future-Proof**: Design allows for extension without breaking changes
5. **Common First**: Shared utilities go in `common`, not duplicated

---

## Package Dependency Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│                      USER INTERFACES                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐  │
│  │   CLI    │  │   SDK    │  │  Services (Future)    │  │
│  └─────┬────┘  └────┬─────┘  └──────────┬───────────┘  │
└────────┼────────────┼───────────────────┼──────────────┘
         │            │                   │
         └────────────┼───────────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
    ┌────▼─────┐            ┌─────▼──────┐
    │  SCHEMA  │            │  ADAPTERS  │
    └────┬─────┘            └─────┬──────┘
         │                        │
         └────────┬───────────────┘
                  │
         ┌────────▼─────────┐
         │  POLICY ENGINE   │
         └────────┬─────────┘
                  │
         ┌────────┴─────────┐
         │                  │
    ┌────▼─────┐      ┌────▼──────┐
    │  COMMON  │      │ TELEMETRY │
    └──────────┘      └───────────┘

Legend:
- Top layer depends on bottom layers
- Bottom layers NEVER depend on top layers
- Common and Telemetry are foundation (no dependencies on other Dockrion packages)
```

---

## 1. Common Package (`packages/common-py`)

### Primary Responsibility
**Shared utilities and primitives used across all Dockrion packages and services**

### Owns
- ✅ **Error Classes**: All Dockrion exceptions (`DockrionError`, `ValidationError`, `AuthError`, etc.)
- ✅ **Constants**: Supported values, defaults, permissions list
- ✅ **Validation Utilities**: Input validation, format checking, parsing
- ✅ **Auth Utilities**: API key generation, validation, hashing
- ✅ **HTTP Models**: Standard API response formats (`APIResponse`, `ErrorResponse`)

### Does NOT Own
- ❌ Schema definitions (that's `schema` package)
- ❌ Logging/metrics (that's `telemetry` package)
- ❌ Agent adapters (that's `adapters` package)
- ❌ Policy logic (that's `policy-engine` package)
- ❌ Business logic (that's services/SDK)

### Dependencies
- **External only**: `pydantic` for models
- **No internal dependencies**: Foundation layer

### Examples
```python
# ✅ BELONGS in common
from dockrion_common.errors import ValidationError
from dockrion_common.constants import SUPPORTED_FRAMEWORKS
from dockrion_common.validation import validate_entrypoint
from dockrion_common.auth_utils import generate_api_key
from dockrion_common.http_models import success_response

# ❌ DOES NOT belong in common
DockSpec  # This is schema
log_event()  # This is telemetry
LangGraphAdapter  # This is adapters
```

### Future Considerations (V2+)
- Rate limiting utilities (when needed by multiple services)
- Circuit breaker patterns (when services communicate)
- Caching abstractions (when Redis is added)

---

## 2. Schema Package (`packages/schema`)

### Primary Responsibility
**Define and validate the Dockfile configuration structure**

### Owns
- ✅ **Dockfile Schema**: `DockSpec` and all nested models (`AgentCfg`, `ModelCfg`, `Policies`, etc.)
- ✅ **Schema Validation**: Pydantic model validation, field validators
- ✅ **Version Management**: Support for multiple Dockfile versions (v1.0, v1.1, etc.)
- ✅ **Type Definitions**: Type hints for configuration objects

### Does NOT Own
- ❌ **File I/O** (reading YAML files is SDK/CLI responsibility)
- ❌ **YAML parsing** (converting YAML to dict is SDK/CLI responsibility)
- ❌ **Environment variable expansion** (I/O operation, belongs in SDK)
- ❌ Business logic validation (format checking is in `common`)
- ❌ Schema enforcement at runtime (that's runtime/services)
- ❌ Default value logic (defaults come from constants in `common`)

### Dependencies
- `common`: For constants, validation utilities, error classes
- External: `pydantic` for models

### Examples
```python
# ✅ BELONGS in schema
class DockSpec(BaseModel):
    """Schema defines structure and validates data"""
    version: Literal["1.0"]
    agent: AgentCfg
    model: ModelCfg
    
    @field_validator("agent")
    def validate_agent(cls, v):
        validate_entrypoint(v.entrypoint)  # Uses common
        return v

# Usage: Schema receives dict, returns validated object
data = {"version": "1.0", "agent": {...}}
spec = DockSpec.model_validate(data)  # ✅ Pure validation

# ❌ DOES NOT belong in schema
def load_dockspec(path):  # This is SDK - does file I/O
    with open(path) as f:
        data = yaml.safe_load(f)  # SDK parses YAML
    return DockSpec.model_validate(data)  # Then uses schema

def deploy_agent(spec):  # This is SDK/services
```

### Future Considerations (V2+)
- Schema versioning and migration utilities
- Schema evolution support (backwards compatibility)
- Custom validators via plugins

---

## 3. Adapters Package (`packages/adapters`)

### Primary Responsibility
**Provide uniform interface to different agent frameworks**

### Owns
- ✅ **Adapter Interface**: `AgentAdapter` protocol
- ✅ **Framework Adapters**: `LangGraphAdapter`, `LangChainAdapter`, etc.
- ✅ **Adapter Registry**: `get_adapter()` function
- ✅ **Agent Loading**: Dynamic import and initialization of user agents

### Does NOT Own
- ❌ Agent implementation (that's user code)
- ❌ Agent configuration (that's `schema`)
- ❌ Policy enforcement (that's `policy-engine`)
- ❌ Invocation logging (that's `telemetry`)

### Dependencies
- `common`: For error classes
- External: Framework-specific libraries (LangGraph, LangChain)

### Examples
```python
# ✅ BELONGS in adapters
class LangGraphAdapter(AgentAdapter):
    def invoke(self, payload: dict) -> dict:
        return self._runner.invoke(payload)

def get_adapter(framework: str) -> AgentAdapter:
    if framework == "langgraph":
        return LangGraphAdapter()

# ❌ DOES NOT belong in adapters
def apply_redaction(text):  # This is policy-engine
def log_invocation():  # This is telemetry
```

### Future Considerations (V2+)
- Streaming support (yield results incrementally)
- Async adapter protocol
- Custom adapter plugins
- Adapter middleware (pre/post hooks)

---

## 4. Policy Engine Package (`packages/policy-engine`)

### Primary Responsibility
**Enforce safety and security policies on agent inputs/outputs**

### Owns
- ✅ **Policy Engine**: `PolicyEngine` class
- ✅ **Safety Policies**: Redaction, output limits, prompt injection detection
- ✅ **Tool Guards**: Tool allow/deny lists
- ✅ **Policy Enforcement**: `post_invoke()`, `tool_allowed()` methods

### Does NOT Own
- ❌ Policy configuration (that's in `schema` as `Policies`)
- ❌ Agent invocation (that's `adapters`)
- ❌ Logging violations (that's `telemetry`)
- ❌ Error definitions (that's `common`)

### Dependencies
- `schema`: For policy configuration types
- `common`: For error classes
- External: Regex for pattern matching

### Examples
```python
# ✅ BELONGS in policy-engine
class PolicyEngine:
    def post_invoke(self, text: str) -> str:
        text = redact(text, self.redact_patterns)
        if len(text) > self.max_output_chars:
            text = text[:self.max_output_chars]
        return text
    
    def tool_allowed(self, name: str) -> bool:
        return is_tool_allowed(name, self.tools_allowed, self.deny_by_default)

# ❌ DOES NOT belong in policy-engine
def invoke_agent():  # This is adapters/runtime
def log_violation():  # This is telemetry
```

### Future Considerations (V2+)
- PII detection and redaction
- Content moderation (hate speech, violence)
- Custom policy plugins
- Policy versioning and auditing

---

## 5. Telemetry Package (`packages/telemetry`)

### Primary Responsibility
**Agent runtime observability and metrics collection**

### Owns
- ✅ **Event Logging**: `log_event()` for structured logs
- ✅ **Prometheus Metrics**: Request counts, latency histograms, token counters
- ✅ **Metric Utilities**: `observe_request()`, metric helpers
- ✅ **Agent-Level Telemetry**: Invocation tracking, performance monitoring

### Does NOT Own
- ❌ Service logging (services use standard Python logging or `common` logger)
- ❌ Log storage/aggregation (use external systems: Langfuse, ELK)
- ❌ Alerting (use Prometheus Alertmanager)
- ❌ Business logic (only observes, doesn't control)

### Dependencies
- External: `prometheus-client` for metrics
- **No internal dependencies**: Foundation layer

### Examples
```python
# ✅ BELONGS in telemetry
def log_event(event: str, **kwargs):
    sys.stdout.write(json.dumps({"event": event, **kwargs}))

REQ_COUNT = Counter("dockrion_requests_total", "Total requests", ["agent","version"])
LATENCY = Histogram("dockrion_latency_seconds", "Latency", ["agent","version"])

def observe_request(agent: str, version: str, latency_s: float):
    REQ_COUNT.labels(agent, version).inc()
    LATENCY.labels(agent, version).observe(latency_s)

# ❌ DOES NOT belong in telemetry
def invoke_agent():  # This is adapters
class DockrionLogger:  # This would be common (if needed)
```

### Future Considerations (V2+)
- Langfuse integration
- Distributed tracing (OpenTelemetry)
- Cost tracking per invocation
- Custom metric exporters

---

## 6. SDK Package (`packages/sdk-python`)

### Primary Responsibility
**Programmatic interface for deploying and managing agents**

### Owns
- ✅ **Deployment Orchestration**: `deploy()`, `run_local()`
- ✅ **Dockfile Loading**: `load_dockspec()` - YAML parsing
- ✅ **Runtime Generation**: Template rendering (`_render_runtime()`)
- ✅ **Dockerfile Generation**: Container image building
- ✅ **Controller Client**: API client for controller service (V1.1+)

### Does NOT Own
- ❌ Schema definition (that's `schema`)
- ❌ Validation logic (that's `common` and `schema`)
- ❌ Runtime execution (that's generated runtime/services)
- ❌ CLI commands (that's `cli`)

### Dependencies
- `schema`: For `DockSpec` types
- `common`: For validation, errors
- External: `pyyaml`, `jinja2` (for templates)

### Examples
```python
# ✅ BELONGS in sdk
def load_dockspec(path: str) -> DockSpec:
    data = yaml.safe_load(open(path))
    return DockSpec.model_validate(data)

def deploy(dockfile_path: str, target: str = "local"):
    spec = load_dockspec(dockfile_path)
    runtime_code = _render_runtime(spec)
    # ... build and deploy

# ❌ DOES NOT belong in sdk
class DockSpec:  # This is schema
def validate_entrypoint():  # This is common
```

### Future Considerations (V2+)
- Remote deployment (talk to controller service)
- Blue-green deployments
- Rollback support
- Multi-target deployment (K8s, ECS, etc.)

---

## 7. CLI Package (`packages/cli`)

### Primary Responsibility
**Command-line interface for developers**

### Owns
- ✅ **CLI Commands**: `validate`, `deploy`, `logs` commands
- ✅ **User Interaction**: Input prompts, progress indicators, error display
- ✅ **Command Orchestration**: Calls SDK functions
- ✅ **Output Formatting**: Pretty-printing results

### Does NOT Own
- ❌ Business logic (delegates to SDK)
- ❌ Validation implementation (uses `common` and `schema`)
- ❌ Deployment logic (calls SDK)

### Dependencies
- `sdk`: For deployment, validation
- `common`: For errors
- External: `typer` or `click` for CLI framework

### Examples
```python
# ✅ BELONGS in cli
@app.command()
def validate(path: str = "Dockfile.yaml"):
    try:
        result = validate_dockspec(path)  # Calls SDK
        typer.echo("✅ Dockfile valid")
    except ValidationError as e:
        typer.echo(f"❌ {e.message}")

# ❌ DOES NOT belong in cli
def load_dockspec():  # This is SDK
def _render_runtime():  # This is SDK
```

### Future Considerations (V2+)
- Interactive mode (wizard for creating Dockfiles)
- Shell completions
- Watch mode (auto-redeploy on changes)

---

## Package Interaction Rules

### Rule 1: Dependency Direction
**Lower-level packages NEVER import from higher-level packages**

```python
# ✅ ALLOWED
# SDK imports from schema, common
from dockrion_schema.dockfile_v1 import DockSpec
from dockrion_common.errors import ValidationError

# ❌ FORBIDDEN
# Common importing from schema
from dockrion_schema.dockfile_v1 import DockSpec  # NO!

# Schema importing from SDK
from dockrion_sdk.client import load_dockspec  # NO!
```

### Rule 2: Common is Foundation
**Only `common` and `telemetry` have zero internal dependencies**

```python
# ✅ Everyone can import from common
from dockrion_common.errors import ValidationError

# ❌ Common cannot import from anyone
from dockrion_schema import DockSpec  # NO!
```

### Rule 3: Avoid Circular Dependencies
**If package A imports package B, then B cannot import A**

### Rule 4: External Dependencies
**Add external dependencies only when necessary, document why**

---

## Responsibility Matrix

| Package | Configuration | Validation | Execution | Observability | User Interface |
|---------|--------------|------------|-----------|---------------|----------------|
| **common** | ❌ | ✅ Utilities | ❌ | ❌ | ❌ |
| **schema** | ✅ Structure | ✅ Model | ❌ | ❌ | ❌ |
| **adapters** | ❌ | ❌ | ✅ Agent | ❌ | ❌ |
| **policy-engine** | ❌ | ❌ | ✅ Policies | ❌ | ❌ |
| **telemetry** | ❌ | ❌ | ❌ | ✅ | ❌ |
| **sdk** | ❌ | ✅ Orchestration | ✅ Deploy | ❌ | ✅ API |
| **cli** | ❌ | ❌ | ❌ | ❌ | ✅ Commands |

Legend:
- ✅ Primary responsibility
- ❌ Not responsible

---

## What Goes Where: Decision Tree

```
Is it an exception/error class?
  └─ YES → common/errors.py

Is it a constant/default value?
  └─ YES → common/constants.py

Is it a Pydantic model for Dockfile?
  └─ YES → schema/dockfile_v1.py

Is it format validation logic?
  └─ YES → common/validation.py

Is it framework-specific agent logic?
  └─ YES → adapters/

Is it safety/security enforcement?
  └─ YES → policy-engine/

Is it agent performance tracking?
  └─ YES → telemetry/

Is it YAML parsing or deployment orchestration?
  └─ YES → sdk/

Is it a CLI command?
  └─ YES → cli/

Is it service-level logging?
  └─ YES → Each service uses Python logging (not in packages)
```

---

## Adding New Functionality: Guidelines

### Before Adding to a Package, Ask:

1. **Does it align with the package's primary responsibility?**
   - If no → find the right package or create new one

2. **Will it be used by 3+ other packages?**
   - If yes → consider `common`
   - If no → keep it in the specific package

3. **Does it create a circular dependency?**
   - If yes → refactor or move to lower-level package

4. **Is it framework/domain-specific?**
   - If yes → probably not `common`
   - Keep domain-specific code in domain packages

5. **Is it stable and unlikely to change?**
   - If unstable → keep it local, don't share yet
   - If stable → safe to share via `common`

---

## Anti-Patterns to Avoid

### ❌ Anti-Pattern 1: "God Package"
**Problem:** Putting everything in `common` because "it might be shared"

```python
# ❌ BAD - Don't do this
# common/everything.py
class LangGraphAdapter:  # This is adapters!
class PolicyEngine:      # This is policy-engine!
def deploy_agent():      # This is SDK!
```

**Solution:** Only put in `common` what is ALREADY used by 3+ packages

### ❌ Anti-Pattern 2: Circular Dependencies
**Problem:** Packages importing from each other

```python
# ❌ BAD
# schema imports from adapters
from dockrion_adapters import LangGraphAdapter

# adapters imports from schema
from dockrion_schema import DockSpec
```

**Solution:** Extract shared types to `common` or restructure

### ❌ Anti-Pattern 3: Bypassing Abstractions
**Problem:** Directly using internals instead of public APIs

```python
# ❌ BAD
from dockrion_adapters.langgraph_adapter import _private_method

# ✅ GOOD
from dockrion_adapters import get_adapter
adapter = get_adapter("langgraph")
```

### ❌ Anti-Pattern 4: Duplicating Logic
**Problem:** Same validation logic in multiple packages

```python
# ❌ BAD - Duplicated in SDK and CLI
# sdk/validate.py
def validate_name(name):
    if not re.match(r'^[a-z0-9-]+$', name):
        raise ValueError("Invalid name")

# cli/validate.py  
def validate_name(name):  # Same code!
    if not re.match(r'^[a-z0-9-]+$', name):
        raise ValueError("Invalid name")
```

**Solution:** Extract to `common/validation.py`

---

## Future Services (V2+)

When services are built, they should follow this pattern:

### Controller Service
- **Owns:** Deployment lifecycle, versioning, rollbacks
- **Uses:** `schema`, `common`, `telemetry` packages
- **Does NOT:** Execute agents (that's runtime)

### Auth Service
- **Owns:** Authentication, authorization, API key management
- **Uses:** `common/auth_utils.py` (extend, not replace)
- **Does NOT:** Agent logic

### Runtime Gateway
- **Owns:** Request routing, load balancing
- **Uses:** `adapters`, `policy-engine`, `telemetry`
- **Does NOT:** Deployment logic

### Dashboard BFF
- **Owns:** Dashboard API aggregation
- **Uses:** `common/http_models.py` for responses
- **Does NOT:** Business logic (calls other services)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Nov 11, 2024 | Initial version - V1 package boundaries |

---

## Modifying This Document

1. **Propose changes** via discussion/PR
2. **Update version number** when boundaries change
3. **Document reasoning** for significant changes
4. **Review with team** before merging
5. **Communicate changes** to all developers

---

## Summary

| Package | One-Line Responsibility | Dependencies |
|---------|------------------------|--------------|
| **common** | Shared utilities and primitives | External only |
| **schema** | Dockfile structure and validation | common |
| **adapters** | Uniform interface to agent frameworks | common |
| **policy-engine** | Safety and security enforcement | schema, common |
| **telemetry** | Agent runtime observability | External only |
| **sdk** | Deployment orchestration and API | schema, common |
| **cli** | Command-line interface | sdk, common |

**Golden Rule:** When in doubt, ask "Who owns this?" If unclear, it probably doesn't exist yet or belongs in `common`.

