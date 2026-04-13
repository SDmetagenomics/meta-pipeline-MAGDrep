import pytest
from pathlib import Path
from meta_pipeline_magdrep.inputs import (
    build_mag_path_map, mag_id_from_path,
)


def _make_fasta(p: Path, name: str) -> Path:
    f = p / name
    f.write_text(">seq1\nACGT\n")
    return f


def test_mag_id_from_path_strips_suffixes():
    assert mag_id_from_path("foo/bar/MAG_001.fna") == "MAG_001"
    assert mag_id_from_path("MAG_002.fasta.gz") == "MAG_002"
    assert mag_id_from_path("xyz.fa") == "xyz"
    assert mag_id_from_path("noext") == "noext"


def test_directory_input(tmp_path):
    """Directory mode: discover all FASTAs in the directory."""
    _make_fasta(tmp_path, "MAG_A.fna")
    _make_fasta(tmp_path, "MAG_B.fasta")
    _make_fasta(tmp_path, "MAG_C.fa.gz")
    (tmp_path / "ignore.txt").write_text("not a fasta")

    result = build_mag_path_map(tmp_path)
    assert set(result.keys()) == {"MAG_A", "MAG_B", "MAG_C"}
    assert result["MAG_A"].name == "MAG_A.fna"


def test_path_list_file(tmp_path):
    """List-file mode: read paths from a text file."""
    dir1 = tmp_path / "lab1"
    dir2 = tmp_path / "lab2"
    dir1.mkdir()
    dir2.mkdir()
    f1 = _make_fasta(dir1, "M1.fna")
    f2 = _make_fasta(dir2, "M2.fasta")

    listfile = tmp_path / "mags.txt"
    listfile.write_text(f"# header comment\n{f1}\n\n{f2}\n# trailing comment\n")

    result = build_mag_path_map(listfile)
    assert set(result.keys()) == {"M1", "M2"}
    assert result["M1"] == f1.resolve()
    assert result["M2"] == f2.resolve()


def test_path_list_relative_paths(tmp_path):
    """Relative paths in a list file resolve against the file's directory."""
    sub = tmp_path / "genomes"
    sub.mkdir()
    f = _make_fasta(sub, "X.fna")

    listfile = tmp_path / "list.txt"
    listfile.write_text("genomes/X.fna\n")

    result = build_mag_path_map(listfile)
    assert result["X"] == f.resolve()


def test_path_list_missing_file_raises(tmp_path):
    """Bad paths in a list file should fail loud, not silently skip."""
    listfile = tmp_path / "bad.txt"
    listfile.write_text(f"{tmp_path}/does_not_exist.fna\n")

    with pytest.raises(ValueError, match="does not exist"):
        build_mag_path_map(listfile)


def test_duplicate_mag_id_raises(tmp_path):
    """Two FASTAs with the same stem should raise."""
    a_dir = tmp_path / "a"
    b_dir = tmp_path / "b"
    a_dir.mkdir()
    b_dir.mkdir()
    _make_fasta(a_dir, "MAG_X.fna")
    _make_fasta(b_dir, "MAG_X.fasta")

    listfile = tmp_path / "dups.txt"
    listfile.write_text(f"{a_dir}/MAG_X.fna\n{b_dir}/MAG_X.fasta\n")

    with pytest.raises(ValueError, match="Duplicate MAG ID"):
        build_mag_path_map(listfile)


def test_invalid_input_path_raises(tmp_path):
    """Path that is neither a directory nor a regular file raises."""
    with pytest.raises(ValueError, match="must be a directory or a text file"):
        build_mag_path_map(tmp_path / "does_not_exist")


def test_path_list_with_tilde_expansion(tmp_path, monkeypatch):
    """Paths starting with ~ should expand to home directory."""
    # Set HOME to tmp_path so ~ expands there
    monkeypatch.setenv("HOME", str(tmp_path))
    f = _make_fasta(tmp_path, "Home.fna")

    listfile = tmp_path / "list.txt"
    listfile.write_text("~/Home.fna\n")

    result = build_mag_path_map(listfile)
    assert "Home" in result
