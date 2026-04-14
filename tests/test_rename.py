import pytest
from pathlib import Path

from meta_pipeline_magdrep.rename import (
    check_uniqueness, assign_unique_genome_ids, stage_normalized_inputs,
    InputValidationError, _suffix,
)


def _fasta(p: Path, contigs: list[str]) -> Path:
    lines = []
    for name in contigs:
        lines.append(f">{name}")
        lines.append("ACGT")
    p.write_text("\n".join(lines) + "\n")
    return p


def test_suffix_generation():
    """A-Z then AA,AB,…"""
    assert _suffix(0) == "A"
    assert _suffix(25) == "Z"
    assert _suffix(26) == "AA"
    assert _suffix(27) == "AB"
    assert _suffix(51) == "AZ"


def test_assign_unique_genome_ids_no_conflict(tmp_path):
    a = _fasta(tmp_path / "A.fna", ["c1"])
    b = _fasta(tmp_path / "B.fna", ["c1"])
    result = assign_unique_genome_ids([a, b])
    assert result == {a: "A", b: "B"}


def test_assign_unique_genome_ids_with_conflict(tmp_path):
    d1 = tmp_path / "d1"
    d2 = tmp_path / "d2"
    d3 = tmp_path / "d3"
    d1.mkdir(); d2.mkdir(); d3.mkdir()
    a = _fasta(d1 / "X.fna", ["c1"])
    b = _fasta(d2 / "X.fna", ["c1"])
    c = _fasta(d3 / "X.fna", ["c1"])
    result = assign_unique_genome_ids([a, b, c])
    assert set(result.values()) == {"X_A", "X_B", "X_C"}


def test_check_uniqueness_clean_directory(tmp_path):
    _fasta(tmp_path / "A.fna", ["c1", "c2"])
    _fasta(tmp_path / "B.fna", ["c1", "c2"])  # within-genome unique — fine
    report = check_uniqueness(tmp_path)
    assert report == {}


def test_check_uniqueness_duplicate_genomes(tmp_path):
    d1 = tmp_path / "d1"
    d2 = tmp_path / "d2"
    d1.mkdir(); d2.mkdir()
    _fasta(d1 / "X.fna", ["c1"])
    _fasta(d2 / "X.fna", ["c1"])
    listfile = tmp_path / "list.txt"
    listfile.write_text(f"{d1}\n{d2}\n")
    report = check_uniqueness(listfile)
    assert "duplicate_genome_ids" in report
    assert "X" in report["duplicate_genome_ids"]


def test_check_uniqueness_duplicate_contigs(tmp_path):
    _fasta(tmp_path / "X.fna", ["c1", "c1", "c2"])
    report = check_uniqueness(tmp_path)
    assert "contig_collisions" in report


def test_stage_without_rename_succeeds_when_clean(tmp_path):
    _fasta(tmp_path / "A.fna", ["c1"])
    _fasta(tmp_path / "B.fna", ["c1"])  # within-genome unique
    staging = tmp_path / "stage"
    _, id_map = stage_normalized_inputs(tmp_path, staging, rename=False)
    assert set(id_map.keys()) == {"A", "B"}
    # Symlinks, not copies
    assert (staging / "A.fna").is_symlink()


def test_stage_without_rename_fails_on_duplicates(tmp_path):
    d1 = tmp_path / "d1"
    d2 = tmp_path / "d2"
    d1.mkdir(); d2.mkdir()
    _fasta(d1 / "X.fna", ["c1"])
    _fasta(d2 / "X.fna", ["c1"])
    listfile = tmp_path / "list.txt"
    listfile.write_text(f"{d1}\n{d2}\n")
    with pytest.raises(InputValidationError, match="Duplicate genome IDs"):
        stage_normalized_inputs(listfile, tmp_path / "stage", rename=False)


def test_stage_with_rename_resolves_duplicates_and_rewrites_contigs(tmp_path):
    d1 = tmp_path / "d1"
    d2 = tmp_path / "d2"
    d1.mkdir(); d2.mkdir()
    _fasta(d1 / "X.fna", ["original_contig_1", "original_contig_2"])
    _fasta(d2 / "X.fna", ["original_contig_1"])  # duplicate stem + collides across genomes
    listfile = tmp_path / "list.txt"
    listfile.write_text(f"{d1}\n{d2}\n")

    staging = tmp_path / "stage"
    _, id_map = stage_normalized_inputs(listfile, staging, rename=True)

    # Genome IDs disambiguated
    assert set(id_map.keys()) == {"X_A", "X_B"}

    # Each output file has the new contig naming
    for mag_id, path in id_map.items():
        assert path.exists()
        headers = [line[1:].strip() for line in path.read_text().splitlines() if line.startswith(">")]
        assert all(h.startswith(f"{mag_id}_scaffold_") for h in headers), headers
        # Numbering is sequential
        assert [int(h.split("_")[-1]) for h in headers] == list(range(1, len(headers) + 1))


def test_stage_with_rename_fixes_within_genome_contig_collisions(tmp_path):
    """--rename rewrites all contigs, so duplicate names within a genome
    are silently normalized away."""
    _fasta(tmp_path / "G.fna", ["contig1", "contig1", "contig2"])
    staging = tmp_path / "stage"
    _, id_map = stage_normalized_inputs(tmp_path, staging, rename=True)
    headers = [l[1:].strip() for l in id_map["G"].read_text().splitlines() if l.startswith(">")]
    assert headers == ["G_scaffold_1", "G_scaffold_2", "G_scaffold_3"]
