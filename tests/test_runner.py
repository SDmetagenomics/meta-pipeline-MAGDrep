import pytest
from pathlib import Path
from meta_pipeline_magdrep.runner import build_snakemake_config


@pytest.fixture
def sample_config():
    return {
        "outdir": "results",
        "steps": ["genome_stats", "checkm2"],
        "batch_size": 1000,
        "max_parallel_jobs": 4,
    }


def test_build_snakemake_config_includes_input_dir(tmp_path, sample_config):
    snk_cfg = build_snakemake_config(input_dir=tmp_path, config=sample_config)
    assert snk_cfg["input_dir"] == str(tmp_path)


def test_build_snakemake_config_includes_all_keys(tmp_path, sample_config):
    snk_cfg = build_snakemake_config(input_dir=tmp_path, config=sample_config)
    for key in ("outdir", "steps", "batch_size"):
        assert key in snk_cfg, f"Missing key: {key}"
