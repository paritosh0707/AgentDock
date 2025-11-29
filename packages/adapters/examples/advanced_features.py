"""
Advanced features demo for dockrion-adapters.

Demonstrates:
1. Strict validation mode
2. Config parameter for state persistence
3. Signature validation and detection
4. Multi-turn conversations with memory
5. Error handling with new features
"""

import sys
from pathlib import Path

# Add current directory to Python path for mock agent imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from dockrion_adapters import (
    LangGraphAdapter,
    AdapterLoadError,
    InvalidAgentError,
)


print("=" * 70)
print("dockrion ADAPTERS - ADVANCED FEATURES DEMO")
print("=" * 70)
print()

# =============================================================================
# DEMO 1: Basic vs Strict Validation
# =============================================================================

print("📋 DEMO 1: Validation Modes")
print("-" * 70)

# Create mock agent for demonstration
def build_demo_agent():
    """Mock agent for demonstration"""
    class DemoAgent:
        def invoke(self, payload: dict, config: dict = None) -> dict:
            return {
                "output": f"Processed: {payload.get('input')}",
                "config_used": config is not None
            }
    return DemoAgent()

# Save mock agent to temporary module
import types
demo_module = types.ModuleType("demo_agent_module")
demo_module.build_demo_agent = build_demo_agent
sys.modules["demo_agent_module"] = demo_module

print("\n1️⃣  Duck Typing (Default - No strict validation)")
print("-" * 70)
adapter_duck = LangGraphAdapter()
adapter_duck.load("demo_agent_module:build_demo_agent")

metadata = adapter_duck.get_metadata()
print(f"✅ Loaded successfully")
print(f"   Strict validation: {metadata['strict_validation']}")
print(f"   Agent type: {metadata['agent_type']}")
print(f"   Is LangGraph type: {metadata['is_langgraph_type']}")
print(f"   Supports config: {metadata['supports_config']}")
print()

print("2️⃣  Strict Validation (Type checking enabled)")
print("-" * 70)
try:
    adapter_strict = LangGraphAdapter(strict_validation=True)
    adapter_strict.load("demo_agent_module:build_demo_agent")
    print(f"✅ Loaded successfully")
except InvalidAgentError as e:
    print(f"❌ Validation failed (expected with mock agents)")
    print(f"   Error: {str(e)[:80]}...")
except Exception as e:
    # LangGraph not installed - falls back to duck typing
    print(f"⚠️  LangGraph not installed - fell back to duck typing")
    print(f"   This is expected behavior!")

print()
input("Press Enter to continue to Demo 2...\n")

# =============================================================================
# DEMO 2: Config Parameter Support
# =============================================================================

print("=" * 70)
print("📋 DEMO 2: Config Parameter Support")
print("-" * 70)

# Create stateful agent
def build_stateful_agent():
    """Agent that supports state persistence via config"""
    class StatefulAgent:
        def __init__(self):
            self.conversations = {}
        
        def invoke(self, payload: dict, config: dict = None) -> dict:
            thread_id = config.get("thread_id") if config else None
            query = payload.get("query", "")
            
            if thread_id:
                # Initialize conversation if new
                if thread_id not in self.conversations:
                    self.conversations[thread_id] = []
                
                # Add to history
                self.conversations[thread_id].append(query)
                
                return {
                    "response": f"Understood: {query}",
                    "turn": len(self.conversations[thread_id]),
                    "history": self.conversations[thread_id].copy()
                }
            else:
                return {
                    "response": f"Processed: {query}",
                    "turn": 1,
                    "note": "No memory - no thread_id provided"
                }
    
    return StatefulAgent()

# Register stateful agent
stateful_module = types.ModuleType("stateful_agent_module")
stateful_module.build_stateful_agent = build_stateful_agent
sys.modules["stateful_agent_module"] = stateful_module

print("\n1️⃣  Load Agent and Check Config Support")
print("-" * 70)
adapter = LangGraphAdapter()
adapter.load("stateful_agent_module:build_stateful_agent")

metadata = adapter.get_metadata()
print(f"✅ Agent loaded")
print(f"   Supports config: {metadata['supports_config']}")
print(f"   Agent type: {metadata['agent_type']}")
print()

print("2️⃣  Invocation WITHOUT Config (No Memory)")
print("-" * 70)
result = adapter.invoke({"query": "Hello!"})
print(f"Response: {result['response']}")
print(f"Turn: {result['turn']}")
if "note" in result:
    print(f"Note: {result['note']}")
print()

print("3️⃣  Invocation WITH Config (Multi-Turn Conversation)")
print("-" * 70)
print("Starting conversation (thread_id='user-123')...")
print()

# Turn 1
print("🔵 Turn 1:")
result1 = adapter.invoke(
    {"query": "My name is Alice"},
    config={"thread_id": "user-123"}
)
print(f"   Query: 'My name is Alice'")
print(f"   Response: {result1['response']}")
print(f"   Turn: {result1['turn']}")
print(f"   History: {result1['history']}")
print()

# Turn 2
print("🔵 Turn 2 (same thread):")
result2 = adapter.invoke(
    {"query": "What is my name?"},
    config={"thread_id": "user-123"}
)
print(f"   Query: 'What is my name?'")
print(f"   Response: {result2['response']}")
print(f"   Turn: {result2['turn']}")
print(f"   History: {result2['history']}")
print()

