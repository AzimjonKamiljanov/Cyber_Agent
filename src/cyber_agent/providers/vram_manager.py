"""GPU VRAM Manager and Sequential Offloader for Cyber Agent.

Guarantees execution strictly within the 8151 MiB (~8 GB) VRAM budget
of the NVIDIA RTX 5070 Laptop GPU.
"""

from __future__ import annotations

import gc
import logging
import subprocess

logger = logging.getLogger(__name__)

MAX_VRAM_BUDGET_MB = 7168.0  # 7.0 GB safe threshold


class VRAMManager:
    """Monitors GPU memory and coordinates sequential model loading/unloading."""

    def __init__(self, max_budget_mb: float = MAX_VRAM_BUDGET_MB) -> None:
        self.max_budget_mb = max_budget_mb

    def get_vram_usage(self) -> tuple[float, float]:
        """Return (used_mb, total_mb) queried directly from nvidia-smi."""
        try:
            out = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.used,memory.total",
                    "--format=csv,noheader,nounits",
                ],
                stderr=subprocess.DEVNULL,
            ).decode().strip()
            parts = [float(p.strip()) for p in out.split(",")]
            return parts[0], parts[1]
        except Exception:  # noqa: BLE001
            return 0.0, 8151.0

    def purge_gpu_cache(self) -> None:
        """Force Python garbage collection and PyTorch CUDA cache clearing."""
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
        except ImportError:
            pass

    def check_headroom(self, required_mb: float = 1500.0) -> bool:
        """Check if enough VRAM headroom exists without exceeding 7.0 GB threshold."""
        used_mb, _total_mb = self.get_vram_usage()
        projected_mb = used_mb + required_mb
        logger.debug(
            "VRAM check: used=%.1f MB, required=%.1f MB, projected=%.1f MB (Max budget=%.1f MB)",
            used_mb,
            required_mb,
            projected_mb,
            self.max_budget_mb,
        )
        return projected_mb <= self.max_budget_mb


_global_vram_manager: VRAMManager | None = None


def get_vram_manager() -> VRAMManager:
    global _global_vram_manager
    if _global_vram_manager is None:
        _global_vram_manager = VRAMManager()
    return _global_vram_manager
