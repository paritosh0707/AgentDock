"""
Policy Engine Integration for Dockrion Runtime

Provides input validation, output redaction, and safety checks.
"""

import re
import json
from typing import Dict, Any, List, Optional

from dockrion_common.errors import ValidationError
from dockrion_common.logger import get_logger

logger = get_logger(__name__)


class RuntimePolicyEngine:
    """
    Applies policies to agent inputs and outputs.
    
    Features:
        - Input validation (prompt injection detection)
        - Output redaction (PII, credit cards, etc.)
        - Output length limits
        - Tool allowlists
    """
    
    def __init__(
        self,
        redact_patterns: Optional[List[str]] = None,
        max_output_chars: Optional[int] = None,
        block_prompt_injection: bool = True,
        allowed_tools: Optional[List[str]] = None,
        deny_tools_by_default: bool = True
    ):
        """
        Initialize policy engine.
        
        Args:
            redact_patterns: Regex patterns to redact from output
            max_output_chars: Maximum output length (truncates if exceeded)
            block_prompt_injection: Whether to check for injection attempts
            allowed_tools: List of allowed tool names
            deny_tools_by_default: If True, only allowed_tools can be used
        """
        self.redact_patterns = redact_patterns or []
        self.max_output_chars = max_output_chars
        self.block_prompt_injection = block_prompt_injection
        self.allowed_tools = allowed_tools or []
        self.deny_tools_by_default = deny_tools_by_default
        
        # Compile redact patterns for efficiency
        self._compiled_patterns = [
            re.compile(pattern) for pattern in self.redact_patterns
        ]
        
        # Common prompt injection patterns
        self._injection_patterns = [
            re.compile(r"ignore\s+(previous|above|all)\s+instructions", re.IGNORECASE),
            re.compile(r"system\s*:\s*", re.IGNORECASE),
            re.compile(r"<\|.*\|>"),
            re.compile(r"\[INST\].*\[/INST\]", re.IGNORECASE),
        ]
    
    def validate_input(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and sanitize input payload.
        
        Args:
            payload: Input dictionary
            
        Returns:
            Validated payload (unchanged if valid)
            
        Raises:
            ValidationError: If input violates policies
        """
        if not self.block_prompt_injection:
            return payload
        
        # Convert payload to string for pattern matching
        payload_str = json.dumps(payload)
        
        for pattern in self._injection_patterns:
            if pattern.search(payload_str):
                logger.warning(f"Potential prompt injection detected: {pattern.pattern}")
                raise ValidationError("Potential prompt injection detected")
        
        return payload
    
    def apply_output_policies(self, output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply output policies (redaction, length limits).
        
        Args:
            output: Output dictionary from agent
            
        Returns:
            Processed output with policies applied
        """
        # Convert to string for processing
        output_str = json.dumps(output)
        
        # Apply redaction patterns
        for pattern in self._compiled_patterns:
            output_str = pattern.sub("[REDACTED]", output_str)
        
        # Apply length limit
        if self.max_output_chars and len(output_str) > self.max_output_chars:
            logger.warning(
                f"Output truncated from {len(output_str)} to {self.max_output_chars} chars"
            )
            output_str = output_str[:self.max_output_chars]
            # Try to parse truncated JSON, fall back to wrapping in object
            try:
                return json.loads(output_str)
            except json.JSONDecodeError:
                return {"output": output_str, "_truncated": True}
        
        return json.loads(output_str)
    
    def is_tool_allowed(self, tool_name: str) -> bool:
        """
        Check if a tool is allowed.
        
        Args:
            tool_name: Name of the tool to check
            
        Returns:
            True if allowed, False otherwise
        """
        if not self.deny_tools_by_default:
            return True
        return tool_name in self.allowed_tools


def create_policy_engine(policies_config: Optional[dict]) -> RuntimePolicyEngine:
    """
    Factory function to create RuntimePolicyEngine from config.
    
    Args:
        policies_config: Policies section from DockSpec
        
    Returns:
        Configured RuntimePolicyEngine instance
    """
    if not policies_config:
        return RuntimePolicyEngine()
    
    safety = policies_config.get("safety", {})
    tools = policies_config.get("tools", {})
    
    return RuntimePolicyEngine(
        redact_patterns=safety.get("redact_patterns"),
        max_output_chars=safety.get("max_output_chars"),
        block_prompt_injection=safety.get("block_prompt_injection", True),
        allowed_tools=tools.get("allowed"),
        deny_tools_by_default=tools.get("deny_by_default", True)
    )

