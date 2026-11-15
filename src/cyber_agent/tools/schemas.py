"""Strict Pydantic schemas for Cyber Agent tools.

Enforces extra='forbid' to reject unexpected or injection parameters.
"""

from pydantic import BaseModel, ConfigDict, Field


class BaseToolArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MutatingToolArgs(BaseToolArgs):
    request_id: str | None = Field(default=None, description="Unique client request ID")
    idempotency_key: str | None = Field(default=None, description="Idempotency key for side-effect deduplication")


# --- Tool Specific Argument Schemas ---

class GetLocalTimeArgs(BaseToolArgs):
    timezone: str = Field(default="Asia/Tashkent", description="Timezone name")


class GetSystemStatusArgs(BaseToolArgs):
    pass


class SearchWorkspaceArgs(BaseToolArgs):
    query: str = Field(..., description="Filename or keyword to search within workspace")
    max_results: int = Field(default=10, ge=1, le=50, description="Maximum matches to return")


class OpenAllowedAppArgs(BaseToolArgs):
    app_name: str = Field(..., description="Name of the application defined in apps_allowlist.toml")


class SetVolumeArgs(BaseToolArgs):
    level: int = Field(..., ge=0, le=100, description="Volume level between 0 and 100")


class CreateTimerArgs(MutatingToolArgs):
    seconds: int = Field(..., ge=1, le=86400, description="Timer duration in seconds")
    label: str = Field(default="", max_length=100, description="Optional label for the timer")


class ListTimersArgs(BaseToolArgs):
    pass


class DraftMessageArgs(BaseToolArgs):
    recipient: str = Field(..., max_length=100, description="Recipient name or handle")
    body: str = Field(..., max_length=2000, description="Draft message content")


class WebSearchReadArgs(BaseToolArgs):
    url: str = Field(..., description="Target HTTP/HTTPS URL allowed by url_rules.toml")


class WriteWorkspaceFileArgs(MutatingToolArgs):
    filename: str = Field(..., description="Relative file path inside ~/cyber-workspace")
    content: str = Field(..., max_length=500000, description="Content to write into the new file")


class MoveWorkspaceFileArgs(MutatingToolArgs):
    source: str = Field(..., description="Relative source path inside ~/cyber-workspace")
    destination: str = Field(..., description="Relative destination path inside ~/cyber-workspace")


class RunTestSuiteArgs(MutatingToolArgs):
    test_path: str = Field(default="", description="Specific test file or directory inside workspace")


class ToolResult(BaseModel):
    success: bool
    output: str
    error: str | None = None
    execution_time_ms: float = 0.0
