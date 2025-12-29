"""Mock agent for testing purposes."""

from typing import Any, Dict


class MockAgent:
    """A simple mock agent that echoes input."""

    def invoke(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Echo the input back with a result field."""
        return {
            "result": f"Mock agent processed: {payload.get('text', 'no input')}",
            "status": "success",
        }


def build_agent():
    """Factory function to build the mock agent."""
    return MockAgent()


# Alternative names for flexibility in tests
def build_mock_agent():
    """Alternative factory function for compatibility."""
    return MockAgent()
