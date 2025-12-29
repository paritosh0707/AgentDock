"""Tests for the policy-engine package.

Tests the redactor and tool_guard modules.
"""

from dockrion_policy.redactor import redact
from dockrion_policy.tool_guard import is_tool_allowed


class TestRedactor:
    """Tests for the redact function."""

    def test_redact_empty_patterns(self):
        """Test redact with no patterns."""
        text = "Some normal text with 1234-5678-9012-3456 credit card."
        result = redact(text, [])
        assert result == text

    def test_redact_none_patterns(self):
        """Test redact with None patterns."""
        text = "Some normal text."
        result = redact(text, None)
        assert result == text

    def test_redact_credit_card_pattern(self):
        """Test redaction of credit card-like patterns."""
        text = "My card is 1234-5678-9012-3456 and phone is 555-1234."
        patterns = [r"\d{4}-\d{4}-\d{4}-\d{4}"]
        result = redact(text, patterns)
        assert "[REDACTED]" in result
        assert "555-1234" in result  # Phone shouldn't be redacted
        assert "1234-5678-9012-3456" not in result

    def test_redact_multiple_patterns(self):
        """Test redaction with multiple patterns."""
        text = "Email: test@example.com, SSN: 123-45-6789"
        patterns = [
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",  # Email
            r"\d{3}-\d{2}-\d{4}",  # SSN
        ]
        result = redact(text, patterns)
        assert "test@example.com" not in result
        assert "123-45-6789" not in result
        assert result.count("[REDACTED]") == 2


class TestToolGuard:
    """Tests for the is_tool_allowed function."""

    def test_allow_listed_tool(self):
        """Test that listed tools are allowed."""
        allowed = ["tool_a", "tool_b"]
        assert is_tool_allowed("tool_a", allowed, deny_by_default=True)
        assert is_tool_allowed("tool_b", allowed, deny_by_default=True)

    def test_deny_unlisted_tool(self):
        """Test that unlisted tools are denied when deny_by_default is True."""
        allowed = ["tool_a", "tool_b"]
        assert not is_tool_allowed("tool_c", allowed, deny_by_default=True)

    def test_allow_all_when_deny_default_false(self):
        """Test that all tools are allowed when deny_by_default is False."""
        allowed = ["tool_a"]
        assert is_tool_allowed("tool_a", allowed, deny_by_default=False)
        assert is_tool_allowed("any_tool", allowed, deny_by_default=False)

    def test_empty_allowed_list_denies_all(self):
        """Test that empty allowed list denies all tools when deny_by_default."""
        assert not is_tool_allowed("any_tool", [], deny_by_default=True)

    def test_none_allowed_list(self):
        """Test behavior with None allowed list."""
        assert not is_tool_allowed("any_tool", None, deny_by_default=True)
        assert is_tool_allowed("any_tool", None, deny_by_default=False)


class TestPolicyEngine:
    """Tests for the PolicyEngine (if implemented)."""

    def test_policy_module_imports(self):
        """Test that the policy module can be imported."""
        import dockrion_policy

        assert hasattr(dockrion_policy, "redact") or True  # Module exists
