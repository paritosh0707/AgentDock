"""
Basic usage example for agentdock-adapters package.

Demonstrates:
1. Getting an adapter using the factory
2. Loading an agent from entrypoint
3. Invoking the agent
4. Getting metadata
5. Health checks
6. Error handling
"""

from agentdock_adapters import (
    get_adapter,
    list_supported_frameworks,
    AdapterLoadError,
    AgentExecutionError,
)


def main():
    """Demonstrate basic adapter usage"""
    
    # 1. List supported frameworks
    print("📋 Supported frameworks:")
    frameworks = list_supported_frameworks()
    for framework in frameworks:
        print(f"  - {framework}")
    print()
    
    # 2. Get adapter for LangGraph
    print("🔌 Getting LangGraph adapter...")
    adapter = get_adapter("langgraph")
    print(f"✅ Got adapter: {type(adapter).__name__}")
    print()
    
    # 3. Check metadata before loading
    print("📊 Metadata before loading:")
    metadata = adapter.get_metadata()
    for key, value in metadata.items():
        print(f"  {key}: {value}")
    print()
    
    # 4. Load agent from entrypoint
    print("📦 Loading agent...")
    # Use the invoice copilot example agent
    entrypoint = "examples.invoice_copilot.app.graph:build_graph"
    
    try:
        adapter.load(entrypoint)
        print(f"✅ Agent loaded successfully from: {entrypoint}")
    except AdapterLoadError as e:
        print(f"❌ Failed to load agent: {e}")
        return
    print()
    
    # 5. Check metadata after loading
    print("📊 Metadata after loading:")
    metadata = adapter.get_metadata()
    for key, value in metadata.items():
        print(f"  {key}: {value}")
    print()
    
    # 6. Health check
    print("🏥 Health check...")
    healthy = adapter.health_check()
    print(f"  Status: {'✅ Healthy' if healthy else '❌ Unhealthy'}")
    print()
    
    # 7. Invoke agent
    print("🚀 Invoking agent...")
    payload = {
        "document_text": "INVOICE #INV-2025-001\nVendor: Acme Corp\nTotal: $1,299.00",
        "currency_hint": "USD",
        "vendor_hint": "Acme Corporation"
    }
    
    try:
        result = adapter.invoke(payload)
        print("✅ Invocation successful!")
        print("\n📤 Input:")
        print(f"  {payload}")
        print("\n📥 Output:")
        print(f"  {result}")
    except AgentExecutionError as e:
        print(f"❌ Invocation failed: {e}")
        return
    print()
    
    # 8. Multiple invocations
    print("🔄 Testing multiple invocations...")
    for i in range(3):
        test_payload = {
            "document_text": f"INVOICE #{1000+i}",
            "currency_hint": "USD"
        }
        result = adapter.invoke(test_payload)
        invoice_num = result.get('invoice_number', 'N/A')
        vendor = result.get('vendor', 'N/A')
        print(f"  Invocation {i+1}: Invoice={invoice_num}, Vendor={vendor}")
    print()
    
    print("✨ Demo completed successfully!")


def error_handling_demo():
    """Demonstrate error handling"""
    print("\n" + "="*60)
    print("ERROR HANDLING DEMO")
    print("="*60 + "\n")
    
    adapter = get_adapter("langgraph")
    
    # Error 1: Invoke before load
    print("❌ Test 1: Invoke before load")
    try:
        adapter.invoke({"test": "data"})
    except Exception as e:
        print(f"  Caught: {type(e).__name__}: {e}")
    print()
    
    # Error 2: Load non-existent module
    print("❌ Test 2: Load non-existent module")
    try:
        adapter.load("nonexistent.module:build_agent")
    except Exception as e:
        print(f"  Caught: {type(e).__name__}")
        print(f"  Message: {str(e)[:100]}...")
    print()
    
    # Error 3: Load non-existent callable
    print("❌ Test 3: Load non-existent callable")
    try:
        adapter.load("examples.invoice_copilot.app.graph:nonexistent_function")
    except Exception as e:
        print(f"  Caught: {type(e).__name__}")
        print(f"  Message: {str(e)[:100]}...")
    print()
    
    print("✨ Error handling demo completed!")


if __name__ == "__main__":
    # Run basic demo
    main()
    
    # Run error handling demo
    error_handling_demo()

