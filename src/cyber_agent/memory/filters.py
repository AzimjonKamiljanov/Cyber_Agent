"""Filters and safety guards for memory storage.

Security Invariants:
1. Never store passwords, API keys, bank data, recovery codes, or PINs.
2. Filter memory content before persistence.
"""

from __future__ import annotations

import re

# Patterns matching sensitive secrets that must NEVER be persisted in memory
SECRET_PATTERNS = [
    re.compile(r"(?i)\b(?:password|parol[ia]?|pwd|secret)\s*[:=]\s*\S+"),
    re.compile(r"(?i)\b(?:pin(?:\s*kod[ia]?)?)\s*[:=]?\s*\d{4,8}\b"),
    re.compile(r"\bAIza[0-9A-Za-z-_]{35}\b"),  # Google API Key
    re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"),  # OpenAI/Generic secret key
    re.compile(r"\bghp_[a-zA-Z0-9]{36}\b"),  # GitHub Personal Access Token
    re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"),  # Bank card numbers (16 digits: Uzcard/Humo/Visa/MasterCard)
    re.compile(r"(?i)\b(?:cvv|cvc)\s*[:=]?\s*\d{3,4}\b"),  # Card CVV
    re.compile(r"(?i)\b(?:recovery\s*code|tiklash\s*kodi)\s*[:=]?\s*[a-z0-9-]{8,}\b"),  # Recovery codes
]


def check_for_secrets(text: str) -> tuple[bool, str]:
    """Check if the provided text contains any prohibited secret or credential.

    Returns (contains_secret, reason).
    """
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            return True, "Xavfsizlik qoidasi: Maxfiy parol, API kalit, bank kartasi yoki tiklash kodlarini saqlash qat'iyan taqiqlangan."
    return False, ""
