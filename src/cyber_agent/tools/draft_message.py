"""Tool: draft_message (GREEN tier).

Drafts a message without sending it anywhere.
"""

from cyber_agent.tools.schemas import DraftMessageArgs, ToolResult


async def handle_draft_message(args: DraftMessageArgs) -> ToolResult:
    output = (
        f"Xabar qoralamasi tayyorlandi (Yuborilmadi):\n"
        f"• Qabul qiluvchi: {args.recipient}\n"
        f"• Matn: \"{args.body}\"\n"
        f"Eslatma: Xabar faqat qoralama holatida saqlandi. Haqiqiy yuborish foydalanuvchi tasdig'isiz amalga oshirilmaydi."
    )
    return ToolResult(success=True, output=output)
