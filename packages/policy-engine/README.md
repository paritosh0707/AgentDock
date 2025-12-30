# dockrion-policy

Policy engine for Dockrion - redaction, tool gating, and safety controls for AI agents.

## Installation

```bash
pip install dockrion-policy
```

## Features

- **Policy Engine**: Define and enforce policies for AI agent behavior
- **Redaction**: Automatically redact sensitive information from agent outputs
- **Tool Guard**: Gate and control access to tools based on policies

## Usage

```python
from dockrion_policy.policy_engine import PolicyEngine
from dockrion_policy.redactor import Redactor
from dockrion_policy.tool_guard import ToolGuard

# Initialize the policy engine
engine = PolicyEngine()

# Set up redaction for sensitive data
redactor = Redactor()
safe_output = redactor.redact(agent_output)

# Control tool access
guard = ToolGuard(allowed_tools=["search", "calculate"])
if guard.is_allowed("search"):
    # Execute tool
    pass
```

## License

Apache-2.0

