from __future__ import annotations
import os
import subprocess
from dataclasses import dataclass


@dataclass
class ResourceInfo:
    cpu_count: int
    gpu_available: bool
    gpu_type: str          # "cuda" | "mps" | "none"
    gpu_device_count: int


def detect_cpu_count() -> int:
    """Return number of logical CPUs available."""
    return os.cpu_count() or 1


def detect_gpu() -> dict:
    """
    Detect GPU availability.
    Checks NVIDIA CUDA first, then Apple MPS, then falls back to none.
    """
    # Check NVIDIA CUDA via nvidia-smi
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            devices = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
            if devices:
                return {"available": True, "type": "cuda", "device_count": len(devices)}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Check Apple Silicon MPS via torch if available
    try:
        import torch  # type: ignore
        if torch.backends.mps.is_available():
            return {"available": True, "type": "mps", "device_count": 1}
    except ImportError:
        pass

    # Fallback: detect Apple Silicon via system_profiler
    try:
        import platform
        if platform.system() == "Darwin" and platform.processor() == "arm":
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=5
            )
            if "Apple M" in result.stdout:
                return {"available": True, "type": "mps", "device_count": 1}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return {"available": False, "type": "none", "device_count": 0}


def detect_resources() -> ResourceInfo:
    """Detect all available compute resources."""
    cpu_count = detect_cpu_count()
    gpu_info = detect_gpu()
    return ResourceInfo(
        cpu_count=cpu_count,
        gpu_available=gpu_info["available"],
        gpu_type=gpu_info["type"],
        gpu_device_count=gpu_info["device_count"],
    )
