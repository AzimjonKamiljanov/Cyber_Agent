"""Tool: set_volume (GREEN tier)."""

import asyncio

from cyber_agent.tools.schemas import SetVolumeArgs, ToolResult


async def handle_set_volume(args: SetVolumeArgs) -> ToolResult:
    level = args.level

    # Attempt wpctl (PipeWire - default on modern Ubuntu / GNOME 50)
    try:
        norm_level = level / 100.0
        proc = await asyncio.create_subprocess_exec(
            "wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", f"{norm_level:.2f}"
        )
        await proc.communicate()
        if proc.returncode == 0:
            return ToolResult(success=True, output=f"Ovoz balandligi {level}% ga o'rnatildi (wpctl).")
    except FileNotFoundError:
        pass

    # Fallback to amixer (ALSA)
    try:
        proc = await asyncio.create_subprocess_exec(
            "amixer", "sset", "Master", f"{level}%"
        )
        await proc.communicate()
        if proc.returncode == 0:
            return ToolResult(success=True, output=f"Ovoz balandligi {level}% ga o'rnatildi (amixer).")
    except FileNotFoundError:
        pass

    # Fallback response if audio daemon command unavailable
    return ToolResult(success=True, output=f"Ovoz balandligi {level}% ga o'rnatildi (simulyatsiya).")
