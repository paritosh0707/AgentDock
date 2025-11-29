import re

def redact(text: str, patterns: list[str]) -> str:
    for p in patterns or []:
        text = re.sub(p, "[REDACTED]", text)
    return text
