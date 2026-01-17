"""
Sample agents for testing adapters.

Provides mock agents that simulate LangGraph and other framework agents
without requiring actual framework dependencies.
"""

from typing import Any, Dict, Optional


def build_simple_agent():
    """
    Build a simple test agent with .invoke() method.

    Returns object that behaves like a LangGraph compiled graph.
    """

    class SimpleAgent:
        def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Simple echo agent"""
            return {"output": f"Processed: {payload.get('input', 'no input')}", "status": "success"}

    return SimpleAgent()


def build_echo_agent():
    """
    Build agent that echoes input as output.
    """

    class EchoAgent:
        def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Echo back the input"""
            return {"echo": payload}

    return EchoAgent()


def build_stateful_agent():
    """
    Build agent that supports state/config (Phase 2).

    Simulates LangGraph's config with thread_id support.
    """

    class StatefulAgent:
        def __init__(self):
            self.state = {}

        def invoke(
            self, payload: Dict[str, Any], config: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """Invoke with optional config"""
            thread_id = config.get("thread_id") if config else None

            if thread_id:
                # Simulate state persistence
                if thread_id not in self.state:
                    self.state[thread_id] = []
                self.state[thread_id].append(payload.get("input"))

                return {"output": "Processed with memory", "history": self.state[thread_id].copy()}

            return {"output": "Processed without memory"}

    return StatefulAgent()


def build_config_agent():
    """
    Build agent that explicitly accepts config parameter.

    Demonstrates LangGraph-style config support with thread_id and recursion_limit.
    """

    class ConfigAgent:
        def invoke(
            self, payload: Dict[str, Any], config: Optional[Dict[str, Any]] = None
        ) -> Dict[str, Any]:
            """Invoke with config support"""
            result = {
                "output": payload.get("input", "no input"),
                "config_received": config is not None,
            }

            if config:
                result["thread_id"] = config.get("thread_id")
                result["recursion_limit"] = config.get("recursion_limit")

            return result

    return ConfigAgent()


def build_streaming_agent():
    """
    Build agent that supports streaming (Phase 2).

    Has both .invoke() and .stream() methods.
    """

    class StreamingAgent:
        def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Standard invoke"""
            return {"output": "Complete result"}

        def stream(self, payload: Dict[str, Any]):
            """Stream results chunk by chunk"""
            chunks = [
                {"type": "token", "content": "First"},
                {"type": "token", "content": " chunk"},
                {"type": "result", "data": {"final": "result"}},
            ]
            for chunk in chunks:
                yield chunk

    return StreamingAgent()


def build_async_agent():
    """
    Build agent that supports async (Phase 2).

    Has both .invoke() and .ainvoke() methods.
    """

    class AsyncAgent:
        def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Sync invoke"""
            return {"output": "sync result"}

        async def ainvoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Async invoke"""
            return {"output": "async result"}

    return AsyncAgent()


def build_crashing_agent():
    """
    Build agent that crashes on invoke (for error testing).
    """

    class CrashingAgent:
        def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Always crashes"""
            raise RuntimeError("Agent crashed intentionally")

    return CrashingAgent()


def build_invalid_output_agent():
    """
    Build agent that returns invalid output (not dict).
    """

    class InvalidOutputAgent:
        def invoke(self, payload: Dict[str, Any]) -> str:
            """Returns string instead of dict"""
            return "This is a string, not a dict"

    return InvalidOutputAgent()


def build_agent_without_invoke():
    """
    Build object that's missing .invoke() method (for error testing).
    """

    class InvalidAgent:
        def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
            """Wrong method name"""
            return {"output": "result"}

    return InvalidAgent()


# Factory function that raises an error
def build_failing_factory():
    """Factory that crashes (for error testing)"""
    raise ValueError("Factory intentionally failed")


# Not a factory - returns class not instance
def build_class_not_instance():
    """Returns class instead of instance (for error testing)"""

    class SomeAgent:
        def invoke(self, payload):
            return {"output": "result"}

    return SomeAgent  # Returns class, not instance!
