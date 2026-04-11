import pytest
from pathlib import Path
from scripts.genome_stats import compute_genome_stats, _compute_n50, write_stats_tsv


def test_compute_n50_simple():
    # Contigs: 100, 200, 300. Total=600, half=300.
    # Sorted desc: 300, 200, 100. Cumsum: 300 >= 300. N50=300.
    assert _compute_n50([100, 200, 300]) == 300


def test_compute_n50_single_contig():
    assert _compute_n50([5000]) == 5000


def test_compute_n50_equal_contigs():
    # 4 x 1000. Total=4000, half=2000. Cumsum: 1000, 2000 >= 2000. N50=1000.
    assert _compute_n50([1000, 1000, 1000, 1000]) == 1000


def test_compute_n50_empty():
    assert _compute_n50([]) == 0


def test_compute_genome_stats_synthetic(tmp_path):
    """Test genome stats on a small synthetic FASTA."""
    fasta = tmp_path / "test_mag.fna"
    fasta.write_text(
        ">contig_1\n" + "G" * 100 + "\n"
        ">contig_2\n" + "C" * 200 + "\n"
    )
    stats = compute_genome_stats(fasta)
    assert stats["mag_id"] == "test_mag"
    assert stats["total_length_bp"] == 300
    assert stats["contig_count"] == 2
    assert stats["n50_bp"] == 200
    assert stats["largest_contig_bp"] == 200
    assert stats["gc_percent"] == pytest.approx(100.0, abs=0.1)


def test_compute_genome_stats_mixed_gc(tmp_path):
    """Test GC computation with mixed bases."""
    fasta = tmp_path / "mixed.fna"
    fasta.write_text(">contig_1\n" + "ATGC" * 50 + "\n")
    stats = compute_genome_stats(fasta)
    assert stats["gc_percent"] == pytest.approx(50.0, abs=0.1)


def test_compute_genome_stats_gzipped(tmp_path):
    """Test that gzipped FASTAs are handled."""
    import gzip
    fasta = tmp_path / "gz_mag.fna.gz"
    with gzip.open(fasta, "wt") as f:
        f.write(">contig_1\n" + "ATGC" * 100 + "\n")
    stats = compute_genome_stats(fasta)
    assert stats["mag_id"] == "gz_mag"
    assert stats["total_length_bp"] == 400


def test_write_stats_tsv(tmp_path):
    """Test TSV output format."""
    stats = {
        "mag_id": "test",
        "total_length_bp": 1000,
        "gc_percent": 45.5,
        "contig_count": 3,
        "n50_bp": 500,
        "largest_contig_bp": 600,
    }
    out = tmp_path / "stats.tsv"
    write_stats_tsv(stats, out)
    lines = out.read_text().strip().split("\n")
    assert len(lines) == 2
    assert lines[0] == "mag_id\ttotal_length_bp\tgc_percent\tcontig_count\tn50_bp\tlargest_contig_bp"
    assert lines[1].startswith("test\t")
