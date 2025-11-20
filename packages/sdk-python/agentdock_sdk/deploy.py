import subprocess
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional
from agentdock_sdk.client import load_dockspec
# from agentdock_schema.dockfile_v1 import DockSpec
from agentdock_schema import DockSpec
from agentdock_common.errors import AgentDockError


def _check_uv_available() -> bool:
    """Check if uv package manager is available.
    
    Returns:
        True if uv is available, False otherwise
    """
    try:
        subprocess.check_output(
            ["uv", "--version"],
            stderr=subprocess.STDOUT,
            text=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def _print_uv_setup_instructions():
    """Print instructions for installing uv package manager."""
    print("\n" + "="*70)
    print("⚠️  UV Package Manager Not Found")
    print("="*70)
    print("\nAgentDock uses 'uv' for fast, reliable package management.")
    print("\n📦 Quick Setup (recommended):")
    print("\n  On macOS/Linux:")
    print("    curl -LsSf https://astral.sh/uv/install.sh | sh")
    print("\n  On Windows:")
    print("    powershell -c \"irm https://astral.sh/uv/install.ps1 | iex\"")
    print("\n  Using pip:")
    print("    pip install uv")
    print("\n  Using pipx:")
    print("    pipx install uv")
    print("\n📚 Learn more: https://github.com/astral-sh/uv")
    print("\n💡 Note: Docker builds will still work (uv is installed in the container)")
    print("   but local development benefits from having uv installed.")
    print("="*70 + "\n")


def deploy(dockfile_path: str, target: str = "local", **kwargs) -> Dict[str, Any]:
    """Deploy an agent to a target environment.
    
    V1 Implementation: Builds a Docker image locally using uv package manager
    V1.1+: Will support remote deployment via Controller
    
    Args:
        dockfile_path: Path to the Dockfile
        target: Deployment target ("local" for V1)
        **kwargs: Additional deployment options
        
    Returns:
        Dictionary with deployment information:
        {
            "image": str,  # Docker image name
            "status": str,  # "built" or "failed"
            "agent_name": str
        }
        
    Raises:
        AgentDockError: If deployment fails
        
    Example:
        >>> result = deploy("Dockfile.yaml", target="local")
        >>> print(result["image"])
        agentdock/invoice-copilot:dev
    """
    # Check if uv is available (informational only - Docker will install it)
    if not _check_uv_available():
        _print_uv_setup_instructions()
        print("ℹ️  Continuing with Docker build (uv will be installed in container)...\n")
    
    # Load and validate Dockfile
    try:
        spec = load_dockspec(dockfile_path)
    except Exception as e:
        raise AgentDockError(f"Failed to load Dockfile: {str(e)}")
    
    # Build Docker image
    image = f"agentdock/{spec.agent.name}:dev"
    
    # Check if Docker is available
    try:
        subprocess.check_output(
            ["docker", "--version"],
            stderr=subprocess.STDOUT,
            text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        raise AgentDockError(
            "Docker is not available. Please install Docker to deploy agents.\n"
            "Visit: https://docs.docker.com/get-docker/"
        )
    
    # Generate runtime files (needed for Docker build)
    runtime_dir = Path(".agentdock_runtime")
    runtime_dir.mkdir(exist_ok=True)
    
    # Write runtime code
    runtime_code = _render_runtime(spec)
    main_file = runtime_dir / "main.py"
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(runtime_code)
    
    # Write requirements.txt
    requirements = _generate_requirements(spec)
    req_file = runtime_dir / "requirements.txt"
    with open(req_file, "w", encoding="utf-8") as f:
        f.write(requirements)
    
    # Build the image
    try:
        dockerfile_content = _render_dockerfile(spec)
        result = subprocess.run(
            ["docker", "build", "-t", image, "-f", "-", "."],
            input=dockerfile_content.encode(),
            cwd=".",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
    except subprocess.CalledProcessError as e:
        raise AgentDockError(
            f"Docker build failed for agent '{spec.agent.name}'.\n"
            f"Error: {e.stderr.decode() if e.stderr else 'Unknown error'}"
        )
    
    return {
        "image": image,
        "status": "built",
        "agent_name": spec.agent.name
    }


def run_local(dockfile_path: str) -> subprocess.Popen:
    """Run an agent locally without Docker (development mode).
    
    This function:
    1. Loads the Dockfile
    2. Generates a FastAPI runtime
    3. Installs dependencies
    4. Starts the server with uvicorn
    
    Args:
        dockfile_path: Path to the Dockfile
        
    Returns:
        Subprocess.Popen object (running server)
        
    Raises:
        AgentDockError: If startup fails
        
    Example:
        >>> proc = run_local("Dockfile.yaml")
        >>> # Server is now running...
        >>> proc.terminate()  # Stop the server
    """
    # Load and validate Dockfile
    try:
        spec = load_dockspec(dockfile_path)
    except Exception as e:
        raise AgentDockError(f"Failed to load Dockfile: {str(e)}")
    
    # Generate runtime code
    code = _render_runtime(spec)
    
    # Create runtime directory
    runtime_dir = Path(".agentdock_runtime")
    runtime_dir.mkdir(exist_ok=True)
    
    # Write runtime code
    main_file = runtime_dir / "main.py"
    with open(main_file, "w", encoding="utf-8") as f:
        f.write(code)
    
    # Write requirements.txt
    requirements = _generate_requirements(spec)
    req_file = runtime_dir / "requirements.txt"
    with open(req_file, "w", encoding="utf-8") as f:
        f.write(requirements)
    
    # Install dependencies using uv (if available) or pip
    print("Installing dependencies...")
    
    # Check if uv is available
    use_uv = _check_uv_available()
    
    if use_uv:
        print("  Using uv package manager (fast!)...")
        try:
            # Note: Don't use --system flag for local dev (requires admin/root)
            # uv will automatically use the active virtual environment
            subprocess.check_call(
                ["uv", "pip", "install", "-r", "requirements.txt", "-q"],
                cwd=str(runtime_dir),
                stdout=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError as e:
            raise AgentDockError(f"Failed to install dependencies with uv: {str(e)}")
    else:
        print("  Using pip (consider installing uv for faster installs)...")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
                cwd=str(runtime_dir),
                stdout=subprocess.DEVNULL
            )
        except subprocess.CalledProcessError as e:
            raise AgentDockError(f"Failed to install dependencies with pip: {str(e)}")
    
    # Start the server
    host = spec.expose.host if spec.expose else "0.0.0.0"
    port = str(spec.expose.port if spec.expose else 8080)
    
    print(f"Starting agent server at http://{host}:{port}")
    
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", host, "--port", port],
            cwd=str(runtime_dir)
        )
        return proc
    except Exception as e:
        raise AgentDockError(f"Failed to start server: {str(e)}")

def _generate_requirements(spec: DockSpec) -> str:
    """Generate requirements.txt for the runtime.
    
    Args:
        spec: DockSpec with agent configuration
        
    Returns:
        requirements.txt content as string
        
    Note:
        AgentDock packages will be installed from local copies bundled in the image.
        This allows us to use the full adapter layer and schema validation.
    """
    requirements = [
        # Core dependencies
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "prometheus-client>=0.19.0",
        "pydantic>=2.0.0",
        "pyyaml>=6.0"
    ]
    
    # Add framework-specific dependencies
    framework = spec.agent.framework.lower()
    if framework == "langgraph":
        requirements.append("langgraph>=0.0.1")
        requirements.append("langchain>=0.1.0")
    elif framework == "langchain":
        requirements.append("langchain>=0.1.0")
    
    # Note: agentdock-* packages will be installed from /agentdock_packages/
    # in the Dockerfile using pip install -e
    
    return "\n".join(requirements) + "\n"


def _render_dockerfile(spec: DockSpec) -> str:
    """Generate Dockerfile for the agent runtime.
    
    Args:
        spec: DockSpec with agent configuration
        
    Returns:
        Dockerfile content as string
    """
    port = spec.expose.port if spec.expose else 8080
    
    # Extract module path from entrypoint to copy agent code
    entrypoint = spec.agent.entrypoint
    if ":" in entrypoint:
        module_path = entrypoint.rsplit(":", 1)[0]
        # Convert module path to directory path (e.g., "app.graph" -> "app/")
        agent_dir = module_path.split(".")[0]
    else:
        agent_dir = "app"
    
    return f"""FROM python:3.12-slim

WORKDIR /app

# Install uv package manager (fast, reliable Python package installer)
# https://github.com/astral-sh/uv
RUN apt-get update && apt-get install -y curl && \\
    curl -LsSf https://astral.sh/uv/install.sh | sh && \\
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Add uv to PATH (installed to /root/.local/bin)
ENV PATH="/root/.local/bin:$PATH"

# Copy AgentDock packages (to be installed locally)
COPY packages/common-py/ /agentdock_packages/common-py/
COPY packages/schema/ /agentdock_packages/schema/
COPY packages/adapters/ /agentdock_packages/adapters/

# Copy agent code
COPY {agent_dir}/ /app/{agent_dir}/

# Copy runtime files
COPY .agentdock_runtime/main.py /app/main.py
COPY .agentdock_runtime/requirements.txt /app/requirements.txt

# Install AgentDock packages first (from local copies) using uv
RUN uv pip install --system -e /agentdock_packages/common-py && \\
    uv pip install --system -e /agentdock_packages/schema && \\
    uv pip install --system -e /agentdock_packages/adapters

# Install other dependencies using uv
RUN uv pip install --system -r /app/requirements.txt

EXPOSE {port}

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]
"""


def _render_runtime(spec: DockSpec) -> str:
    """Generate FastAPI runtime code for the agent.
    
    Args:
        spec: DockSpec with agent configuration
        
    Returns:
        Python code as string
        
    Note:
        The generated runtime is self-contained and doesn't depend on
        agentdock packages. It directly loads and invokes the agent.
    """
    # Serialize spec for embedding in runtime
    spec_json = json.dumps(spec.model_dump(), indent=2)
    
    # Determine if we need policy engine
    has_policies = spec.policies is not None
    
    # Get entrypoint details
    entrypoint = spec.agent.entrypoint
    
    # Build runtime code
    code = f'''"""
Generated AgentDock Runtime
Agent: {spec.agent.name}
Framework: {spec.agent.framework}

This runtime leverages the full AgentDock infrastructure:
- Adapter layer for framework-agnostic agent invocation
- Schema validation for inputs/outputs
- Common utilities for error handling and logging
"""
import os
import time
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

# Import AgentDock packages
from agentdock_adapters import get_adapter
from agentdock_schema import DockSpec
from agentdock_common.errors import AgentDockError, ValidationError
from agentdock_common.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="{spec.agent.name}",
    description="{spec.agent.description if spec.agent.description else 'AgentDock Agent'}",
    version="1.0.0"
)

# Load agent specification
SPEC_DATA = {spec_json}
SPEC = DockSpec.model_validate(SPEC_DATA)

# Initialize adapter and load agent
logger.info(f"Initializing {{SPEC.agent.framework}} adapter...")
adapter = get_adapter(SPEC.agent.framework)

logger.info(f"Loading agent from {{SPEC.agent.entrypoint}}...")
adapter.load(SPEC.agent.entrypoint)

logger.info(f"Agent {{SPEC.agent.name}} loaded successfully")

'''
    
    # Add policy engine if needed
    if has_policies:
        code += '''
# Initialize policy engine (placeholder for V1)
# Full policy implementation in V1.1+
def apply_policies(output: Dict[str, Any]) -> Dict[str, Any]:
    """Apply safety policies to output"""
    # TODO: Implement full policy engine integration
    return output

'''
    
    # Add endpoints
    code += '''
@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "agent": SPEC["agent"]["name"]}


@app.get("/schema")
async def get_schema():
    """Get input/output schema"""
    return SPEC.get("io_schema", {})


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


@app.post("/invoke")
async def invoke(request: Request):
    """Invoke the agent with input payload.
    
    Uses the adapter layer for framework-agnostic invocation.
    """
    try:
        # Get payload
        payload = await request.json()
        
        logger.info(f"Received invocation request: {{payload}}")
        
        # Optional: Check API key
        api_key = request.headers.get("X-API-Key")
        if os.environ.get("AGENTDOCK_REQUIRE_AUTH", "false").lower() == "true":
            if not api_key or api_key != os.environ.get("AGENTDOCK_API_KEY", ""):
                logger.warning("Unauthorized access attempt")
                raise HTTPException(status_code=401, detail="Invalid or missing API key")
        
        # Optional: Validate input against schema
        if SPEC.io_schema and SPEC.io_schema.input:
            # TODO: Add input validation in V1.1+
            pass
        
        # Invoke agent using adapter layer
        logger.info("Invoking agent via adapter...")
        start_time = time.time()
        result = adapter.invoke(payload)
        latency = time.time() - start_time
        
        logger.info(f"Agent invocation completed in {{latency:.3f}}s")
'''
    
    if has_policies:
        code += '''        
        # Apply policies
        result = apply_policies(result)
'''
    
    code += '''        
        # Optional: Validate output against schema
        if SPEC.io_schema and SPEC.io_schema.output:
            # TODO: Add output validation in V1.1+
            pass
        
        # Return response
        return JSONResponse({
            "success": True,
            "output": result,
            "latency_s": round(latency, 3),
            "agent": SPEC.agent.name,
            "framework": SPEC.agent.framework
        })
        
    except ValidationError as e:
        logger.error(f"Validation error: {{e}}")
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": str(e),
                "error_type": "ValidationError"
            }
        )
    except AgentDockError as e:
        logger.error(f"AgentDock error: {{e}}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "error_type": "AgentDockError"
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error: {{e}}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
'''
    
    return code
