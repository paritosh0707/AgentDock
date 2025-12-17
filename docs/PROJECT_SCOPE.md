# Dockrion – Current Scope (Reflection)

**Date:** 2025-12-12  
**Purpose:** A crisp “stop-and-reflect” snapshot of what is implemented in `packages/`, what each package owns, and how they connect end-to-end.

## Product Goal (PRD-aligned, V1)

**Turn user agent code into a framework-agnostic, deployable HTTP runtime** driven by a `Dockfile.yaml`.

- **Agent code stays independent** of Dockrion internals (user writes agent; Dockrion loads/invokes via adapters).
- **One command path** to validate → generate runtime → run locally or build a container image.
- **Runtime output** is a FastAPI service (local or containerized) exposing consistent endpoints (`/invoke`, `/health`, `/schema`, `/metrics`, etc.).

> PRD reference: `docs/prd/AgentDock_PRD.pdf` (and `docs/prd/README.md`).

## Core Workflow (Matches the “initial phase” diagram)

1. **User code**: agent implementation in repo (any folder); Dockfile points to an entrypoint `module.path:callable`.
2. **SDK (`packages/sdk-python`)**
   - loads + validates Dockfile
   - generates runtime code via templates → writes to `.dockrion_runtime/`
   - runs locally (uvicorn) *or* builds a Docker image
3. **Generated runtime (FastAPI)**
   - embeds Dockfile content as `SPEC_DATA`
   - uses **adapters** to load/invoke the agent
   - provides health, schema, metrics, and invocation endpoints

## Package Scope (at a glance)

| Package | Responsibility (what it owns) | Key APIs / Capabilities (implemented) | Depends on | Used by |
|---|---|---|---|---|
| `packages/common-py` (`dockrion_common`) | Shared primitives | errors, constants, validation helpers, auth helpers, HTTP models, structured JSON logger | external-only | schema, adapters, SDK, CLI |
| `packages/schema` (`dockrion_schema`) | Dockfile structure + validation | `DockSpec` + nested Pydantic models; validates via `dockrion_common`; forward-compatible (`extra=\"allow\"`) | common | SDK, generated runtime |
| `packages/adapters` (`dockrion_adapters`) | Framework abstraction | `get_adapter()`, registry, LangGraph adapter (load+invoke+errors), `register_adapter()` (future runtime wiring) | common | SDK, generated runtime |
| `packages/sdk-python` (`dockrion_sdk`) | Orchestration engine | Dockfile load (YAML + env expand), runtime generation (Jinja), local run (uvicorn), docker build, docker helpers | common, schema, adapters | CLI, programmatic users |
| `packages/cli` (`dockrion_cli`) | Human interface | `dockrion validate/build/run/logs/init/info/test` (Typer); mostly delegates to SDK | SDK (+ common) | end-users |
| `packages/policy-engine` (`dockrion_policy`) | Policy enforcement library | `PolicyEngine.from_dockspec()`, `post_invoke()`, `tool_allowed()` | (schema optional), common | intended for runtime/services |
| `packages/telemetry` (`dockrion_telemetry`) | Telemetry helpers | Prometheus counters/histograms helpers (minimal) | external-only | intended for runtime/services |

### Reality check (important correlations)
- **Generated runtime template** uses `dockrion_adapters`, `dockrion_schema`, `dockrion_common` directly.
- **Policies + metrics are currently implemented inside the runtime template** (inline policy logic + direct `prometheus_client` metrics), not via `dockrion_policy` / `dockrion_telemetry` yet.

## Correlation & Dependency Direction

**Dependency rule (by design):** top-level interfaces depend on lower-level primitives, never the reverse.

- **Top-level:** CLI → SDK
- **Core libraries:** SDK → (schema, common, adapters)
- **Runtime:** generated FastAPI runtime → (adapters, schema, common) + direct `prometheus_client`
- **Foundations:** common, telemetry (should remain low-dependency)
- **Optional enforcement:** policy-engine (intended to be used by runtime/services)

## What’s Implemented vs Planned (Very Short)

- **Implemented now (V1):** validate Dockfile, generate FastAPI runtime, run locally, build docker image locally.
- **Planned next (V1.1+):** Controller-based remote deploy (`deploy_cmd.py` placeholder), deeper policy/telemetry package integration in the runtime template, broader adapter coverage (LangChain/etc.), custom adapter config surfaced in schema.

## Where to Read More (Existing deeper docs)

- Package boundaries (detailed): `docs/PACKAGE_RESPONSIBILITIES.md`
- Runtime architecture: `DOCKER_RUNTIME_ARCHITECTURE.md`
- Schema vs SDK responsibilities: `docs/ARCHITECTURE_CLARIFICATION.md`


