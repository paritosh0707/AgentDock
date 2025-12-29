"""
Standalone demonstration of dockrion-adapters.

This example creates a mock agent inline and demonstrates all adapter features
without requiring external dependencies or imports.
"""

import sys
from pathlib import Path

# Add current directory to Python path so we can import our mock agent
sys.path.insert(0, str(Path(__file__).parent))

from dockrion_adapters import (
    get_adapter,
    get_adapter_info,
    is_framework_supported,
    list_supported_frameworks,
)

# =============================================================================
# MOCK AGENT (simulates a real LangGraph agent)
# =============================================================================


def build_demo_agent():
    """
    Build a demo agent that simulates invoice processing.

    This is what a user would typically define in their codebase.
    """

    class InvoiceAgent:
        """Mock invoice processing agent"""

        def invoke(self, payload: dict) -> dict:
            """Process invoice and extract information"""
            document = payload.get("document_text", "")

            return {
                "vendor": payload.get("vendor_hint", "Unknown Vendor"),
                "invoice_number": "INV-2025-001",
                "invoice_date": "2025-11-14",
                "total_amount": 1299.00,
                "currency": payload.get("currency_hint", "USD"),
                "line_items": [
                    {
                        "description": "GPU Hosting",
                        "quantity": 1,
                        "unit_price": 1299.00,
                        "amount": 1299.00,
                    }
                ],
                "notes": "Processed by demo agent",
                "metadata": {"processed_at": "2025-11-14T10:00:00Z", "agent_version": "1.0.0"},
            }

    return InvoiceAgent()


# =============================================================================
# DEMONSTRATIONS
# =============================================================================


def demo_framework_discovery():
    """Demo 1: Discover available frameworks"""
    print("=" * 60)
    print("DEMO 1: Framework Discovery")
    print("=" * 60 + "\n")

    # List all supported frameworks
    print("📋 Supported frameworks:")
    frameworks = list_supported_frameworks()
    for framework in frameworks:
        print(f"  ✓ {framework}")
    print()

    # Check specific frameworks
    print("🔍 Framework checks:")
    test_frameworks = ["langgraph", "langchain", "crewai"]
    for framework in test_frameworks:
        supported = is_framework_supported(framework)
        status = "✅ Supported" if supported else "❌ Not supported"
        print(f"  {framework}: {status}")
    print()

    # Get adapter info
    print("📊 LangGraph adapter info:")
    info = get_adapter_info("langgraph")
    for key, value in info.items():
        print(f"  {key}: {value}")
    print()


def demo_basic_usage():
    """Demo 2: Basic adapter usage"""
    print("=" * 60)
    print("DEMO 2: Basic Usage")
    print("=" * 60 + "\n")

    # Step 1: Get adapter
    print("🔌 Getting LangGraph adapter...")
    adapter = get_adapter("langgraph")
    print(f"✅ Created: {type(adapter).__name__}\n")

    # Step 2: Check metadata before loading
    print("📊 Initial metadata:")
    metadata = adapter.get_metadata()
    print(f"  Loaded: {metadata['loaded']}")
    print(f"  Framework: {metadata['framework']}")
    print(f"  Version: {metadata['adapter_version']}")
    print()

    # Step 3: Load agent
    print("📦 Loading agent...")
    entrypoint = "__main__:build_demo_agent"
    adapter.load(entrypoint)
    print(f"✅ Agent loaded from: {entrypoint}\n")

    # Step 4: Check metadata after loading
    print("📊 Metadata after loading:")
    metadata = adapter.get_metadata()
    print(f"  Loaded: {metadata['loaded']}")
    print(f"  Agent type: {metadata['agent_type']}")
    print(f"  Entrypoint: {metadata['entrypoint']}")
    print()

    # Step 5: Health check
    print("🏥 Health check...")
    healthy = adapter.health_check()
    print(f"  Status: {'✅ Healthy' if healthy else '❌ Unhealthy'}\n")

    return adapter


def demo_invocation(adapter):
    """Demo 3: Agent invocation"""
    print("=" * 60)
    print("DEMO 3: Agent Invocation")
    print("=" * 60 + "\n")

    # Single invocation
    print("🚀 Invoking agent...")
    payload = {
        "document_text": "INVOICE #INV-2025-001\nVendor: Acme Corp\nTotal: $1,299.00",
        "currency_hint": "USD",
        "vendor_hint": "Acme Corporation",
    }

    result = adapter.invoke(payload)

    print("✅ Invocation successful!\n")
    print("📤 Input:")
    print(f"  Document: {payload['document_text'][:50]}...")
    print(f"  Currency: {payload['currency_hint']}")
    print(f"  Vendor Hint: {payload['vendor_hint']}")
    print()

    print("📥 Output:")
    print(f"  Vendor: {result['vendor']}")
    print(f"  Invoice #: {result['invoice_number']}")
    print(f"  Date: {result['invoice_date']}")
    print(f"  Amount: ${result['total_amount']} {result['currency']}")
    print(f"  Line Items: {len(result['line_items'])} item(s)")
    print()


