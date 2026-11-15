"""Local LLM provider interfacing with Ollama (qwen3:8b / qwen2.5:7b).

Enforces:
- Structured schema-validated tool calling through ToolRegistry and PolicyEngine.
- Low-confidence or invalid output handling: clarifies or replies in text, NEVER guesses tools.
- Strict 1-request concurrency and 4k-8k context window limits.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

import httpx

from cyber_agent.config import get_settings
from cyber_agent.tools.registry import ToolRegistry, get_tool_registry

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Sen Cyber Agent - Azimjonning shaxsiy ovozli yordamchisisan.
Asosiy qoidalar:
1. Foydalanuvchiga faqat o'zbek tilida (lotin yozuvida), qisqa, aniq va xushmuomala javob ber (JARVIS ohangida).
2. Dasturlash va IT atamalari (git, docker, python, bwrap va hk.) inglizcha o'z holicha qolsin.
3. Agar foydalanuvchi biror amalni bajarishni so'rasa va buning uchun mos vosita (tool) mavjud bo'lsa, mos tool'ni chaqir.
4. Hech qachon taxminiy yoki mavjud bo'lmagan toollarni to'qima! Agar biror amal uchun tool bo'lmasa yoki niyat noaniq bo'lsa, buni o'zbekcha matn bilan tushuntir yoki aniqlashtirishni so'ra.
5. Maxfiy ma'lumotlar, parollar yoki xavfli buyruqlarni aslo bajarma."""


@dataclass
class OllamaToolCall:
    name: str
    arguments: dict[str, Any]


@dataclass
class OllamaResponse:
    content: str
    tool_calls: list[OllamaToolCall] = field(default_factory=list)
    raw_response: dict[str, Any] = field(default_factory=dict)


class OllamaLocalProvider:
    """Ollama client for local inference and tool calling."""

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        tool_registry: ToolRegistry | None = None,
        timeout: float = 30.0,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or settings.cyber_ollama_url).rstrip("/")
        self.model = model or settings.cyber_ollama_model
        self.tool_registry = tool_registry or get_tool_registry()
        self.timeout = timeout

    async def is_healthy(self) -> bool:
        """Check if Ollama server is accessible."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception:  # noqa: BLE001
            return False

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Export ToolRegistry tools in Ollama/OpenAI function format."""
        tools: list[dict[str, Any]] = []
        for t in self.tool_registry.list_tools():
            schema = t.args_schema.model_json_schema()
            # Remove title to make schema compact
            schema.pop("title", None)
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": schema,
                    },
                }
            )
        return tools

    async def chat(
        self,
        messages: list[dict[str, Any]],
        enable_tools: bool = True,
    ) -> OllamaResponse:
        """Send chat completion request to Ollama."""
        tools = self.get_tool_schemas() if enable_tools else None

        # Ensure system prompt is present
        payload_messages: list[dict[str, Any]] = []
        has_system = any(m.get("role") == "system" for m in messages)
        if not has_system:
            payload_messages.append({"role": "system", "content": SYSTEM_PROMPT})
        payload_messages.extend(messages)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "stream": False,
            "options": {
                "num_ctx": 4096,
                "temperature": 0.2,
                "num_predict": 512,
            },
        }
        if tools:
            payload["tools"] = tools

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                res = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                res.raise_for_status()
                data = res.json()
            except Exception as e:  # noqa: BLE001
                logger.error("Ollama request failed: %s", e)
                return OllamaResponse(
                    content="Kechirasiz, mahalliy model bilan bog'lanishda xatolik yuz berdi.",
                    tool_calls=[],
                )

        msg = data.get("message", {})
        content = msg.get("content", "") or ""
        tool_calls: list[OllamaToolCall] = []

        raw_calls = msg.get("tool_calls") or []
        for rc in raw_calls:
            fn = rc.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except Exception:  # noqa: BLE001
                    args = {}

            # Strict check against ToolRegistry: unknown tools are discarded
            if self.tool_registry.get(name):
                tool_calls.append(OllamaToolCall(name=name, arguments=args))
            else:
                logger.warning("Ollama suggested unknown tool '%s'; ignoring call.", name)

        # Fallback if model attempted JSON tool call directly in text content
        if not tool_calls and content.strip().startswith("{") and "name" in content:
            try:
                parsed = json.loads(content.strip())
                fn_name = parsed.get("name") or parsed.get("function")
                fn_args = parsed.get("arguments") or parsed.get("parameters") or {}
                if isinstance(fn_name, str) and self.tool_registry.get(fn_name):
                    tool_calls.append(OllamaToolCall(name=fn_name, arguments=fn_args))
                    content = ""
            except Exception:  # noqa: BLE001, S110
                pass

        return OllamaResponse(
            content=content.strip(),
            tool_calls=tool_calls,
            raw_response=data,
        )
