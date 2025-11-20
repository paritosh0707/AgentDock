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


def deploy(dockfile_path: str, target: str = "local", **kwargs) -> Dict[str, Any]:
    """Deploy an agent to a target environment.
    
    V1 Implementation: Builds a Docker image locally
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
    
    # Install dependencies
    print("Installing dependencies...")
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "-q"],
            cwd=str(runtime_dir),
            stdout=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError as e:
        raise AgentDockError(f"Failed to install dependencies: {str(e)}")
    
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
    """
    requirements = [
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "prometheus-client>=0.19.0",
        "agentdock-common>=0.1.0",
        "agentdock-adapters>=0.1.0",
        "agentdock-schema>=0.1.0"
    ]
    
    # Add framework-specific dependencies
    framework = spec.agent.framework.lower()
    if framework == "langgraph":
        requirements.append("langgraph>=0.0.1")
        requirements.append("langchain>=0.1.0")
    elif framework == "langchain":
        requirements.append("langchain>=0.1.0")
    
    # Add policy engine if policies are defined
    if spec.policies:
        requirements.append("agentdock-policy>=0.1.0")
    
    return "\n".join(requirements) + "\n"


def _render_dockerfile(spec: DockSpec) -> str:
    """Generate Dockerfile for the agent runtime.
    
    Args:
        spec: DockSpec with agent configuration
        
    Returns:
        Dockerfile content as string
    """
    port = spec.expose.port if spec.expose else 8080
    
    return f"""FROM python:3.11-slim

WORKDIR /app

# Copy runtime files
COPY .agentdock_runtime/main.py /app/main.py
COPY .agentdock_runtime/requirements.txt /app/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

EXPOSE {port}

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]
"""


def _render_runtime(spec: DockSpec) -> str:
    """Generate FastAPI runtime code for the agent.
    
    Args:
        spec: DockSpec with agent configuration
        
    Returns:
        Python code as string
    """
    # Serialize spec for embedding in runtime
    spec_json = json.dumps(spec.model_dump(), indent=2)
    
    # Determine if we need policy engine
    has_policies = spec.policies is not None
    
    # Build runtime code
    code = f'''"""
Generated AgentDock Runtime
Agent: {spec.agent.name}
Framework: {spec.agent.framework}
"""
import os
import time
from typing import Dict, Any
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from agentdock_adapters import get_adapter

# Initialize FastAPI app
app = FastAPI(
    title="{spec.agent.name}",
    description="{spec.agent.description if spec.agent.description else 'AgentDock Agent'}",
    version="1.0.0"
)

# Load agent specification
SPEC = {spec_json}

# Initialize adapter and load agent
adapter = get_adapter(SPEC["agent"]["framework"])
adapter.load(SPEC["agent"]["entrypoint"])

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
    """Invoke the agent with input payload"""
    try:
        # Get payload
        payload = await request.json()
        
        # Optional: Check API key
        api_key = request.headers.get("X-API-Key")
        if os.environ.get("AGENTDOCK_REQUIRE_AUTH", "false").lower() == "true":
            if not api_key or api_key != os.environ.get("AGENTDOCK_API_KEY", ""):
                raise HTTPException(status_code=401, detail="Invalid or missing API key")
        
        # Invoke agent
        start_time = time.time()
        result = adapter.invoke(payload)
        latency = time.time() - start_time
'''
    
    if has_policies:
        code += '''        
        # Apply policies
        result = apply_policies(result)
'''
    
    code += '''        
        # Return response
        return JSONResponse({
            "success": True,
            "output": result,
            "latency_s": round(latency, 3)
        })
        
    except Exception as e:
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
