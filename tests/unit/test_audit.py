"""Unit tests for audit logger and secret redaction."""

from pathlib import Path

from cyber_agent.audit.logger import AuditLogger, verify_chain
from cyber_agent.audit.redaction import redact_data, redact_text


def test_redaction_rules() -> None:
    # Test API key pattern
    fake_key = "AIzaSyAbcdef1234567890abcdef1234567890"
    assert redact_text(f"API key is {fake_key}") == "API key is [REDACTED_API_KEY]"

    # Test Bearer token
    bearer = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz"
    assert "[REDACTED_TOKEN]" in redact_text(f"Authorization: {bearer}")

    # Test sensitive dict fields and bytes
    data = {
        "gemini_api_key": "secret-1234",
        "cyber_pairing_token": "token-abcd",
        "payload": b"\x01\x02\x03\x04",
        "nested": {"password": "super-secret-password", "safe": "public_data"},
    }
    cleaned = redact_data(data)
    assert cleaned["gemini_api_key"] == "[REDACTED]"
    assert cleaned["cyber_pairing_token"] == "[REDACTED]"
    assert cleaned["payload"] == "<bytes: 4 bytes>"
    assert cleaned["nested"]["password"] == "[REDACTED]"
    assert cleaned["nested"]["safe"] == "public_data"


def test_hash_chain_integrity(tmp_path: Path) -> None:
    log_file = tmp_path / "audit_test.jsonl"
    logger = AuditLogger(log_path=log_file)

    logger.log_event("TEST_EVENT_1", {"message": "hello"})
    logger.log_event("TEST_EVENT_2", {"action": "do_work"})
    logger.log_event("TEST_EVENT_3", {"api_key": "AIzaSyAbcdef1234567890abcdef1234567890"})

    # Verify chain passes
    valid, msg = verify_chain(log_file)
    assert valid is True
    assert "Verified 3 entries" in msg

    # Tamper with file
    content = log_file.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    # Alter line 2 content
    tampered_lines = [lines[0], lines[1].replace("do_work", "tampered_work"), lines[2]]
    log_file.write_text("\n".join(tampered_lines) + "\n", encoding="utf-8")

    # Verify tampering is caught
    valid_tampered, tamper_msg = verify_chain(log_file)
    assert valid_tampered is False
    assert "Tampered hash" in tamper_msg
