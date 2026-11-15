"""Redaction helper for sensitive data, secrets, tokens, and audio payloads.

Ensures zero credential leakage into logs or model context.
"""

import re
from typing import Any

# Regex patterns for common sensitive tokens
PATTERNS = [
    # Gemini / Google API keys
    (re.compile(r"AIzaSy[A-Za-z0-9_-]{28,40}"), "[REDACTED_API_KEY]"),
    # General secret / auth tokens (hex or base64)
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]{16,}"), r"\1[REDACTED_TOKEN]"),
    # Generic token assignments in strings
    (re.compile(r"(?i)(key|token|password|secret|pairing_token)\s*[:=]\s*['\"]?[A-Za-z0-9._~+/-]{8,}['\"]?"), r"\1=[REDACTED]"),
]

SENSITIVE_FIELD_NAMES = {
    "gemini_api_key",
    "cyber_pairing_token",
    "api_key",
    "token",
    "password",
    "secret",
    "auth",
    "authorization",
    "pairing_token",
    "private_key",
}


def redact_text(text: str) -> str:
    """Scan and redact secret tokens from string text."""
    if not text:
        return text

    redacted = text
    for pattern, replacement in PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def redact_data(data: Any) -> Any:
    """Recursively redact dictionary, list, or primitive values."""
    if isinstance(data, str):
        return redact_text(data)

    if isinstance(data, bytes):
        return f"<bytes: {len(data)} bytes>"

    if isinstance(data, dict):
        cleaned: dict[str, Any] = {}
        for k, v in data.items():
            if str(k).lower() in SENSITIVE_FIELD_NAMES:
                cleaned[k] = "[REDACTED]"
            else:
                cleaned[k] = redact_data(v)
        return cleaned

    if isinstance(data, list | tuple | set):
        return [redact_data(item) for item in data]

    return data
