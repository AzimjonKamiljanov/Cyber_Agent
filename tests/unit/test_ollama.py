"""Unit tests for Ollama local provider and tool schema generation."""

from typing import Any

import httpx
import pytest

from cyber_agent.providers.ollama_local import OllamaLocalProvider
from cyber_agent.tools.default_tools import register_default_tools
from cyber_agent.tools.registry import ToolRegistry


@pytest.fixture
def registry() -> ToolRegistry:
    reg = ToolRegistry()
    register_default_tools(reg)
    return reg


def test_ollama_tool_schema_export(registry: ToolRegistry) -> None:
    provider = OllamaLocalProvider(tool_registry=registry)
    schemas = provider.get_tool_schemas()
    assert len(schemas) >= 10
    names = [s["function"]["name"] for s in schemas]
    assert "get_local_time" in names
    assert "get_system_status" in names
    assert "set_volume" in names


@pytest.mark.asyncio
async def test_ollama_chat_success(registry: ToolRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaLocalProvider(tool_registry=registry)

    async def mock_post(*args: Any, **kwargs: Any) -> httpx.Response:
        content = {
            "message": {
                "role": "assistant",
                "content": "Hozir soat 14:30.",
                "tool_calls": [],
            }
        }
        return httpx.Response(200, json=content, request=httpx.Request("POST", "http://test"))

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    resp = await provider.chat([{"role": "user", "content": "Soat necha bo'ldi?"}])
    assert resp.content == "Hozir soat 14:30."
    assert len(resp.tool_calls) == 0


@pytest.mark.asyncio
async def test_ollama_tool_call_parsing(registry: ToolRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaLocalProvider(tool_registry=registry)

    async def mock_post(*args: Any, **kwargs: Any) -> httpx.Response:
        content = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_local_time",
                            "arguments": {"timezone": "Asia/Tashkent"},
                        }
                    }
                ],
            }
        }
        return httpx.Response(200, json=content, request=httpx.Request("POST", "http://test"))

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    resp = await provider.chat([{"role": "user", "content": "Soatni ayt"}])
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "get_local_time"
    assert resp.tool_calls[0].arguments == {"timezone": "Asia/Tashkent"}


@pytest.mark.asyncio
async def test_ollama_unknown_tool_rejection(registry: ToolRegistry, monkeypatch: pytest.MonkeyPatch) -> None:
    provider = OllamaLocalProvider(tool_registry=registry)

    async def mock_post(*args: Any, **kwargs: Any) -> httpx.Response:
        content = {
            "message": {
                "role": "assistant",
                "content": "Buyruq berildi",
                "tool_calls": [
                    {
                        "function": {
                            "name": "forbidden_unknown_tool",
                            "arguments": {},
                        }
                    }
                ],
            }
        }
        return httpx.Response(200, json=content, request=httpx.Request("POST", "http://test"))

    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)
    resp = await provider.chat([{"role": "user", "content": "Noma'lum buyruq"}])
    # The unknown tool call must be filtered out
    assert len(resp.tool_calls) == 0
    assert resp.content == "Buyruq berildi"
