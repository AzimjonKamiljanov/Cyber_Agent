---
name: stage-report-uz
description: Writes the mandatory Uzbek-language stage completion report for Cyber Agent. Use at the end of every stage before asking the owner for approval.
---
# Stage report (Uzbek, Latin script)
Save to `docs/reports/stage-N-report.uz.md` and summarize in chat. Use exactly these headings:
1. **Xulosa** — 3–5 sentences: what the stage achieved.
2. **Nima qilindi** — list of created/changed files and modules.
3. **Tekshiruv natijalari** — real command outputs (trimmed), test counts, lint/type results. Never invent.
4. **Siz bajaradigan tekshiruvlar (USER-TEST-REQUIRED)** — numbered, exact steps incl. commands for Ghostty and phone steps.
5. **Qo'lda bajariladigan tizim qadamlari** — `scripts/manual/*` the owner must run (sudo, Tailscale, keys).
6. **Muammolar va qarorlar** — problems, decision records created.
7. **Rejadan chetlanishlar** — "Yo'q" or an explicit list with reasons.
8. **Keyingi qadam** — ask the owner to reply `APPROVED STAGE N` or list defects.
Tone: short, clear, factual. No marketing language.