def demo_multiple_invocations(adapter):
    """Demo 4: Multiple invocations"""
    print("=" * 60)
    print("DEMO 4: Multiple Invocations")
    print("=" * 60 + "\n")

    print("🔄 Processing multiple invoices...\n")

    invoices = [
        {"vendor_hint": "Acme Corp", "currency_hint": "USD"},
        {"vendor_hint": "Tech Solutions", "currency_hint": "EUR"},
        {"vendor_hint": "Global Industries", "currency_hint": "GBP"},
    ]

    for i, invoice_data in enumerate(invoices, 1):
        payload = {"document_text": f"INVOICE #{1000 + i}", **invoice_data}

        result = adapter.invoke(payload)

        print(f"  Invoice {i}:")
        print(f"    Vendor: {result['vendor']}")
        print(f"    Number: {result['invoice_number']}")
        print(f"    Amount: ${result['total_amount']} {result['currency']}")

    print()


def demo_error_handling():
    """Demo 5: Error handling"""
    print("=" * 60)
    print("DEMO 5: Error Handling")
    print("=" * 60 + "\n")

    adapter = get_adapter("langgraph")

    # Error 1: Invoke before load
    print("❌ Test 1: Invoke before load")
    try:
        adapter.invoke({"test": "data"})
    except Exception as e:
        print(f"  Caught: {type(e).__name__}")
        print(f"  Message: {str(e)}\n")

    # Error 2: Module not found
    print("❌ Test 2: Module not found")
    try:
        adapter.load("nonexistent.module:build_agent")
    except Exception as e:
        print(f"  Caught: {type(e).__name__}")
        print(f"  Message: {str(e)[:80]}...\n")

    # Error 3: Callable not found
    print("❌ Test 3: Callable not found")
    try:
        adapter.load("__main__:nonexistent_function")
    except Exception as e:
        print(f"  Caught: {type(e).__name__}")
        print(f"  Message: {str(e)[:80]}...\n")

    print("✅ All error cases handled correctly!\n")


def demo_adapter_lifecycle():
    """Demo 6: Complete adapter lifecycle"""
    print("=" * 60)
    print("DEMO 6: Adapter Lifecycle")
    print("=" * 60 + "\n")

    print("📝 Lifecycle stages:\n")

    # Stage 1: Creation
    print("1️⃣  Creation")
    adapter = get_adapter("langgraph")
    print(f"   Created adapter: {type(adapter).__name__}")
    print(f"   Loaded: {adapter.get_metadata()['loaded']}\n")

    # Stage 2: Loading
    print("2️⃣  Loading")
    adapter.load("__main__:build_demo_agent")
    print(f"   Loaded agent: {adapter.get_metadata()['agent_type']}")
    print(f"   Loaded: {adapter.get_metadata()['loaded']}\n")

    # Stage 3: Health check
    print("3️⃣  Health Check")
    healthy = adapter.health_check()
    print(f"   Status: {'Healthy ✅' if healthy else 'Unhealthy ❌'}\n")

    # Stage 4: Invocation
    print("4️⃣  Invocation")
    result = adapter.invoke({"test": "data"})
    print("   Invoked successfully")
    print(f"   Result keys: {', '.join(result.keys())}\n")

    # Stage 5: Re-loading (replacing agent)
    print("5️⃣  Re-loading")
    adapter.load("__main__:build_demo_agent")  # Load again
    print("   Agent reloaded")
    print("   Can invoke again: ✅\n")


# =============================================================================
# MAIN
# =============================================================================


def main():
    """Run all demonstrations"""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "dockrion ADAPTERS - DEMO" + " " * 23 + "║")
    print("╚" + "═" * 58 + "╝")
    print()

    # Run all demos
    demo_framework_discovery()
    input("Press Enter to continue to next demo...\n")

    adapter = demo_basic_usage()
    input("Press Enter to continue to next demo...\n")

    demo_invocation(adapter)
    input("Press Enter to continue to next demo...\n")

    demo_multiple_invocations(adapter)
    input("Press Enter to continue to next demo...\n")

    demo_error_handling()
    input("Press Enter to continue to next demo...\n")

    demo_adapter_lifecycle()

    print("=" * 60)
    print("✨ ALL DEMOS COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print()
    print("📚 Next steps:")
    print("  - Check out the README.md for more information")
    print("  - Run tests with: uv run pytest tests/ -v")
    print("  - Read the source code in dockrion_adapters/")
    print()


if __name__ == "__main__":
    main()
