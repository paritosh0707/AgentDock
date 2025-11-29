# Dockrion Developer Journey: From Code to Production

This document provides a detailed journey of how Dockrion components interact, following real user workflows from development to production deployment and invocation.

## Table of Contents
1. [Journey 1: Developer Creates and Deploys an Agent](#journey-1-developer-creates-and-deploys-an-agent)
2. [Journey 2: End User Invokes an Agent](#journey-2-end-user-invokes-an-agent)
3. [Journey 3: Admin Manages API Keys and Permissions](#journey-3-admin-manages-api-keys-and-permissions)
4. [Journey 4: Developer Monitors Agent Performance](#journey-4-developer-monitors-agent-performance)

---

## Journey 1: Developer Creates and Deploys an Agent

**Persona:** Alice, a Python developer building an invoice extraction agent

### Step 1: Alice Creates Her Agent Code

**Location:** `examples/invoice_copilot/app/graph.py`

```python
from langgraph.graph import Graph
from langchain_openai import ChatOpenAI

def build_graph():
    """Alice's agent logic"""
    graph = Graph()
    # ... agent implementation
    return graph
```

**Modules Used:** None yet - pure agent logic

---

### Step 2: Alice Creates a Dockfile.yaml

**Location:** `Dockfile.yaml` (in her project root)

**What Alice does:**
```bash
# Alice creates her configuration
touch Dockfile.yaml
```

**Alice writes:**
```yaml
version: "1.0"
agent:
  name: invoice-copilot
  entrypoint: examples.invoice_copilot.app.graph:build_graph
  framework: langgraph
model:
  provider: openai
  name: gpt-4o-mini
# ... rest of config
```

**Modules Involved:**
- **`schema`** package is the reference for valid structure
- Alice doesn't import it yet, just follows the spec

---

### Step 3: Alice Validates Her Dockfile (CLI)

**Command:**
```bash
Dockrion validate
```

**Flow:**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CLI Entry Point                                           │
│    packages/cli/dockrion_cli/validate_cmd.py               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Load Dockfile (SDK)                                       │
│    packages/sdk-python/dockrion_sdk/validate.py            │
│                                                               │
│    - Reads Dockfile.yaml from disk                          │
│    - Parses YAML content                                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Parse & Validate Schema                                   │
│    packages/schema/dockrion_schema/dockfile_v1.py          │
│                                                               │
│    DockSpec.model_validate(data)                            │
│    - Validates all fields                                    │
│    - Checks required fields                                  │
│    - Validates field types                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Custom Validation (Common)                                │
│    packages/common-py/dockrion_common/validation.py        │
│                                                               │
│    - validate_entrypoint()                                   │
│      ✓ Checks "module:callable" format                      │
│      ✓ Ensures both parts exist                             │
│                                                               │
│    - validate_agent_name()                                   │
│      ✓ Lowercase alphanumeric + hyphens                     │
│      ✓ Max 63 characters                                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Check Constants (Common)                                  │
│    packages/common-py/dockrion_common/constants.py         │
│                                                               │
│    - framework in SUPPORTED_FRAMEWORKS?                      │
│    - provider in SUPPORTED_PROVIDERS?                        │
│    - auth.mode in SUPPORTED_AUTH_MODES?                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Return Result to CLI                                      │
│    packages/cli/dockrion_cli/validate_cmd.py               │
│                                                               │
│    if valid:                                                 │
│        print("✅ Dockfile valid")                           │
│    else:                                                     │
│        print("❌ Invalid")                                   │
│        print(error_message)                                  │
└─────────────────────────────────────────────────────────────┘
```

**Error Handling Example:**

If Alice made a mistake:
```yaml
agent:
  name: Invoice_Copilot  # ❌ Uppercase not allowed
  entrypoint: wrong_format  # ❌ Missing ':'
```

**Flow:**
```python
# In validation.py
validate_agent_name("Invoice_Copilot")
# Raises: ValidationError from common/errors.py
# Message: "Agent name must be lowercase alphanumeric with hyphens only"

# CLI catches it
except ValidationError as e:
    typer.echo(f"❌ {e.message}")
```

**Output to Alice:**
```
❌ Validation failed:
  - Agent name must be lowercase alphanumeric with hyphens only
  - Entrypoint must be in format 'module:callable'
```

---

### Step 4: Alice Deploys Locally (SDK)

**Command:**
```bash
Dockrion deploy --target local
```

**Detailed Flow:**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. CLI Entry Point                                           │
│    packages/cli/dockrion_cli/deploy_cmd.py                 │
│                                                               │
│    - Parses arguments: target="local"                        │
│    - Calls SDK deploy function                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Load & Validate Dockspec (SDK + Schema + Common)         │
│    packages/sdk-python/dockrion_sdk/client.py              │
│                                                               │
│    def load_dockspec(path):                                  │
│        data = yaml.safe_load(...)                            │
│        return DockSpec.model_validate(data)                  │
│                                                               │
│    Uses: schema, common/validation, common/errors            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Generate Dockerfile (SDK)                                 │
│    packages/sdk-python/dockrion_sdk/deploy.py              │
│                                                               │
│    _render_dockerfile(spec)                                  │
│    - Uses Jinja2 template: templates/dockerfiles/           │
│                             Dockerfile.runtime.j2            │
│    - Injects: python version, dependencies, entrypoint      │
│                                                               │
│    Generated Dockerfile:                                     │
│    ┌─────────────────────────────────────────┐             │
│    │ FROM python:3.12                         │             │
│    │ RUN pip install langgraph langchain-openai │          │
│    │ COPY . /app                              │             │
│    │ CMD ["python", "runtime.py"]             │             │
│    └─────────────────────────────────────────┘             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Generate Runtime Server (SDK)                             │
│    packages/sdk-python/dockrion_sdk/deploy.py              │
│                                                               │
│    _render_runtime(spec)                                     │
│    - Uses template: templates/runtime-fastapi/main.py.j2    │
│    - Creates FastAPI app with routes:                        │
│      • POST /invoke                                          │
│      • GET /health                                           │
│      • GET /schema                                           │
│      • GET /metrics                                          │
│                                                               │
│    Generated runtime.py:                                     │
│    ┌─────────────────────────────────────────┐             │
│    │ from fastapi import FastAPI              │             │
│    │ from dockrion_adapters import get_adapter │           │
│    │ from dockrion_policy import PolicyEngine │            │
│    │ from dockrion_telemetry import log_event │            │
│    │                                           │             │
│    │ app = FastAPI()                          │             │
│    │ agent = load_agent_from_entrypoint()     │             │
│    │ policy = PolicyEngine.from_dockspec(spec)│             │
│    │                                           │             │
│    │ @app.post("/invoke")                     │             │
│    │ async def invoke(request):               │             │
│    │     # Validate auth                      │             │
│    │     # Run agent                          │             │
│    │     # Apply policies                     │             │
│    │     # Log telemetry                      │             │
│    │     return response                      │             │
│    └─────────────────────────────────────────┘             │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Build Docker Image                                        │
│    packages/sdk-python/dockrion_sdk/deploy.py              │
│                                                               │
│    subprocess.run([                                          │
│        "docker", "build",                                    │
│        "-t", "Dockrion/invoice-copilot:latest",            │
│        "."                                                   │
│    ])                                                        │
│                                                               │
│    Image layers:                                             │
│    - Base Python image                                       │
│    - Dockrion packages (adapters, policy, telemetry)       │
│    - User's agent code                                       │
│    - Generated runtime server                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Run Container Locally                                     │
│    packages/sdk-python/dockrion_sdk/deploy.py              │
│                                                               │
│    subprocess.run([                                          │
│        "docker", "run",                                      │
│        "-p", "8080:8080",                                    │
│        "-e", "OPENAI_API_KEY=...",                          │
│        "Dockrion/invoice-copilot:latest"                   │
│    ])                                                        │
│                                                               │
│    Container starts:                                         │
│    - Loads agent from entrypoint                             │
│    - Initializes FastAPI server                              │
│    - Binds to 0.0.0.0:8080                                  │
│    - Ready to receive requests                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Success Message to Alice                                  │
│                                                               │
│    ✅ Deployment successful!                                │
│    📦 Image: Dockrion/invoice-copilot:latest               │
│    🚀 Running on: http://localhost:8080                     │
│    📝 API Docs: http://localhost:8080/docs                  │
└─────────────────────────────────────────────────────────────┘
```

**Packages Used in This Step:**
- ✓ `cli` - Command interface
- ✓ `sdk-python` - Deployment orchestration
- ✓ `schema` - Dockspec validation
- ✓ `common` - Validation, errors, constants
- ✓ `adapters` - Injected into runtime
- ✓ `policy-engine` - Injected into runtime
- ✓ `telemetry` - Injected into runtime

---

## Journey 2: End User Invokes an Agent

**Persona:** Bob, an end user who needs to extract data from an invoice

### Step 1: Bob Sends API Request

**Bob's code:**
```python
import requests

response = requests.post(
    "http://localhost:8080/invoke",
    headers={
        "X-API-Key": "agd_abc123...",
        "Content-Type": "application/json"
    },
    json={
        "document_text": "INVOICE #12345...",
        "currency_hint": "USD"
    }
)

print(response.json())
```

---

### Step 2: Request Enters Runtime Container

**Detailed Flow Through Runtime:**

```
┌─────────────────────────────────────────────────────────────┐
│ RUNTIME CONTAINER (Generated by SDK)                        │
│ Image: Dockrion/invoice-copilot:latest                     │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 1. FastAPI Receives Request                                  │
│    Generated: runtime.py (from template)                     │
│                                                               │
│    @app.post("/invoke")                                      │
│    async def invoke(request: Request):                       │
│        body = await request.json()                           │
│        api_key = request.headers.get("X-API-Key")           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Validate API Key (Common)                                 │
│    packages/common-py/dockrion_common/auth_utils.py        │
│                                                               │
│    validate_api_key(api_key, expected_key)                   │
│                                                               │
│    - Compares provided key with configured key               │
│    - Reads expected_key from environment variable            │
│    - If invalid: raises AuthError                            │
│                                                               │
│    from dockrion_common.errors import AuthError             │
│    if not valid:                                             │
│        raise AuthError("Invalid API key")                    │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Validate Input Schema (Schema)                            │
│    packages/schema/dockrion_schema/dockfile_v1.py          │
│                                                               │
│    Expected input from io_schema:                            │
│    {                                                         │
│        "type": "object",                                     │
│        "required": ["document_text"],                        │
│        "properties": {                                       │
│            "document_text": {"type": "string"},             │
│            "currency_hint": {"type": "string"}              │
│        }                                                     │
│    }                                                         │
│                                                               │
│    - Validates Bob's input matches schema                    │
│    - Checks required fields present                          │
│    - If invalid: raises ValidationError                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Log Invocation Start (Telemetry)                         │
│    packages/telemetry/dockrion_telemetry/logger.py         │
│                                                               │
│    log_event("invocation_start",                             │
│        agent="invoice-copilot",                              │
│        timestamp=time.time(),                                │
│        input_size=len(body)                                  │
│    )                                                         │
│                                                               │
│    Output to stdout (JSON):                                  │
│    {"event": "invocation_start", "agent": "invoice-copilot", │
│     "timestamp": 1699456789.123, "input_size": 1234}        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. Get Agent Adapter (Adapters)                              │
│    packages/adapters/dockrion_adapters/registry.py         │
│                                                               │
│    adapter = get_adapter(framework="langgraph")              │
│    # Returns: LangGraphAdapter                               │
│                                                               │
│    packages/adapters/dockrion_adapters/langgraph_adapter.py│
│    - Wraps LangGraph execution                               │
│    - Provides uniform interface                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. Load Agent from Entrypoint                                │
│    Runtime dynamically imports:                              │
│                                                               │
│    import importlib                                          │
│    module_path, callable_name = parse_entrypoint(           │
│        "examples.invoice_copilot.app.graph:build_graph"     │
│    )                                                         │
│    # Uses: common/validation.py                              │
│                                                               │
│    module = importlib.import_module(module_path)             │
│    build_graph = getattr(module, callable_name)              │
│    agent = build_graph()  # Alice's actual agent!            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. Execute Agent (via Adapter)                               │
│    packages/adapters/dockrion_adapters/langgraph_adapter.py│
│                                                               │
│    start_time = time.time()                                  │
│                                                               │
│    result = adapter.invoke(                                  │
│        agent=agent,                                          │
│        input=body  # Bob's invoice data                      │
│    )                                                         │
│                                                               │
│    Inside adapter:                                           │
│    - Calls LangGraph's .invoke()                             │
│    - Agent processes invoice                                 │
│    - Calls OpenAI API                                        │
│    - Extracts structured data                                │
│    - Returns result                                          │
│                                                               │
│    latency = time.time() - start_time                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. Apply Safety Policies (Policy Engine)                    │
│    packages/policy-engine/dockrion_policy/policy_engine.py │
│                                                               │
│    policy = PolicyEngine.from_dockspec(spec)                 │
│                                                               │
│    Step 8a: Redact Sensitive Patterns                        │
│    ┌──────────────────────────────────────┐                │
│    │ policy-engine/redactor.py             │                │
│    │                                        │                │
│    │ For pattern in redact_patterns:       │                │
│    │     # "\b\d{16}\b" (credit cards)     │                │
│    │     result = re.sub(pattern, "[REDACTED]", result) │   │
│    │                                        │                │
│    │ Before: "Card: 1234567812345678"      │                │
│    │ After:  "Card: [REDACTED]"            │                │
│    └──────────────────────────────────────┘                │
│                                                               │
│    Step 8b: Enforce Max Output Length                        │
│    if len(result) > max_output_chars:                        │
│        result = result[:max_output_chars]                    │
│                                                               │
│    result_safe = policy.post_invoke(result)                  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 9. Log Telemetry (Telemetry)                                │
│    packages/telemetry/dockrion_telemetry/                  │
│                                                               │
│    # Log completion event                                    │
│    logger.py:                                                │
│    log_event("invocation_complete",                          │
│        agent="invoice-copilot",                              │
│        latency_ms=latency * 1000,                            │
│        status="success"                                      │
│    )                                                         │
│                                                               │
│    # Record Prometheus metrics                               │
│    prometheus_utils.py:                                      │
│    observe_request(                                          │
│        agent="invoice-copilot",                              │
│        version="v1.0.0",                                     │
│        latency_s=latency                                     │
│    )                                                         │
│    # Increments: dockrion_requests_total                    │
│    # Records: dockrion_latency_seconds histogram            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 10. Format Response (Common)                                 │
│     packages/common-py/dockrion_common/http_models.py      │
│                                                               │
│     from dockrion_common.http_models import success_response│
│                                                               │
│     response = success_response({                            │
│         "vendor": "Acme Corp",                               │
│         "invoice_number": "INV-12345",                       │
│         "total_amount": 1234.56,                             │
│         "currency": "USD",                                   │
│         "line_items": [...]                                  │
│     })                                                       │
│                                                               │
│     Returns:                                                 │
│     {                                                        │
│         "success": true,                                     │
│         "data": { ... extracted invoice data ... }           │
│     }                                                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 11. Return to Bob                                            │
│                                                               │
│     FastAPI sends HTTP 200 response                          │
│     Bob's client receives JSON                               │
└─────────────────────────────────────────────────────────────┘
```

---

### Error Handling Example

**If Bob sends invalid API key:**

```
┌─────────────────────────────────────────────────────────────┐
│ Step 2: Validate API Key                                     │
│    auth_utils.validate_api_key(wrong_key, expected)          │
│    ↓                                                         │
│    Raises: AuthError("Invalid API key")                      │
│    (from common/errors.py)                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ FastAPI Exception Handler                                    │
│                                                               │
│    @app.exception_handler(AuthError)                         │
│    async def auth_error_handler(request, exc):               │
│        from dockrion_common.http_models import error_response│
│        return JSONResponse(                                  │
│            status_code=401,                                  │
│            content=error_response(exc)                       │
│        )                                                     │
│                                                               │
│    Returns to Bob:                                           │
│    {                                                         │
│        "success": false,                                     │
│        "error": "Invalid API key",                           │
│        "code": "AUTH_ERROR"                                  │
│    }                                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Journey 3: Admin Manages API Keys and Permissions

**Persona:** Carol, platform admin managing access control

### Step 1: Carol Deploys with Auth Service (V1.1+)

In V1, auth is embedded in runtime. In V1.1+, there will be a separate Auth service.

**Flow for V1 (Embedded):**

```
┌─────────────────────────────────────────────────────────────┐
│ API Key Management in V1                                     │
│                                                               │
│ Config in Dockfile.yaml:                                     │
│   auth:                                                      │
│     mode: api_key                                            │
│     api_keys:                                                │
│       enabled: true                                          │
│     roles:                                                   │
│       - name: admin                                          │
│         permissions: [deploy, invoke, view_metrics]          │
│       - name: viewer                                         │
│         permissions: [invoke]                                │
│     rate_limits:                                             │
│       admin: "1000/m"                                        │
│       viewer: "60/m"                                         │
│                                                               │
│ Runtime reads this config at startup                         │
└─────────────────────────────────────────────────────────────┘
```

**Modules Used:**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Parse Auth Config (Schema)                                │
│    packages/schema/dockrion_schema/dockfile_v1.py          │
│                                                               │
│    class AuthCfg(BaseModel):                                 │
│        mode: Literal["jwt","api_key","oauth2"] = "api_key"  │
│        roles: List[RoleCfg] = []                             │
│        rate_limits: Dict[str,str] = {}                       │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Generate API Keys (Common)                                │
│    packages/common-py/dockrion_common/auth_utils.py        │
│                                                               │
│    new_key = generate_api_key(prefix="agd")                  │
│    # Returns: "agd_8f7g9h2j3k4l5m6n7o8p9q0r1s2t3u4v5w6x7y" │
│                                                               │
│    hashed = hash_api_key(new_key)                            │
│    # Store hashed version, show new_key to user once         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Validate Permissions (Constants)                          │
│    packages/common-py/dockrion_common/constants.py         │
│                                                               │
│    PERMISSIONS = [                                           │
│        "deploy", "rollback", "invoke",                       │
│        "view_metrics", "key_manage", "read_logs"             │
│    ]                                                         │
│                                                               │
│    # Validate that role permissions are in PERMISSIONS       │
│    for perm in role.permissions:                             │
│        if perm not in PERMISSIONS:                           │
│            raise ValidationError(f"Unknown permission: {perm}")│
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. Parse Rate Limits (Common)                                │
│    packages/common-py/dockrion_common/validation.py        │
│                                                               │
│    count, seconds = parse_rate_limit("1000/m")               │
│    # Returns: (1000, 60)                                     │
│                                                               │
│    count, seconds = parse_rate_limit("60/m")                 │
│    # Returns: (60, 60)                                       │
│                                                               │
│    # Runtime uses this to enforce rate limits                │
└─────────────────────────────────────────────────────────────┘
```

---

### Step 2: Carol's API Key is Used in Request

**When user makes request with Carol's admin key:**

```
┌─────────────────────────────────────────────────────────────┐
│ Incoming Request                                             │
│   Headers: { "X-API-Key": "agd_carol_admin_key_..." }      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 1. Validate Key (Common)                                     │
│    auth_utils.validate_api_key(provided, expected)           │
│    ✓ Key is valid                                            │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Check Rate Limit (Common + Telemetry)                    │
│                                                               │
│    rate_limit = "1000/m"  # from Carol's role               │
│    count, window = parse_rate_limit(rate_limit)              │
│    # count=1000, window=60                                   │
│                                                               │
│    # Check if Carol has exceeded limit                       │
│    current_count = get_user_request_count(user_id, window)   │
│    if current_count >= count:                                │
│        raise RateLimitError(f"Rate limit exceeded: {rate_limit}")│
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Check Permissions (Common)                                │
│                                                               │
│    requested_action = "invoke"                               │
│    user_permissions = ["deploy", "invoke", "view_metrics"]   │
│                                                               │
│    if requested_action not in user_permissions:              │
│        raise AuthError(f"Permission denied: {requested_action}")│
│                                                               │
│    ✓ Carol has "invoke" permission                           │
│    ✓ Request proceeds                                        │
└─────────────────────────────────────────────────────────────┘
```

---

## Journey 4: Developer Monitors Agent Performance

**Persona:** Alice wants to see how her agent is performing

### Step 1: Alice Checks Metrics Endpoint

**Request:**
```bash
curl http://localhost:8080/metrics
```

**Flow:**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Runtime Metrics Endpoint                                  │
│    Generated runtime.py:                                     │
│                                                               │
│    @app.get("/metrics")                                      │
│    def metrics():                                            │
│        from prometheus_client import generate_latest         │
│        return Response(                                      │
│            generate_latest(),                                │
│            media_type="text/plain"                           │
│        )                                                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. Prometheus Metrics (Telemetry)                            │
│    packages/telemetry/dockrion_telemetry/prometheus_utils.py│
│                                                               │
│    Metrics collected during invocations:                     │
│                                                               │
│    REQ_COUNT = Counter(                                      │
│        "dockrion_requests_total",                           │
│        "Total requests",                                     │
│        ["agent", "version"]                                  │
│    )                                                         │
│                                                               │
│    LATENCY = Histogram(                                      │
│        "dockrion_latency_seconds",                          │
│        "Latency seconds",                                    │
│        ["agent", "version"]                                  │
│    )                                                         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. Response to Alice                                         │
│                                                               │
│    # HELP dockrion_requests_total Total requests            │
│    # TYPE dockrion_requests_total counter                   │
│    dockrion_requests_total{agent="invoice-copilot",         │
│                             version="v1.0.0"} 1523           │
│                                                               │
│    # HELP dockrion_latency_seconds Latency seconds          │
│    # TYPE dockrion_latency_seconds histogram                │
│    dockrion_latency_seconds_bucket{agent="invoice-copilot", │
│                                     version="v1.0.0",le="0.5"} 1234│
│    dockrion_latency_seconds_bucket{agent="invoice-copilot", │
│                                     version="v1.0.0",le="1.0"} 1456│
│    dockrion_latency_seconds_sum{agent="invoice-copilot",    │
│                                   version="v1.0.0"} 1234.56  │
│    dockrion_latency_seconds_count{agent="invoice-copilot",  │
│                                     version="v1.0.0"} 1523   │
└─────────────────────────────────────────────────────────────┘
```

---

### Step 2: Alice Views Logs

**Command:**
```bash
docker logs dockrion-invoice-copilot
```

**Output (from Telemetry):**

```
{"event": "invocation_start", "agent": "invoice-copilot", "timestamp": 1699456789.123}
{"event": "invocation_complete", "agent": "invoice-copilot", "latency_ms": 234.5, "status": "success"}
{"event": "invocation_start", "agent": "invoice-copilot", "timestamp": 1699456790.456}
{"event": "invocation_complete", "agent": "invoice-copilot", "latency_ms": 189.2, "status": "success"}
{"event": "policy_violation", "agent": "invoice-copilot", "reason": "output_too_long", "timestamp": 1699456791.789}
```

**Generated by:**
```python
# packages/telemetry/dockrion_telemetry/logger.py
log_event("invocation_start", agent="invoice-copilot", timestamp=time.time())
log_event("invocation_complete", agent="invoice-copilot", latency_ms=234.5, status="success")
```

---

## Summary: Package Usage Across Journeys

| Package | Deploy | Validate | Invoke | Monitor | Auth |
|---------|--------|----------|--------|---------|------|
| **schema** | ✓ | ✓ | ✓ | | ✓ |
| **common** | ✓ | ✓ | ✓ | | ✓ |
| **sdk-python** | ✓ | ✓ | | | |
| **cli** | ✓ | ✓ | | | |
| **adapters** | ✓ | | ✓ | | |
| **policy-engine** | ✓ | | ✓ | | |
| **telemetry** | | | ✓ | ✓ | |

---

## Key Takeaways for Common Package

### 1. **errors.py** - Used Throughout All Journeys
- ✓ Validation: `ValidationError` when Dockfile is invalid
- ✓ Deployment: `DeploymentError` if build fails
- ✓ Invocation: `AuthError` for invalid keys, `RateLimitError` for exceeded limits
- ✓ Policy: `PolicyViolationError` when safety rules broken

### 2. **constants.py** - Reference Data
- ✓ Validation: Check `framework in SUPPORTED_FRAMEWORKS`
- ✓ UI: Show dropdown with `SUPPORTED_PROVIDERS`
- ✓ Auth: Validate permissions against `PERMISSIONS` list

### 3. **validation.py** - Input Validation
- ✓ Deploy: `validate_entrypoint()` ensures correct format
- ✓ Deploy: `validate_agent_name()` enforces naming rules
- ✓ Auth: `parse_rate_limit()` parses "1000/m" format

### 4. **auth_utils.py** - Security
- ✓ Setup: `generate_api_key()` creates secure keys
- ✓ Invocation: `validate_api_key()` checks every request
- ✓ Storage: `hash_api_key()` for secure storage

### 5. **http_models.py** - Consistent APIs
- ✓ Success: `success_response()` for all successful API calls
- ✓ Errors: `error_response()` formats exceptions consistently
- ✓ SDK: Parse responses uniformly

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                         USER LAND                            │
│  ┌──────────┐  ┌──────────┐  ┌─────────────────┐           │
│  │   CLI    │  │   SDK    │  │ User's Agent    │           │
│  │ (deploy, │  │ (Python  │  │ (invoice_copilot│           │
│  │ validate)│  │  client) │  │  /graph.py)     │           │
│  └─────┬────┘  └────┬─────┘  └────────┬────────┘           │
└────────┼────────────┼─────────────────┼────────────────────┘
         │            │                  │
         ▼            ▼                  ▼
┌─────────────────────────────────────────────────────────────┐
│                     Dockrion PACKAGES                       │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  COMMON (Shared by All)                              │   │
│  │  • errors.py                                         │   │
│  │  • constants.py                                      │   │
│  │  • validation.py                                     │   │
│  │  • auth_utils.py                                     │   │
│  │  • http_models.py                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│         ▲              ▲               ▲             ▲       │
│         │              │               │             │       │
│  ┌──────┴───┐   ┌─────┴────┐   ┌─────┴─────┐ ┌────┴────┐  │
│  │ SCHEMA   │   │ ADAPTERS │   │  POLICY   │ │TELEMETRY│  │
│  │(dockspec)│   │(langgraph│   │ (safety)  │ │(metrics)│  │
│  └──────────┘   └──────────┘   └───────────┘ └─────────┘  │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                     RUNTIME (Generated)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  FastAPI Server (from template)                       │   │
│  │  • POST /invoke  ← Uses: adapters, policy, telemetry │   │
│  │  • GET /health   ← Uses: common                       │   │
│  │  • GET /metrics  ← Uses: telemetry                    │   │
│  │  • GET /schema   ← Uses: schema                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  Contains: User's agent + All Dockrion packages             │
└─────────────────────────────────────────────────────────────┘
```

---

## Conclusion

The **common** package is the foundation that all other components build upon:

- 🎯 **Provides consistency** - Same errors, responses, and validation everywhere
- 🔒 **Enforces security** - Centralized auth utilities
- ✅ **Ensures quality** - Shared validation logic prevents bugs
- 📊 **Enables monitoring** - Standard models for telemetry
- 🚀 **Enables scale** - Reusable utilities reduce duplication

Every journey - from deployment to invocation to monitoring - touches the common package multiple times, making it the most critical shared component in V1.

