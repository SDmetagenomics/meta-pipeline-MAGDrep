from __future__ import annotations
import sys
from pathlib import Path
import click
from meta_pipeline_magdrep import __version__
from meta_pipeline_magdrep.config import load_and_merge_config, VALID_STEPS, ConfigError
from meta_pipeline_magdrep.resources import detect_resources

VALID_PROFILES = {"local", "slurm"}


@click.group()
@click.version_option(version=__version__)
def main():
    """meta-pipeline-MAGDrep: quality assessment and taxonomy of MAGs at scale."""
    pass


@main.command()
@click.option("--input", "-i", "input_dir", required=True,
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Directory of input MAG FASTA files.")
@click.option("--output", "-o", "output_dir", required=True,
              type=click.Path(path_type=Path),
              help="Output directory.")
@click.option("--profile", default="local", show_default=True,
              type=click.Choice(list(VALID_PROFILES)),
              help="Execution profile: local or slurm.")
@click.option("--steps", default=None,
              help="Comma-separated steps to run (e.g. checkm2,gtdbtk). Default: all.")
@click.option("--skip", default=None,
              help="Comma-separated steps to skip (e.g. gunc).")
@click.option("--config", "config_file", default=None,
              type=click.Path(exists=True, path_type=Path),
              help="Path to a custom config YAML.")
@click.option("--dry-run", is_flag=True, default=False,
              help="Show what would be run without executing.")
@click.option("--jobs", "-j", default=None, type=int,
              help="Maximum parallel jobs. Overrides config.")
def qc(input_dir, output_dir, profile, steps, skip, config_file, dry_run, jobs):
    """Run quality assessment on a directory of MAG FASTA files."""
    overrides = {"outdir": str(output_dir)}
    if jobs:
        overrides["max_parallel_jobs"] = jobs

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

    # Detect and resolve resources
    resources = detect_resources()
    if cfg["threads_per_job"] == "auto":
        cfg["threads_per_job"] = min(resources.cpu_count, 8)
    if cfg["max_parallel_jobs"] == "auto":
        cfg["max_parallel_jobs"] = max(1, resources.cpu_count // cfg["threads_per_job"])

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
@click.option("--db-dir", default="databases", show_default=True,
              type=click.Path(path_type=Path),
              help="Directory to download databases into.")
@click.option("--force", is_flag=True, default=False,
              help="Re-download even if already present.")
def db_update(db_dir, force):
    """Download required databases (CheckM2, GUNC, GTDB-Tk)."""
    click.echo("Database download not yet implemented.")
    click.echo("Please download manually:")
    click.echo("  CheckM2: checkm2 database --download --path <db_dir>")
    click.echo("  GUNC: gunc download_db <db_dir> -db gtdb_214")
    click.echo("  GTDB-Tk: download-db.sh <db_dir>")


@db.command("status")
@click.option("--db-dir", default="databases", show_default=True,
              type=click.Path(path_type=Path),
              help="Database directory to inspect.")
def db_status(db_dir):
    """Show installed database versions."""
    project_root = Path(__file__).parent.parent.parent
    db_path = Path(db_dir)
    if not db_path.is_absolute():
        db_path = project_root / db_path
    click.echo(f"Checking databases in: {db_path}")
    if not db_path.exists():
        click.echo("  No databases directory found.")
        return
    for child in sorted(db_path.iterdir()):
        if child.is_dir():
            click.echo(f"  {child.name}: present")


if __name__ == "__main__":
    main()
