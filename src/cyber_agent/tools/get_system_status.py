"""Tool: get_system_status (GREEN tier)."""

import asyncio
import subprocess

import psutil

from cyber_agent.tools.schemas import GetSystemStatusArgs, ToolResult


async def handle_get_system_status(args: GetSystemStatusArgs) -> ToolResult:
    # CPU & Memory
    cpu_percent = psutil.cpu_percent(interval=None)
    cpu_cores = psutil.cpu_count(logical=True)
    mem = psutil.virtual_memory()
    mem_used_gb = mem.used / (1024**3)
    mem_total_gb = mem.total / (1024**3)

    # Disk
    disk = psutil.disk_usage("/")
    disk_free_gb = disk.free / (1024**3)

    # Battery
    battery = psutil.sensors_battery()
    bat_str = f"{battery.percent:.0f}%" if battery else "Mavjud emas (tarmoqda)"

    # GPU via nvidia-smi
    gpu_str = "Aniqlanmadi"
    try:
        proc = await asyncio.create_subprocess_exec(
            "nvidia-smi",
            "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
            "--format=csv,noheader,nounits",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2.0)
        if proc.returncode == 0 and stdout:
            parts = stdout.decode("utf-8").strip().split(",")
            if len(parts) >= 4:
                gpu_util, mem_used, mem_tot, temp = [p.strip() for p in parts[:4]]
                gpu_str = f"Util: {gpu_util}%, VRAM: {mem_used}/{mem_tot} MiB, Harorat: {temp}°C"
    except (OSError, subprocess.SubprocessError, TimeoutError):
        gpu_str = "NVIDIA drayveri javob bermadi"

    output = (
        f"Tizim holati:\n"
        f"• CPU yuklanishi: {cpu_percent}% ({cpu_cores} vCPU)\n"
        f"• RAM: {mem_used_gb:.1f} / {mem_total_gb:.1f} GB ({mem.percent}%)\n"
        f"• Disk bo'sh joy (/): {disk_free_gb:.1f} GB\n"
        f"• Batareya: {bat_str}\n"
        f"• GPU: {gpu_str}"
    )

    return ToolResult(success=True, output=output)
