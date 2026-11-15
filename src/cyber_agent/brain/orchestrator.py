"""Brain Orchestrator: bridges Gemini Live function calls to Policy Engine, Tool Registry, and Task Queue."""

import logging
from dataclasses import dataclass
from typing import Any

from google.genai import types

from cyber_agent.audit.logger import get_audit_logger
from cyber_agent.brain.task_queue import TaskQueue, get_task_queue
from cyber_agent.killswitch.service import get_killswitch_service
from cyber_agent.policy.confirmations import ConfirmationStore, get_confirmation_store
from cyber_agent.policy.engine import PolicyEngine, get_policy_engine
from cyber_agent.policy.permissions import PolicyVerdict
from cyber_agent.policy.taint import SessionTaintTracker, get_taint_tracker
from cyber_agent.tools.registry import ToolRegistry, get_tool_registry

logger = logging.getLogger(__name__)

LONG_RUNNING_TOOLS = {"run_test_suite"}


@dataclass
class OrchestratorResponse:
    status: str  # "success", "error", "denied", "confirm_required", "enqueued"
    spoken_message: str
    data: dict[str, Any]
    confirmation_card: dict[str, Any] | None = None


class Orchestrator:
    def __init__(
        self,
        tool_registry: ToolRegistry | None = None,
        policy_engine: PolicyEngine | None = None,
        confirmation_store: ConfirmationStore | None = None,
        taint_tracker: SessionTaintTracker | None = None,
        task_queue: TaskQueue | None = None,
    ) -> None:
        self.tool_registry = tool_registry or get_tool_registry()
        self.policy_engine = policy_engine or get_policy_engine()
        self.confirmation_store = confirmation_store or get_confirmation_store()
        self.taint_tracker = taint_tracker or get_taint_tracker()
        self.task_queue = task_queue or get_task_queue()
        self.audit_logger = get_audit_logger()
        self._notification_callback: Any = None

    def set_notification_callback(self, cb: Any) -> None:
        """Callback to push messages or spoken alerts to user (e.g. via WebSocket/PWA)."""
        self._notification_callback = cb

    def build_gemini_declarations(self) -> list[types.Tool]:
        """Convert registered tools into Gemini types.FunctionDeclaration with NON_BLOCKING behavior."""
        declarations = []
        for t in self.tool_registry.list_tools():
            declarations.append(
                types.FunctionDeclaration(
                    name=t.name,
                    description=t.description,
                    parameters_json_schema=t.args_schema.model_json_schema(),
                    behavior=types.Behavior.NON_BLOCKING,
                )
            )
        return [types.Tool(function_declarations=declarations)]

    async def handle_tool_call(
        self,
        name: str,
        args: dict[str, Any],
        call_id: str = "",
        action_id: str | None = None,
        confirmation_token: str | None = None,
    ) -> OrchestratorResponse:
        """Evaluate policy, route to tool execution or confirmation card, and log audit."""
        # 0. Check Kill Switch state
        killswitch = get_killswitch_service()
        if killswitch.is_stopped:
            spoken_stopped = "Cyber Agent to'xtatilgan holatda (STOP). Hech qanday amal bajarilmaydi."
            self.audit_logger.log_event("ORCHESTRATOR_BLOCKED_BY_STOP", {"tool_name": name})
            return OrchestratorResponse(
                status="denied",
                spoken_message=spoken_stopped,
                data={"error": "Agent is in STOP state", "verdict": "DENY"},
            )

        is_tainted = self.taint_tracker.is_tainted()

        # 1. Policy check
        decision = self.policy_engine.evaluate(
            tool_name=name,
            args=args,
            action_id=action_id,
            confirmation_token=confirmation_token,
        )

        # 2. Case: DENY
        if decision.verdict == PolicyVerdict.DENY:
            spoken_refusal = (
                f"Xavfsizlik qoidalariga binoan '{name}' amali rad etildi: {decision.reason}."
            )
            self.audit_logger.log_event(
                "ORCHESTRATOR_TOOL_DENIED",
                {
                    "call_id": call_id,
                    "tool_name": name,
                    "args": args,
                    "reason": decision.reason,
                    "is_tainted": is_tainted,
                },
            )
            return OrchestratorResponse(
                status="denied",
                spoken_message=spoken_refusal,
                data={"error": decision.reason, "verdict": "DENY"},
            )

        # 3. Case: CONFIRM (YELLOW tier requiring mobile button press)
        if decision.verdict == PolicyVerdict.CONFIRM:
            act_id = decision.action_id or ""
            tok = decision.confirmation_token or ""
            spoken_prompt = (
                f"'{name}' amali uchun telefon ekranida tasdiqlash kartochkasi paydo bo'ldi. "
                "Iltimos, ekrandagi tugmani bosib tasdiqlang."
            )
            target = str(
                args.get("filename")
                or args.get("destination")
                or args.get("app_name")
                or args.get("url")
                or "Tizim"
            )
            card = {
                "action_id": act_id,
                "token": tok,
                "action": name,
                "target": target,
                "args": args,
                "reversibility": "Qaytarib bo'lmaydi" if "file" in name else "Qaytariladigan",
                "is_tainted": is_tainted,
                "taint_warning": "DIQQAT: Sessiya tashqi veb-manba tufayli zararlangan!" if is_tainted else None,
                "expires_in_seconds": 60,
            }
            self.audit_logger.log_event(
                "ORCHESTRATOR_CONFIRM_REQUESTED",
                {"call_id": call_id, "action_id": act_id, "tool_name": name, "args": args},
            )
            return OrchestratorResponse(
                status="confirm_required",
                spoken_message=spoken_prompt,
                data={"action_id": act_id, "status": "PENDING_CONFIRMATION"},
                confirmation_card=card,
            )

        # 4. Case: ALLOW
        if name in LONG_RUNNING_TOOLS:
            spoken_enqueue = f"'{name}' vazifasi fonda ishga tushirildi. Tugagach sizga xabar beraman."

            async def _execute_long_job() -> Any:
                res = await self.tool_registry.execute(name, args, skip_policy_check=True)
                if self._notification_callback:
                    notify_msg = (
                        f"Fonda bajarilgan '{name}' vazifasi yakunlandi:\n{res.output or res.error}"
                    )
                    await self._notification_callback(notify_msg)
                return res

            task_id = await self.task_queue.enqueue_task(
                coro_fn=_execute_long_job,
                description=f"Long tool: {name}",
            )
            self.audit_logger.log_event(
                "ORCHESTRATOR_TOOL_ENQUEUED",
                {"call_id": call_id, "task_id": task_id, "tool_name": name},
            )
            return OrchestratorResponse(
                status="enqueued",
                spoken_message=spoken_enqueue,
                data={"task_id": task_id, "status": "ENQUEUED"},
            )

        # Immediate synchronous tool execution
        tool_res = await self.tool_registry.execute(name, args, skip_policy_check=True)
        if tool_res.success:
            spoken_done = tool_res.output[:500] if tool_res.output else "Amal bajarildi."
            return OrchestratorResponse(
                status="success",
                spoken_message=spoken_done,
                data={"output": tool_res.output, "execution_time_ms": tool_res.execution_time_ms},
            )
        else:
            spoken_err = f"Amalni bajarishda xatolik yuz berdi: {tool_res.error}"
            return OrchestratorResponse(
                status="error",
                spoken_message=spoken_err,
                data={"error": tool_res.error},
            )


_default_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    global _default_orchestrator
    if _default_orchestrator is None:
        _default_orchestrator = Orchestrator()
    return _default_orchestrator