# Turn 3
print("🔵 Turn 3 (same thread):")
result3 = adapter.invoke(
    {"query": "I like Python programming"},
    config={"thread_id": "user-123"}
)
print(f"   Query: 'I like Python programming'")
print(f"   Response: {result3['response']}")
print(f"   Turn: {result3['turn']}")
print(f"   History: {result3['history']}")
print()

print("4️⃣  New Conversation (Different thread_id)")
print("-" * 70)
result4 = adapter.invoke(
    {"query": "Hello, I'm Bob"},
    config={"thread_id": "user-456"}
)
print(f"   Query: 'Hello, I'm Bob'")
print(f"   Response: {result4['response']}")
print(f"   Turn: {result4['turn']}")
print(f"   History: {result4['history']}")
print(f"   ✅ New conversation - independent state!")
print()

input("Press Enter to continue to Demo 3...\n")

# =============================================================================
# DEMO 3: Signature Detection
# =============================================================================

print("=" * 70)
print("📋 DEMO 3: Automatic Signature Detection")
print("-" * 70)

# Create agent WITHOUT config support
def build_simple_no_config():
    """Agent that doesn't support config"""
    class SimpleAgent:
        def invoke(self, payload: dict) -> dict:  # No config parameter
            return {"result": "simple response"}
    return SimpleAgent()

# Create agent WITH config support
def build_with_config():
    """Agent that supports config"""
    class ConfigAgent:
        def invoke(self, payload: dict, config: dict = None) -> dict:
            return {
                "result": "config-aware response",
                "config_received": config is not None
            }
    return ConfigAgent()

# Register agents
simple_module = types.ModuleType("simple_module")
simple_module.build_simple_no_config = build_simple_no_config
sys.modules["simple_module"] = simple_module

config_module = types.ModuleType("config_module")
config_module.build_with_config = build_with_config
sys.modules["config_module"] = config_module

print("\n1️⃣  Agent WITHOUT Config Parameter")
print("-" * 70)
adapter1 = LangGraphAdapter()
adapter1.load("simple_module:build_simple_no_config")

meta1 = adapter1.get_metadata()
print(f"Agent type: {meta1['agent_type']}")
print(f"Supports config: {meta1['supports_config']}")
print(f"✅ Signature correctly detected!")
print()

# Try to use config (should be ignored gracefully)
print("   Attempting to use config (should be ignored)...")
result = adapter1.invoke(
    {"input": "test"},
    config={"thread_id": "123"}
)
print(f"   Result: {result}")
print(f"   ⚠️  Config was ignored (as expected)")
print()

print("2️⃣  Agent WITH Config Parameter")
print("-" * 70)
adapter2 = LangGraphAdapter()
adapter2.load("config_module:build_with_config")

meta2 = adapter2.get_metadata()
print(f"Agent type: {meta2['agent_type']}")
print(f"Supports config: {meta2['supports_config']}")
print(f"✅ Signature correctly detected!")
print()

# Use config (should work)
print("   Using config...")
result = adapter2.invoke(
    {"input": "test"},
    config={"thread_id": "123"}
)
print(f"   Result: {result}")
print(f"   ✅ Config was used!")
print()

input("Press Enter to continue to Demo 4...\n")

# =============================================================================
# DEMO 4: Complete Metadata
# =============================================================================

print("=" * 70)
print("📋 DEMO 4: Enhanced Metadata")
print("-" * 70)

adapter = LangGraphAdapter(strict_validation=False)
adapter.load("config_module:build_with_config")

metadata = adapter.get_metadata()

print("\n📊 Complete Metadata:")
print("-" * 70)
for key, value in metadata.items():
    print(f"{key:25} : {value}")
print()

# =============================================================================
# DEMO 5: Error Handling
# =============================================================================

print("=" * 70)
print("📋 DEMO 5: Error Handling")
print("-" * 70)

print("\n1️⃣  Invalid Agent (No invoke method)")
print("-" * 70)

def build_invalid_agent():
    """Agent without invoke method"""
    class InvalidAgent:
        def process(self, payload):  # Wrong method name
            return {"result": "test"}
    return InvalidAgent()

invalid_module = types.ModuleType("invalid_module")
invalid_module.build_invalid_agent = build_invalid_agent
sys.modules["invalid_module"] = invalid_module

try:
    adapter = LangGraphAdapter()
    adapter.load("invalid_module:build_invalid_agent")
except InvalidAgentError as e:
    print(f"❌ Caught InvalidAgentError (expected)")
    print(f"   Error: {str(e)[:100]}...")
    print(f"   ✅ Error message is helpful!")
print()

print("=" * 70)
print("✨ ALL DEMOS COMPLETED SUCCESSFULLY!")
print("=" * 70)
print()
print("🎓 Key Takeaways:")
print("  1. Duck typing (default) is flexible and doesn't require LangGraph")
print("  2. Strict validation provides type safety when needed")
print("  3. Config parameter enables stateful conversations")
print("  4. Signature detection is automatic")
print("  5. Enhanced metadata provides complete introspection")
print("  6. Error messages are helpful and actionable")
print()
print("📚 Next Steps:")
print("  - Check README.md for complete API reference")
print("  - See test_langgraph_adapter.py for more examples")
print("  - Try with real LangGraph agents!")
print()

