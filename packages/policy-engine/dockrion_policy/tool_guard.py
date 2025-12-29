def is_tool_allowed(name: str, allowed: list[str], deny_by_default: bool = True) -> bool:
    if not deny_by_default:
        return True
    return name in (allowed or [])
