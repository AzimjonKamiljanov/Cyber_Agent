"""Registration of all S2 default safe tools."""

from cyber_agent.policy.permissions import PolicyTier
from cyber_agent.tools.draft_message import handle_draft_message
from cyber_agent.tools.get_local_time import handle_get_local_time
from cyber_agent.tools.get_system_status import handle_get_system_status
from cyber_agent.tools.move_workspace_file import handle_move_workspace_file
from cyber_agent.tools.open_allowed_app import handle_open_allowed_app
from cyber_agent.tools.registry import ToolDefinition, ToolRegistry, get_tool_registry
from cyber_agent.tools.run_test_suite import handle_run_test_suite
from cyber_agent.tools.schemas import (
    CreateTimerArgs,
    DraftMessageArgs,
    GetLocalTimeArgs,
    GetSystemStatusArgs,
    ListTimersArgs,
    MoveWorkspaceFileArgs,
    OpenAllowedAppArgs,
    RunTestSuiteArgs,
    SearchWorkspaceArgs,
    SetVolumeArgs,
    WebSearchReadArgs,
    WriteWorkspaceFileArgs,
)
from cyber_agent.tools.search_workspace import handle_search_workspace
from cyber_agent.tools.set_volume import handle_set_volume
from cyber_agent.tools.timers import handle_create_timer, handle_list_timers
from cyber_agent.tools.web_search_read import handle_web_search_read
from cyber_agent.tools.write_workspace_file import handle_write_workspace_file


def register_default_tools(registry: ToolRegistry | None = None) -> ToolRegistry:
    reg = registry or get_tool_registry()

    # GREEN Tier Tools
    reg.register(
        ToolDefinition(
            name="get_local_time",
            description="Toshkent yoki boshqa vaqt zonasidagi aniq sana va vaqtni ko'rsatadi.",
            tier=PolicyTier.GREEN,
            args_schema=GetLocalTimeArgs,
            handler=handle_get_local_time,
        )
    )

    reg.register(
        ToolDefinition(
            name="get_system_status",
            description="Noutbukning CPU, RAM, Disk, Batareya va GPU holatini o'qiydi.",
            tier=PolicyTier.GREEN,
            args_schema=GetSystemStatusArgs,
            handler=handle_get_system_status,
        )
    )

    reg.register(
        ToolDefinition(
            name="search_workspace",
            description="~/cyber-workspace katalogi ichida fayl nomi yoki matn bo'yicha qidiradi.",
            tier=PolicyTier.GREEN,
            args_schema=SearchWorkspaceArgs,
            handler=handle_search_workspace,
        )
    )

    reg.register(
        ToolDefinition(
            name="open_allowed_app",
            description="Ruxsat etilgan ilovalarni (Firefox, Ghostty, Obsidian va b.) ishga tushiradi.",
            tier=PolicyTier.GREEN,
            args_schema=OpenAllowedAppArgs,
            handler=handle_open_allowed_app,
        )
    )

    reg.register(
        ToolDefinition(
            name="set_volume",
            description="Tizim audio ovoz balandligini 0 dan 100 gacha o'rnatadi.",
            tier=PolicyTier.GREEN,
            args_schema=SetVolumeArgs,
            handler=handle_set_volume,
        )
    )

    reg.register(
        ToolDefinition(
            name="create_timer",
            description="Belgilangan soniyaga yangi taymer yoki eslatma o'rnatadi.",
            tier=PolicyTier.GREEN,
            args_schema=CreateTimerArgs,
            handler=handle_create_timer,
        )
    )

    reg.register(
        ToolDefinition(
            name="list_timers",
            description="Faol taymerlar ro'yxatini ko'rsatadi.",
            tier=PolicyTier.GREEN,
            args_schema=ListTimersArgs,
            handler=handle_list_timers,
        )
    )

    reg.register(
        ToolDefinition(
            name="draft_message",
            description="Xabar qoralamasini tayyorlaydi (yubormaydi).",
            tier=PolicyTier.GREEN,
            args_schema=DraftMessageArgs,
            handler=handle_draft_message,
        )
    )

    reg.register(
        ToolDefinition(
            name="web_search_read",
            description="Ruxsat etilgan veb-sayt (Wikipedia, GitHub) sahifasini o'qiydi.",
            tier=PolicyTier.GREEN,
            args_schema=WebSearchReadArgs,
            handler=handle_web_search_read,
        )
    )

    # YELLOW Tier Tools (Confirmation required)
    reg.register(
        ToolDefinition(
            name="write_workspace_file",
            description="~/cyber-workspace ichida yangi fayl yaratadi.",
            tier=PolicyTier.YELLOW,
            args_schema=WriteWorkspaceFileArgs,
            handler=handle_write_workspace_file,
        )
    )

    reg.register(
        ToolDefinition(
            name="move_workspace_file",
            description="~/cyber-workspace ichidagi faylni boshqa joyga ko'chiradi yoki nomini o'zgartiradi.",
            tier=PolicyTier.YELLOW,
            args_schema=MoveWorkspaceFileArgs,
            handler=handle_move_workspace_file,
        )
    )

    reg.register(
        ToolDefinition(
            name="run_test_suite",
            description="Workspace testlarini tarmoqsiz xavfsiz bubblewrap qumdonida ishga tushiradi.",
            tier=PolicyTier.YELLOW,
            args_schema=RunTestSuiteArgs,
            handler=handle_run_test_suite,
        )
    )

    return reg
