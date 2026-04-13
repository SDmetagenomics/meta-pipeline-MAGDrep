from __future__ import annotations
import os
import subprocess
from dataclasses import dataclass


@dataclass
class ResourceInfo:
    cpu_count: int
    mem_gb: float
    gpu_available: bool
    gpu_type: str          # "cuda" | "mps" | "none"
    gpu_device_count: int


def detect_cpu_count() -> int:
    """Return number of logical CPUs available."""
    return os.cpu_count() or 1


def detect_memory_gb() -> float:
    """Return total system memory in GB. Returns 0 if detection fails."""
    # Linux and macOS: /proc/meminfo or sysctl
    try:
        import platform
        if platform.system() == "Linux":
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return kb / (1024 ** 2)
        elif platform.system() == "Darwin":
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True, timeout=5,
            )
            if result.returncode == 0:
                return int(result.stdout.strip()) / (1024 ** 3)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return 0.0


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
    mem_gb = detect_memory_gb()
    gpu_info = detect_gpu()
    return ResourceInfo(
        cpu_count=cpu_count,
        mem_gb=mem_gb,
        gpu_available=gpu_info["available"],
        gpu_type=gpu_info["type"],
        gpu_device_count=gpu_info["device_count"],
    )


# Memory budget for one GTDB-Tk pplacer process on r226 bac120 (GB).
# Peak RAM usage during phylogenetic placement — scales with tree size.
GTDBTK_PPLACER_MEM_GB = 60.0

# Approximate memory reserved for CheckM2 when running concurrently with
# GTDB-Tk. CheckM2's diamond search plus neural-net prediction is ~5-8 GB.
CHECKM2_CONCURRENT_MEM_GB = 8.0

# OS / buffer / other overhead to reserve when computing memory budgets.
SYSTEM_OVERHEAD_GB = 8.0


def compute_gtdbtk_pplacer_cpus(
    mem_gb: float, max_cpus: int, reserve_gb: float = 0.0,
) -> int:
    """Return a safe number of pplacer CPUs based on available memory.

    pplacer is memory-bounded: each parallel instance needs ~60 GB for
    the r226 bac120 tree. Exceeding memory causes swapping or OOM kills.

    *reserve_gb* is memory set aside for other work (e.g. a concurrent
    CheckM2 batch) plus system overhead.
    """
    if mem_gb <= 0:
        return 1
    available = max(0.0, mem_gb - reserve_gb)
    by_mem = max(1, int(available // GTDBTK_PPLACER_MEM_GB))
    return min(by_mem, max_cpus)


def allocate_threads(
    cpu_count: int, concurrent_steps: int,
) -> dict[str, int]:
    """Split CPU budget across concurrent pipeline steps.

    When CheckM2 and GTDB-Tk run back-to-back (one active step), each job
    can claim all CPUs. When they run concurrently (two active steps),
    split roughly in half so Snakemake schedules them in parallel.

    Returns {"checkm2": N, "gtdbtk": N}.
    """
    if concurrent_steps <= 1:
        return {"checkm2": cpu_count, "gtdbtk": cpu_count}
    # Leave 1 core for Snakemake orchestration / genome_stats on small systems
    usable = max(2, cpu_count)
    half = max(1, usable // 2)
    # Prefer slightly more CPU for GTDB-Tk (classify_wf parallelizes well)
    # and slightly less for CheckM2 (saturates at ~8 threads anyway)
    return {"checkm2": half, "gtdbtk": usable - half}
