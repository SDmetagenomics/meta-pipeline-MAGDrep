from __future__ import annotations
import os
import sys
from pathlib import Path
import click
from meta_pipeline_magdrep import __version__
from meta_pipeline_magdrep.config import (
    load_and_merge_config, VALID_STEPS, ConfigError,
    resolve_db_dir, DB_DIR_ENV_VAR,
)
from meta_pipeline_magdrep.resources import (
    detect_resources,
    resolve_execution_resources,
    compute_gtdbtk_pplacer_cpus,
    allocate_threads,
    CHECKM2_CONCURRENT_MEM_GB,
    SYSTEM_OVERHEAD_GB,
)

VALID_PROFILES = {"local", "slurm", "gcp"}

_PROJECT_ROOT = Path(__file__).parent.parent.parent


def _ensure_databases_on_path():
    """Add the project root to sys.path so `from databases.download` works
    regardless of the current working directory."""
    pr = str(_PROJECT_ROOT)
    if pr not in sys.path:
        sys.path.insert(0, pr)


@click.group()
@click.version_option(version=__version__)
def main():
    """meta-pipeline-MAGDrep: quality assessment and taxonomy of MAGs at scale."""
    pass


@main.command()
@click.option("--input", "-i", "input_dir", required=True,
              type=click.Path(exists=True, path_type=Path),
              help="Directory of input MAG FASTA files OR a text file with "
                   "one FASTA path per line (# comments allowed).")
@click.option("--output", "-o", "output_dir", required=True,
              type=click.Path(path_type=Path),
              help="Output directory.")
@click.option("--profile", default="local", show_default=True,
              type=click.Choice(list(VALID_PROFILES)),
              help="Execution profile: local, slurm, or gcp.")
@click.option("--steps", default=None,
              help="Comma-separated steps to run (e.g. checkm2,gtdbtk). Default: all.")
@click.option("--skip", default=None,
              help="Comma-separated steps to skip (e.g. gtdbtk).")
@click.option("--config", "config_file", default=None,
              type=click.Path(exists=True, path_type=Path),
              help="Path to a custom config YAML.")
@click.option("--dry-run", is_flag=True, default=False,
              help="Show what would be run without executing.")
@click.option("--jobs", "-j", default=None, type=int,
              help="Maximum parallel jobs. Overrides config.")
@click.option("--cluster-cpus", default=None, type=int,
              help="CPUs per standard compute node for SLURM/GCP. "
                   "Auto-detected from sinfo if not set.")
@click.option("--cluster-mem-gb", default=None, type=int,
              help="Memory (GB) per standard compute node. "
                   "Auto-detected from sinfo if not set.")
@click.option("--cluster-mem-node-cpus", default=None, type=int,
              help="CPUs on memory partition nodes (for GTDB-Tk). "
                   "Defaults to --cluster-cpus if not set.")
@click.option("--cluster-mem-node-mem-gb", default=None, type=int,
              help="Memory (GB) on memory partition nodes (for GTDB-Tk). "
                   "Defaults to --cluster-mem-gb if not set.")
@click.option("--slurm-standard-partition", default="normal", show_default=True,
              help="SLURM partition for CheckM2 and most rules.")
@click.option("--slurm-memory-partition", default=None,
              help="SLURM partition for GTDB-Tk (high-memory). "
                   "Defaults to --slurm-standard-partition if not set.")
