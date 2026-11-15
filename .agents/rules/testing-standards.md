---
trigger: glob
globs: "tests/**/*.py, test_*.py"
description: "Testing standards."
---
# Testing standards
- Every module gets unit tests; security-relevant code gets tests in `tests/security/`.
- Tests must be deterministic; mock the network and the Gemini API; real-API checks live in `tests/integration/` behind an env flag.
- Paste real command output into the stage report; never write "tests pass" without running them.
