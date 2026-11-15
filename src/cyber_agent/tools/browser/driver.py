"""Isolated Playwright Browser Driver for Cyber Agent Stage S4.

Operates in an isolated user profile under `data/browser_profile/` (never ~/.config).
Enforces domain allow/deny rules from config/url_rules.toml.
"""

from __future__ import annotations

import logging
from pathlib import Path

from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from cyber_agent.tools.browser.url_validator import is_url_allowed

logger = logging.getLogger(__name__)

DEFAULT_PROFILE_DIR = Path("data/browser_profile")


class BrowserDriver:
    """Manages an isolated Playwright browser context."""

    def __init__(self, profile_dir: Path | None = None) -> None:
        self.profile_dir = profile_dir or DEFAULT_PROFILE_DIR
        self._playwright: Playwright | None = None
        self._context: BrowserContext | None = None
        self._current_page: Page | None = None
        self._current_url: str = ""

    def _ensure_profile_dir(self) -> Path:
        resolved = self.profile_dir.resolve()
        # Security invariant: NEVER point to user's real ~/.config directory
        user_home = Path.home().resolve()
        sensitive_roots = [
            user_home / ".config",
            user_home / ".mozilla",
            user_home / ".cache" / "google-chrome",
        ]
        for s in sensitive_roots:
            if s.exists() and (resolved == s or s in resolved.parents):
                raise PermissionError(f"Security violation: Browser profile cannot be inside {s}")

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        return resolved

    async def _ensure_context(self) -> BrowserContext:
        if self._context is not None:
            return self._context

        self._ensure_profile_dir()
        if self._playwright is None:
            self._playwright = await async_playwright().start()

        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
            viewport={"width": 1280, "height": 800},
        )
        pages = self._context.pages
        self._current_page = pages[0] if pages else await self._context.new_page()
        return self._context

    async def open_url(self, url: str, allow_file_fixtures: bool = False) -> tuple[bool, str]:
        """Validate and open the target URL."""
        allowed, reason = is_url_allowed(url, allow_file_fixtures=allow_file_fixtures)
        if not allowed:
            return False, f"URL ochish rad etildi: {reason}"

        try:
            await self._ensure_context()
            if self._current_page is None:
                return False, "Brauzer sahifasi mavjud emas"

            response = await self._current_page.goto(url, wait_until="domcontentloaded", timeout=15000)
            self._current_url = url
            title = await self._current_page.title()
            status = response.status if response else 200
            return True, f"'{url}' ochildi (HTTP {status}, Sarlavha: '{title}')"
        except Exception as e:  # noqa: BLE001
            logger.error("Failed to open URL %s: %s", url, e)
            return False, f"Sahifani ochishda xatolik yuz berdi: {e}"

    async def read_content(self, max_chars: int = 4000) -> tuple[bool, str, str]:
        """Extract inner text from current page.

        Returns (success, content, current_url).
        """
        if self._current_page is None or not self._current_url:
            return False, "Hech qanday veb-sahifa ochilmagan. Avval browser_open chaqiring.", ""

        try:
            # Extract main text
            text = await self._current_page.inner_text("body")
            truncated = text[:max_chars]
            return True, truncated, self._current_url
        except Exception as e:  # noqa: BLE001
            return False, f"Sahifa matnini o'qishda xatolik: {e}", self._current_url

    async def submit_form(self, form_selector: str, fields: dict[str, str]) -> tuple[bool, str]:
        """Fill form inputs and submit."""
        if self._current_page is None:
            return False, "Hech qanday veb-sahifa ochilmagan."

        try:
            form = self._current_page.locator(form_selector)
            if await form.count() == 0:
                return False, f"'{form_selector}' selektori bo'yicha forma topilmadi."

            # Fill each field
            for field_name, value in fields.items():
                input_locator = form.locator(
                    f"input[name='{field_name}'], textarea[name='{field_name}'], #{field_name}, input[id='{field_name}']"
                ).first
                if await input_locator.count() > 0:
                    await input_locator.fill(value)
                else:
                    logger.warning("Field '%s' not found in form", field_name)

            # Attempt submission: either form.evaluate submit or click submit button
            submit_btn = form.locator("button[type='submit'], input[type='submit']").first
            if await submit_btn.count() > 0:
                await submit_btn.click()
            else:
                await form.evaluate("form => form.submit()")

            # Wait briefly for navigation or DOM update
            await self._current_page.wait_for_timeout(1000)
            return True, f"'{form_selector}' formasi muvaffaqiyatli to'ldirildi va yuborildi."
        except Exception as e:  # noqa: BLE001
            return False, f"Formani yuborishda xatolik: {e}"

    async def close(self) -> None:
        """Close browser context and playwright instance."""
        try:
            if self._context is not None:
                await self._context.close()
                self._context = None
                self._current_page = None
            if self._playwright is not None:
                await self._playwright.stop()
                self._playwright = None
        except Exception as e:  # noqa: BLE001
            logger.warning("Error closing browser: %s", e)


_global_browser_driver: BrowserDriver | None = None


def get_browser_driver() -> BrowserDriver:
    global _global_browser_driver
    if _global_browser_driver is None:
        _global_browser_driver = BrowserDriver()
    return _global_browser_driver
