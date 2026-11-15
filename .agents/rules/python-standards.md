---
trigger: glob
globs: "*.py"
description: "Python code standards for Cyber Agent."
---
# Python standards
- Python 3.12, full type hints, `ruff` and `mypy` must pass.
- Async I/O for network/audio; no blocking calls in the event loop (use `asyncio.to_thread` when unavoidable).
- Pydantic models for external input; never trust raw dicts from network, model output or tools.
- Never log secrets, raw audio or sensitive transcripts; use the redaction helper.
- Errors are structured (`code`, `message`, `retryable`); no bare `except`.