def qc(input_dir, output_dir, profile, steps, skip, config_file, dry_run, jobs,
       cluster_cpus, cluster_mem_gb, cluster_mem_node_cpus, cluster_mem_node_mem_gb,
       slurm_standard_partition, slurm_memory_partition):
    """Run quality assessment on a directory of MAG FASTA files."""
    overrides = {"outdir": str(output_dir)}
    if jobs:
        overrides["max_parallel_jobs"] = jobs
    if cluster_cpus:
        overrides["cluster_cpus_per_node"] = cluster_cpus
    if cluster_mem_gb:
        overrides["cluster_mem_gb_per_node"] = cluster_mem_gb
    if cluster_mem_node_cpus:
        overrides["cluster_mem_node_cpus"] = cluster_mem_node_cpus
    if cluster_mem_node_mem_gb:
        overrides["cluster_mem_node_mem_gb"] = cluster_mem_node_mem_gb
    overrides["slurm_standard_partition"] = slurm_standard_partition
    overrides["slurm_memory_partition"] = slurm_memory_partition or slurm_standard_partition

    try:
        cfg = load_and_merge_config(config_file, overrides)
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Resolve which steps to run
    active_steps = set(cfg["steps"])
    if steps:
        requested = set(s.strip() for s in steps.split(","))
        invalid = requested - VALID_STEPS
        if invalid:
            click.echo(f"Error: Invalid step(s): {invalid}", err=True)
            sys.exit(1)
        active_steps = requested
    if skip:
        to_skip = set(s.strip() for s in skip.split(","))
        active_steps -= to_skip

    cfg["steps"] = sorted(active_steps)

    # Detect login-machine resources (always — used for local execution
    # and for selecting sensible defaults).
    login_resources = detect_resources()

    # Standard-partition sizing: CheckM2 and most other rules run here.
    std_cpus, std_mem_gb, std_source = resolve_execution_resources(
        profile, cfg, login_resources,
        partition=cfg.get("slurm_standard_partition") if profile == "slurm" else None,
    )

    # Memory-partition sizing: GTDB-Tk runs here on heterogeneous clusters.
    # Falls back to standard-partition sizing when no distinct memory
    # partition is configured.
    mem_partition = cfg.get("slurm_memory_partition")
    std_partition = cfg.get("slurm_standard_partition")
    distinct_memory = (
        profile == "slurm" and mem_partition and mem_partition != std_partition
    )
    if distinct_memory:
        mem_cpus, mem_mem_gb, mem_source = resolve_execution_resources(
            profile, cfg, login_resources,
            partition=mem_partition,
            cfg_cpus_key="cluster_mem_node_cpus",
            cfg_mem_key="cluster_mem_node_mem_gb",
        )
    else:
        mem_cpus, mem_mem_gb, mem_source = std_cpus, std_mem_gb, std_source

    if cfg["threads_per_job"] == "auto":
        cfg["threads_per_job"] = min(std_cpus, 8)
    if cfg["max_parallel_jobs"] == "auto":
        cfg["max_parallel_jobs"] = max(1, std_cpus) if profile == "local" else 500

    cfg.setdefault("gtdbtk", {})

    # When rules run on the same partition (same node pool), they contend
    # for CPUs, so split allocations. When on different partitions, each
    # rule gets its full partition's CPU budget.
    concurrent = len({"checkm2", "gtdbtk"} & set(cfg["steps"]))
    if concurrent > 1 and not distinct_memory:
        threads_alloc = allocate_threads(std_cpus, concurrent)
        checkm2_threads = threads_alloc["checkm2"]
        gtdbtk_threads = threads_alloc["gtdbtk"]
        # Reserve memory for a concurrent CheckM2 batch on same node
        pplacer_reserve = SYSTEM_OVERHEAD_GB + CHECKM2_CONCURRENT_MEM_GB
    else:
        checkm2_threads = std_cpus
        gtdbtk_threads = mem_cpus
        pplacer_reserve = SYSTEM_OVERHEAD_GB

    if cfg.get("checkm2_threads", "auto") == "auto":
        cfg["checkm2_threads"] = checkm2_threads
    if cfg["gtdbtk"].get("threads", "auto") == "auto":
        cfg["gtdbtk"]["threads"] = gtdbtk_threads
    if cfg["gtdbtk"].get("pplacer_cpus", "auto") == "auto":
        cfg["gtdbtk"]["pplacer_cpus"] = compute_gtdbtk_pplacer_cpus(
            mem_mem_gb,
            max_cpus=cfg["gtdbtk"]["threads"],
            reserve_gb=pplacer_reserve,
        )

    # Stash resolved partitions into config so the runner/profile can pick
    # them up for per-rule --set-resources overrides.
    cfg["_resolved_partitions"] = {
        "standard": std_partition,
        "memory": mem_partition,
    }

    # Startup banner
    if profile == "local":
        click.echo(f"Sizing jobs for {std_cpus} CPUs, {std_mem_gb:.0f} GB RAM (source: {std_source}).")
    elif distinct_memory:
        click.echo(
            f"Standard nodes ({std_partition}): {std_cpus} CPUs, {std_mem_gb:.0f} GB "
            f"(source: {std_source}).\n"
            f"Memory nodes ({mem_partition}): {mem_cpus} CPUs, {mem_mem_gb:.0f} GB "
            f"(source: {mem_source}).\n"
            f"CheckM2 routes to {std_partition}; GTDB-Tk routes to {mem_partition}."
        )
    else:
        click.echo(f"Sizing jobs for {std_cpus} CPUs, {std_mem_gb:.0f} GB RAM (source: {std_source}).")
        click.echo(f"Profile={profile}: SLURM/GCP handles node placement.")

    click.echo(
        f"CheckM2={cfg['checkm2_threads']} threads, "
        f"GTDB-Tk={cfg['gtdbtk']['threads']} threads, "
        f"pplacer_cpus={cfg['gtdbtk']['pplacer_cpus']}."
    )

    from meta_pipeline_magdrep.runner import run_snakemake
    run_snakemake(
        input_dir=input_dir,
        config=cfg,
        profile=profile,
        dry_run=dry_run,
    )


@main.group()
def db():
    """Manage reference databases."""
    pass


@db.command("update")
@click.option("--db-dir", default=None,
              type=click.Path(path_type=Path),
              help=f"Directory to download databases into. "
                   f"Defaults to ${DB_DIR_ENV_VAR} env var or ./databases/.")
@click.option("--only", default=None,
              help="Download only this database (checkm2 or gtdbtk).")
