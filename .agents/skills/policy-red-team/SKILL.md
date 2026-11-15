---
name: policy-red-team
description: Implements and runs the 10-attack security suite against the Cyber Agent policy engine, tools, and kill switch. Use when finishing stages S2, S4, S6 or after any policy change.
---
# Policy red-team suite
Implement tests in `tests/security/` for MASTER_PLAN §18.3 (10 attacks). Each must assert the attack is BLOCKED and audited.
Add attacks relevant to new tools of the stage (path escape, unlisted app/command, tainted-session send).
Fail the stage if any attack succeeds; never weaken policy to pass. Report counts in the Uzbek report.
