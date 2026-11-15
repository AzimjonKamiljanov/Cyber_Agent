"""Configuration management for Cyber Agent using pydantic-settings.

Enforces zero leakage of secrets in string representations or logs.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    cyber_live_model: str = Field(default="gemini-3.8-live", alias="CYBER_LIVE_MODEL")
    cyber_host: str = Field(default="127.0.0.1", alias="CYBER_HOST")
    cyber_port: int = Field(default=8000, alias="CYBER_PORT")
    cyber_pairing_token: str = Field(default="", alias="CYBER_PAIRING_TOKEN")
    cyber_privacy_mode: bool = Field(default=False, alias="CYBER_PRIVACY_MODE")
    cyber_data_dir: Path = Field(default=Path("./data"), alias="CYBER_DATA_DIR")
    cyber_address_as: str = Field(default="Azimjon", alias="CYBER_ADDRESS_AS")
    cyber_workspace_dir: Path = Field(
        default=Path("~/cyber-workspace"), alias="CYBER_WORKSPACE_DIR"
    )

    def __repr__(self) -> str:
        masked_api = "***" if self.gemini_api_key else ""
        masked_token = "***" if self.cyber_pairing_token else ""
        return (
            f"Settings(cyber_live_model={self.cyber_live_model!r}, "
            f"cyber_host={self.cyber_host!r}, "
            f"cyber_port={self.cyber_port!r}, "
            f"gemini_api_key={masked_api!r}, "
            f"cyber_pairing_token={masked_token!r}, "
            f"cyber_privacy_mode={self.cyber_privacy_mode!r}, "
            f"cyber_address_as={self.cyber_address_as!r})"
        )

    def __str__(self) -> str:
        return self.__repr__()

    def safe_dict(self) -> dict[str, Any]:
        """Return configuration dictionary with sensitive credentials redacted."""
        d = self.model_dump()
        if d.get("gemini_api_key"):
            d["gemini_api_key"] = "***"
        if d.get("cyber_pairing_token"):
            d["cyber_pairing_token"] = "***"
        return d


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
