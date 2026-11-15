"""URL validation logic against config/url_rules.toml."""

import tomllib
from fnmatch import fnmatch
from pathlib import Path
from urllib.parse import urlparse

CONFIG_URL_RULES = Path("config/url_rules.toml")


def is_url_allowed(url: str, allow_file_fixtures: bool = False) -> tuple[bool, str]:
    """Validate a URL against allowed/denied domains and schemes."""
    if allow_file_fixtures and url.startswith("file://"):
        return True, "Local file fixture allowed for testing"

    allowed_domains = ["*.wikipedia.org", "wikipedia.org", "*.github.com", "github.com", "python.org"]
    denied_domains = ["localhost", "127.0.0.1", "*.ts.net", "10.*", "192.168.*", "172.16.*"]
    allowed_schemes = ["http", "https"]

    if CONFIG_URL_RULES.exists():
        try:
            with open(CONFIG_URL_RULES, "rb") as f:
                data = tomllib.load(f)
            rules = data.get("rules", {})
            allowed_schemes = rules.get("allowed_schemes", allowed_schemes)
            allowed_domains = rules.get("allowed_domains", allowed_domains)
            denied_domains = rules.get("denied_domains", denied_domains)
        except Exception:  # noqa: BLE001, S110
            pass

    parsed = urlparse(url)
    if parsed.scheme not in allowed_schemes:
        return False, f"URL sxemasi '{parsed.scheme}' ruxsat etilmagan (faqat {allowed_schemes})"

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return False, "Yaroqsiz URL yoki domen nomi ko'rsatilmagan"

    # Explicit deny check
    for denied in denied_domains:
        if fnmatch(hostname, denied.lower()):
            return False, f"Domen '{hostname}' xavfsizlik qoidasi bilan bloklangan"

    # Explicit allow check
    for allowed in allowed_domains:
        if fnmatch(hostname, allowed.lower()):
            return True, "Allowed"

    return False, f"Domen '{hostname}' ruxsat etilgan domenlar ro'yxatida mavjud emas"
