"""Tool: web_search_read (GREEN tier).

Fetches read-only web content.
Marks session as TAINTED upon successful retrieval per MASTER_PLAN §7.4.
"""

import tomllib
from fnmatch import fnmatch
from pathlib import Path
from urllib.parse import urlparse

import httpx

from cyber_agent.policy.taint import get_taint_tracker
from cyber_agent.tools.schemas import ToolResult, WebSearchReadArgs


def is_url_allowed(url: str) -> tuple[bool, str]:
    rules_file = Path(__file__).resolve().parent.parent.parent.parent / "config" / "url_rules.toml"
    allowed_domains = ["*.wikipedia.org", "wikipedia.org", "*.github.com", "github.com", "python.org"]
    denied_domains = ["localhost", "127.0.0.1", "*.ts.net", "10.*", "192.168.*"]

    if rules_file.exists():
        try:
            data = tomllib.loads(rules_file.read_text(encoding="utf-8"))
            rules = data.get("rules", {})
            allowed_domains = rules.get("allowed_domains", allowed_domains)
            denied_domains = rules.get("denied_domains", denied_domains)
        except (OSError, tomllib.TOMLDecodeError):
            pass

    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False, f"Scheme '{parsed.scheme}' is not allowed"

    hostname = (parsed.hostname or "").lower()

    # Check explicit deny
    for denied in denied_domains:
        if fnmatch(hostname, denied):
            return False, f"Domain '{hostname}' is denied by URL safety rules"

    # Check allow
    for allowed in allowed_domains:
        if fnmatch(hostname, allowed):
            return True, "Allowed"

    return False, f"Domain '{hostname}' is not in the allowed domains list"


async def handle_web_search_read(args: WebSearchReadArgs) -> ToolResult:
    allowed, reason = is_url_allowed(args.url)
    if not allowed:
        return ToolResult(success=False, output="", error=f"URL ruxsat etilmadi: {reason}")

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(args.url)
            if resp.status_code != 200:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Veb-sahifani yuklab bo'lmadi (HTTP {resp.status_code})",
                )

            # Strip HTML tags or take first 3000 chars of text
            text = resp.text[:3000]

            # Invariant: External web content TAINTs the session
            taint_tracker = get_taint_tracker()
            taint_tracker.mark_tainted(args.url)

            return ToolResult(
                success=True,
                output=f"Veb-sahifa mazmuni ({args.url}) [SESSIYA ZARARLANDI]:\n{text}",
            )
    except (httpx.HTTPError, OSError) as e:
        return ToolResult(success=False, output="", error=f"So'rov xatosi: {e}")