@click.option("--force", is_flag=True, default=False,
              help="Re-download even if already present.")
def db_update(db_dir, only, force):
    """Download required databases (CheckM2, GTDB-Tk)."""
    _ensure_databases_on_path()
    from databases.download import download_all_databases, _DOWNLOADERS, DATABASES

    db_path = resolve_db_dir(db_dir)
    click.echo(f"Database directory: {db_path}\n")

    if only:
        if only not in _DOWNLOADERS:
            click.echo(f"Error: Unknown database '{only}'. Choose from: {list(_DOWNLOADERS)}", err=True)
            sys.exit(1)
        meta = DATABASES[only]
        click.echo(f"Downloading {meta['display_name']}...")
        _DOWNLOADERS[only](db_path, force=force)
    else:
        click.echo("Downloading all databases...")
        download_all_databases(db_path, force=force)

    click.echo("\nDone. Run 'meta-pipeline-MAGDrep db status' to verify.")


@db.command("status")
@click.option("--db-dir", default=None,
              type=click.Path(path_type=Path),
              help=f"Database directory to inspect. "
                   f"Defaults to ${DB_DIR_ENV_VAR} env var or ./databases/.")
def db_status(db_dir):
    """Show installed database versions."""
    _ensure_databases_on_path()
    from databases.download import database_status

    db_path = resolve_db_dir(db_dir)
    click.echo(f"Database directory: {db_path}")
    env_val = os.environ.get(DB_DIR_ENV_VAR)
    if db_dir is None and env_val:
        click.echo(f"  (source: ${DB_DIR_ENV_VAR})")
    click.echo("")

    status = database_status(db_path)
    for name, info in status.items():
        icon = "OK" if info["present"] else "MISSING"
        click.echo(f"  [{icon:>7}]  {info['display_name']:<20}  {info['size_hint']}")
        if not info["present"] and info["directory_exists"]:
            click.echo(f"           Directory exists but download incomplete — run db update --only {name}")

    all_ok = all(s["present"] for s in status.values())
    if all_ok:
        click.echo("\nAll databases ready.")
    else:
        missing = [n for n, s in status.items() if not s["present"]]
        click.echo(f"\nMissing: {', '.join(missing)}. Run: meta-pipeline-MAGDrep db update")


@main.command()
@click.argument("results_dir", type=click.Path(exists=True, file_okay=False, path_type=Path))
def benchmark(results_dir):
    """Summarize step timing from a completed pipeline run."""
    bench_dir = Path(results_dir) / "benchmarks"
    if not bench_dir.exists():
        click.echo(f"No benchmarks directory found at {bench_dir}", err=True)
        sys.exit(1)

    # Each benchmark TSV has a header: s h:m:s max_rss max_vms max_uss max_pss io_in io_out mean_load cpu_time
    def parse_bench(p: Path) -> dict | None:
        try:
            with open(p) as f:
                header = f.readline().strip().split("\t")
                values = f.readline().strip().split("\t")
                if len(values) < len(header):
                    return None
                row = dict(zip(header, values))
                return {
                    "seconds": float(row.get("s", 0)),
                    "max_rss_mb": float(row.get("max_rss", 0) or 0),
                    "cpu_time": float(row.get("cpu_time", 0) or 0),
                }
        except (ValueError, IOError):
            return None

    def fmt_time(seconds: float) -> str:
        if seconds < 60:
            return f"{seconds:.1f}s"
        if seconds < 3600:
            return f"{seconds / 60:.1f}m"
        return f"{seconds / 3600:.2f}h"

    # Group benchmarks by step (directory name)
    steps: dict[str, list[dict]] = {}
    for tsv in sorted(bench_dir.rglob("*.tsv")):
        rel = tsv.relative_to(bench_dir)
        step = rel.parts[0] if len(rel.parts) > 1 else rel.stem
        data = parse_bench(tsv)
        if data:
            data["batch"] = rel.stem
            steps.setdefault(step, []).append(data)

    if not steps:
        click.echo("No benchmark data found.", err=True)
        return

    click.echo(f"{'Step':<22} {'Jobs':>5} {'Total':>8} {'Avg':>8} {'Max':>8} {'Max RSS':>10}")
    click.echo("-" * 68)
    grand_total = 0.0
    for step in sorted(steps):
        jobs = steps[step]
        seconds = [j["seconds"] for j in jobs]
        total = sum(seconds)
        grand_total += total
        avg = total / len(seconds)
        mx = max(seconds)
        max_rss = max(j["max_rss_mb"] for j in jobs)
        click.echo(
            f"{step:<22} {len(jobs):>5} {fmt_time(total):>8} {fmt_time(avg):>8} "
            f"{fmt_time(mx):>8} {max_rss:>8.0f} MB"
        )
    click.echo("-" * 68)
    click.echo(f"{'Total (sum of step wall times)':<42} {fmt_time(grand_total):>8}")


if __name__ == "__main__":
    main()
