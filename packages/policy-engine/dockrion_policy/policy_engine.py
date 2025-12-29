from .redactor import redact
from .tool_guard import is_tool_allowed


class PolicyEngine:
    def __init__(
        self,
        tools_allowed: list[str],
        deny_by_default: bool,
        redact_patterns: list[str],
        max_out: int | None,
    ):
        self.tools_allowed = tools_allowed
        self.deny_by_default = deny_by_default
        self.redact_patterns = redact_patterns
        self.max_out = max_out

    @classmethod
    def from_dockspec(cls, spec):
        tools = spec.policies.tools.allowed if spec.policies and spec.policies.tools else []
        deny = (
            spec.policies.tools.deny_by_default if spec.policies and spec.policies.tools else True
        )
        red = spec.policies.safety.redact_patterns if spec.policies and spec.policies.safety else []
        mlen = (
            spec.policies.safety.max_output_chars
            if spec.policies and spec.policies.safety
            else None
        )
        return cls(tools, deny, red, mlen)

    def post_invoke(self, text: str) -> str:
        text = redact(text, self.redact_patterns)
        if self.max_out and len(text) > self.max_out:
            text = text[: self.max_out]
        return text

    def tool_allowed(self, name: str) -> bool:
        return is_tool_allowed(name, self.tools_allowed, self.deny_by_default)
