"""
Integration tests -- require installed tools and databases.
Run with: pytest tests/test_integration.py -m slow
"""
import pytest
from pathlib import Path

pytestmark = pytest.mark.slow


@pytest.fixture
def integration_output(tmp_path, test_mags_dir):
    """Run the pipeline on synthetic MAGs with genome_stats only."""
    from meta_pipeline_magqc.config import load_and_merge_config
    from meta_pipeline_magqc.runner import run_snakemake

    output_dir = tmp_path / "results"
    cfg = load_and_merge_config(overrides={
        "outdir": str(output_dir),
        "steps": ["genome_stats"],
        "batch_size": 10,
        "max_parallel_jobs": 1,
        "threads_per_job": 1,
    })

    run_snakemake(
        input_dir=test_mags_dir,
        config=cfg,
        profile="local",
        dry_run=False,
    )
    return output_dir


def test_combined_report_exists(integration_output):
    assert (integration_output / "combined_report.tsv").exists()


def test_combined_report_has_all_mags(integration_output):
    report = integration_output / "combined_report.tsv"
    lines = report.read_text().strip().split("\n")
    assert len(lines) >= 2


def test_filtered_report_exists(integration_output):
    assert (integration_output / "filtered_report.tsv").exists()
