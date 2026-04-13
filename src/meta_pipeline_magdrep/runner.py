from __future__ import annotations
import sys
from pathlib import Path
import click

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_SNAKEFILE = _PROJECT_ROOT / "Snakefile"
_PROFILES_DIR = _PROJECT_ROOT / "config" / "profiles"


def build_snakemake_config(input_dir: Path, config: dict) -> dict:
    """Build the config dict passed to Snakemake."""
    snk_config = dict(config)
    snk_config["input_dir"] = str(input_dir)
    return snk_config


def run_snakemake(
    input_dir: Path,
    config: dict,
    profile: str = "local",
    dry_run: bool = False,
) -> None:
    """
    Invoke Snakemake via its Python API (local) or CLI (SLURM).
    """
    snk_config = build_snakemake_config(input_dir=input_dir, config=config)

    if profile != "local":
        _run_snakemake_cli(snk_config, profile, dry_run, config)
    else:
        _run_snakemake_api(snk_config, config, dry_run)


def _run_snakemake_api(snk_config: dict, config: dict, dry_run: bool) -> None:
    """Run Snakemake in-process via the Python API (local executor)."""
    try:
        from snakemake.api import SnakemakeApi
        from snakemake.settings.types import (
            ConfigSettings,
            DAGSettings,
            DeploymentSettings,
            ExecutionSettings,
            OutputSettings,
            ResourceSettings,
            StorageSettings,
            WorkflowSettings,
        )
    except ImportError:
        click.echo("Error: Snakemake is not installed. Run: pip install snakemake", err=True)
        sys.exit(1)

    cores = config.get("max_parallel_jobs", 1)

    try:
        with SnakemakeApi(OutputSettings(printshellcmds=True, verbose=False)) as api:
            workflow = api.workflow(
                snakefile=_SNAKEFILE,
                workdir=_PROJECT_ROOT,
                resource_settings=ResourceSettings(cores=cores, nodes=cores),
                config_settings=ConfigSettings(config=snk_config),
                storage_settings=StorageSettings(),
                workflow_settings=WorkflowSettings(),
                deployment_settings=DeploymentSettings(),
            )
            dag = workflow.dag(dag_settings=DAGSettings())
            executor = "dryrun" if dry_run else "local"
            dag.execute_workflow(executor=executor)
    except SystemExit as e:
        if e.code != 0:
            raise
    except Exception as e:
        click.echo(f"Snakemake error: {e}", err=True)
        raise


def _run_snakemake_cli(
    snk_config: dict, profile: str, dry_run: bool, config: dict
) -> None:
    """Run Snakemake via CLI subprocess with a cluster profile."""
    import subprocess

    profile_dir = _PROFILES_DIR / profile
    if not profile_dir.exists():
        click.echo(f"Error: Profile '{profile}' not found at {profile_dir}", err=True)
        sys.exit(1)

    cmd = [
        "snakemake",
        "--snakefile", str(_SNAKEFILE),
        "--directory", str(_PROJECT_ROOT),
        "--profile", str(profile_dir),
    ]

    # Build --config args (skip internal resolution artifacts)
    config_args = []
    for k, v in snk_config.items():
        if k.startswith("_"):
            continue
        config_args.append(f"{k}={v}")
    if config_args:
        cmd.extend(["--config"] + config_args)

    # SLURM partition routing: rules land on the right partition via
    # --set-resources overrides. Standard rules (checkm2, etc.) go to the
    # standard partition; gtdbtk_batch goes to the memory partition.
    partitions = snk_config.get("_resolved_partitions") or {}
    std_part = partitions.get("standard")
    mem_part = partitions.get("memory") or std_part
    if profile == "slurm" and (std_part or mem_part):
        set_resource_args = []
        # Default partition for all rules
        if std_part:
            set_resource_args.append(f"slurm_partition={std_part}")
        # gtdbtk_batch override to memory partition (if different)
        if mem_part and mem_part != std_part:
            set_resource_args.append(f"gtdbtk_batch:slurm_partition={mem_part}")
        if set_resource_args:
            cmd.extend(["--default-resources"] + [
                a for a in set_resource_args if ":" not in a
            ])
            rule_overrides = [a for a in set_resource_args if ":" in a]
            if rule_overrides:
                cmd.extend(["--set-resources"] + rule_overrides)

    cores_per_node = config.get("slurm_cores_per_node", 64)
    cmd.extend(["--cores", str(cores_per_node)])

    if dry_run:
        cmd.append("--dry-run")

    click.echo(f"Running Snakemake with {profile} profile...")
    result = subprocess.run(cmd, cwd=_PROJECT_ROOT)
    if result.returncode != 0:
        click.echo(f"Snakemake error: exited with code {result.returncode}", err=True)
        sys.exit(result.returncode)
