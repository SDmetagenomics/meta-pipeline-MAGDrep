import pytest
from pathlib import Path
from meta_pipeline_magdrep.inputs import (
    build_mag_path_map, mag_id_from_path, collect_all_fasta_paths,
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


def test_path_list_file_with_directories(tmp_path):
    """List-file mode: each line is a directory, every FASTA in it is a MAG."""
    dir1 = tmp_path / "sample_1_bins"
    dir2 = tmp_path / "sample_2_bins"
    dir1.mkdir()
    dir2.mkdir()
    _make_fasta(dir1, "bin.001.fna")
    _make_fasta(dir1, "bin.002.fna")
    _make_fasta(dir2, "bin.042.fasta")

    listfile = tmp_path / "mag_dirs.txt"
    listfile.write_text(f"# header comment\n{dir1}\n\n{dir2}\n# trailing comment\n")

    result = build_mag_path_map(listfile)
    assert set(result.keys()) == {"bin.001", "bin.002", "bin.042"}


def test_path_list_relative_directory(tmp_path):
    """Relative directory paths resolve against the list file's location."""
    sub = tmp_path / "genomes"
    sub.mkdir()
    _make_fasta(sub, "X.fna")

    listfile = tmp_path / "list.txt"
    listfile.write_text("genomes\n")

    result = build_mag_path_map(listfile)
    assert "X" in result


def test_path_list_missing_directory_raises(tmp_path):
    """Bad directory paths in a list file should fail loud."""
    listfile = tmp_path / "bad.txt"
    listfile.write_text(f"{tmp_path}/does_not_exist\n")

    with pytest.raises(ValueError, match="directory does not exist"):
        build_mag_path_map(listfile)


def test_path_list_rejects_fasta_path_as_line(tmp_path):
    """A line pointing at a file (not a directory) should raise — directories only."""
    d = tmp_path / "bins"
    d.mkdir()
    f = _make_fasta(d, "bin.fna")

    listfile = tmp_path / "wrong.txt"
    listfile.write_text(f"{f}\n")

    with pytest.raises(ValueError, match="expected a directory of FASTA files"):
        build_mag_path_map(listfile)


def test_path_list_empty_directory_raises(tmp_path):
    """A directory with no FASTAs inside should raise a clear error."""
    empty = tmp_path / "empty_bins"
    empty.mkdir()
    listfile = tmp_path / "list.txt"
    listfile.write_text(f"{empty}\n")
    with pytest.raises(ValueError, match="no FASTA files found"):
        build_mag_path_map(listfile)


def test_duplicate_mag_id_raises(tmp_path):
    """Two FASTAs with the same stem across directories should raise."""
    a_dir = tmp_path / "a"
    b_dir = tmp_path / "b"
    a_dir.mkdir()
    b_dir.mkdir()
    _make_fasta(a_dir, "MAG_X.fna")
    _make_fasta(b_dir, "MAG_X.fasta")

    listfile = tmp_path / "dups.txt"
    listfile.write_text(f"{a_dir}\n{b_dir}\n")

    with pytest.raises(ValueError, match="Duplicate MAG ID"):
        build_mag_path_map(listfile)


def test_duplicate_allowed_when_flag_set(tmp_path):
    """allow_duplicates=True lets collisions through (caller disambiguates)."""
    a_dir = tmp_path / "a"
    b_dir = tmp_path / "b"
    a_dir.mkdir()
    b_dir.mkdir()
    _make_fasta(a_dir, "MAG_X.fna")
    _make_fasta(b_dir, "MAG_X.fasta")

    listfile = tmp_path / "dups.txt"
    listfile.write_text(f"{a_dir}\n{b_dir}\n")

    # Should NOT raise
    result = build_mag_path_map(listfile, allow_duplicates=True)
    assert "MAG_X" in result


def test_collect_all_fasta_paths_returns_duplicates(tmp_path):
    """collect_all_fasta_paths returns the raw list including dup stems."""
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir()
    b.mkdir()
    _make_fasta(a, "X.fna")
    _make_fasta(b, "X.fna")
    listfile = tmp_path / "list.txt"
    listfile.write_text(f"{a}\n{b}\n")
    all_paths = collect_all_fasta_paths(listfile)
    assert len(all_paths) == 2


def test_invalid_input_path_raises(tmp_path):
    """Path that is neither a directory nor a regular file raises."""
    with pytest.raises(ValueError, match="must be a directory or a text file"):
        build_mag_path_map(tmp_path / "does_not_exist")


def test_path_list_with_tilde_expansion(tmp_path, monkeypatch):
    """Directory paths starting with ~ should expand to home directory."""
    # Set HOME to tmp_path so ~ expands there
    monkeypatch.setenv("HOME", str(tmp_path))
    sub = tmp_path / "bins"
    sub.mkdir()
    _make_fasta(sub, "Home.fna")

    listfile = tmp_path / "list.txt"
    listfile.write_text("~/bins\n")

    result = build_mag_path_map(listfile)
    assert "Home" in result
