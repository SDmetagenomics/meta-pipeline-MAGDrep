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


def detect_slurm_node_resources(
    partition: str | None = None,
) -> tuple[int | None, float | None]:
    """Query sinfo for the dominant compute-node CPU/memory spec.

    If *partition* is given, restrict the query to that partition (so
    heterogeneous clusters can size jobs differently per partition).
    Returns (cpus_per_node, mem_gb_per_node). Either element may be None
    if detection fails or sinfo is not available.
    """
    cmd = ["sinfo", "-h", "-o", "%c %m"]
    if partition:
        cmd.extend(["-p", partition])
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return (None, None)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return (None, None)

    # Tally node specs; each line is "<cpus> <mem_mb>"
    counts: dict[tuple[int, int], int] = {}
    for line in result.stdout.strip().splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        try:
            cpus = int(parts[0])
            mem_mb = int(parts[1].rstrip("+"))
        except ValueError:
            continue
        counts[(cpus, mem_mb)] = counts.get((cpus, mem_mb), 0) + 1

    if not counts:
        return (None, None)

    (cpus, mem_mb), _ = max(counts.items(), key=lambda kv: kv[1])
    return (cpus, mem_mb / 1024.0)


def resolve_execution_resources(
    profile: str,
    cfg: dict,
    login_resources: ResourceInfo,
    partition: str | None = None,
    cfg_cpus_key: str = "cluster_cpus_per_node",
    cfg_mem_key: str = "cluster_mem_gb_per_node",
) -> tuple[int, float, str]:
    """Return (cpus_per_job, mem_gb_per_job, source_label) for the chosen profile.

    For local execution, uses the login-machine resources directly.
    For cluster/cloud, prefers explicit config (*cfg_cpus_key* and
    *cfg_mem_key*), then SLURM auto-detection via sinfo (optionally
    filtered to *partition*), then conservative defaults.

    The source_label describes where the numbers came from (useful for
    the startup message).
    """
    if profile == "local":
        return (login_resources.cpu_count, login_resources.mem_gb, "local machine")

    cfg_cpus = cfg.get(cfg_cpus_key)
    cfg_mem = cfg.get(cfg_mem_key)
    if cfg_cpus and cfg_mem:
        return (int(cfg_cpus), float(cfg_mem), "config override")

    if profile == "slurm":
        detected_cpus, detected_mem = detect_slurm_node_resources(partition=partition)
        if detected_cpus and detected_mem:
            label = f"sinfo (partition={partition})" if partition else "sinfo"
            return (
                int(cfg_cpus or detected_cpus),
                float(cfg_mem or detected_mem),
                label,
            )

    # Conservative cluster defaults when nothing else works
    return (int(cfg_cpus or 32), float(cfg_mem or 256), "cluster defaults")


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
