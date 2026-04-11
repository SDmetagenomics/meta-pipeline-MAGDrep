import pytest
from pathlib import Path

TEST_DATA_DIR = Path(__file__).parent / "data"
TEST_MAGS_DIR = TEST_DATA_DIR / "mags"


@pytest.fixture
def test_mags_dir():
    return TEST_MAGS_DIR


@pytest.fixture
def tmp_output_dir(tmp_path):
    out = tmp_path / "results"
    out.mkdir()
    return out


@pytest.fixture
def default_config():
    return {
        "outdir": "results",
        "steps": ["genome_stats", "checkm2", "gunc", "gtdbtk", "dereplicate"],
        "batch_size": 1000,
        "threads_per_job": 4,
        "max_parallel_jobs": 8,
        "fasta_extensions": [".fna", ".fasta", ".fa", ".fna.gz", ".fasta.gz", ".fa.gz"],
        "db_dir": "databases",
        "db_versions": {
            "checkm2": "1.0.2",
            "gunc": "gtdb_214",
            "gtdbtk": "r226",
        },
        "quality_filter": {
            "high_completeness": 90.0,
            "high_contamination": 5.0,
            "medium_completeness": 60.0,
            "medium_contamination": 10.0,
            "min_quality_score": 50.0,
            "gunc_css_threshold": 0.45,
            "default_filter": "medium_quality",
        },
        "dereplicate": {
            "ani_threshold": 95.0,
            "min_af": 10.0,
            "score_weights": {
                "w_qscore": 1.0,
                "w_completeness": 1.0,
                "w_n50": 0.5,
                "w_contam": 0.5,
                "w_gunc": 0.5,
            },
        },
    }


@pytest.fixture
def tmp_mag_dir(tmp_path):
    """Create a temporary directory with small synthetic FASTA files."""
    mag_dir = tmp_path / "mags"
    mag_dir.mkdir()
    (mag_dir / "test_mag_001.fna").write_text(
        ">contig_1\n" + "ATGC" * 250 + "\n"
        ">contig_2\n" + "GCTA" * 200 + "\n"
    )
    (mag_dir / "test_mag_002.fna").write_text(
        ">contig_1\n" + "ATGC" * 300 + "\n"
    )
    return mag_dir
