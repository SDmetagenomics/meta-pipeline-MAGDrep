import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from scripts.run_checkm1 import parse_checkm1_output, run_checkm1, _resolve_checkm1_db


MOCK_CHECKM1_TSV = (
    "Bin Id\tMarker lineage\t# genomes\t# markers\t# marker sets\t0\t1\t2\t3\t4\t5+\t"
    "Completeness\tContamination\tStrain heterogeneity\n"
    "mag_A\tc__Gammaproteobacteria (UID4274)\t119\t544\t284\t10\t530\t4\t0\t0\t0\t"
    "98.41\t0.42\t25.00\n"
    "mag_B\tk__Bacteria (UID203)\t5449\t104\t58\t25\t75\t3\t1\t0\t0\t"
    "70.12\t2.85\t0.00\n"
)


def test_parse_checkm1_output(tmp_path):
    report = tmp_path / "checkm1_summary.tsv"
    report.write_text(MOCK_CHECKM1_TSV)
    rows = parse_checkm1_output(report)
    assert len(rows) == 2
    assert rows[0]["mag_id"] == "mag_A"
    assert rows[0]["completeness"] == pytest.approx(98.41)
    assert rows[0]["contamination"] == pytest.approx(0.42)
    assert rows[0]["strain_heterogeneity"] == pytest.approx(25.0)
    assert "Gammaproteobacteria" in rows[0]["checkm1_marker_lineage"]
    assert rows[1]["strain_heterogeneity"] == pytest.approx(0.0)


def test_resolve_checkm1_db_accepts_root_dir(tmp_path):
    """If the db dir already contains the marker file, use it directly."""
    (tmp_path / "selected_marker_sets.tsv").write_text("")
    assert _resolve_checkm1_db(str(tmp_path)) == str(tmp_path)


def test_resolve_checkm1_db_descends_into_subdir(tmp_path):
    """If marker file is one level down in a 'checkm1' subdir, descend."""
    sub = tmp_path / "checkm1"
    sub.mkdir()
    (sub / "selected_marker_sets.tsv").write_text("")
    assert _resolve_checkm1_db(str(tmp_path)) == str(sub)


@patch("scripts.run_checkm1._conda_available", return_value=False)
@patch("scripts.run_checkm1.subprocess.run")
def test_run_checkm1_invokes_lineage_wf(mock_run, _mock_conda, tmp_path):
    """Sanity-check the command line we build."""
    mock_run.return_value = MagicMock(returncode=0)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    (input_dir / "mag_A.fna").write_text(">c1\nACGT\n")

    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)
    (output_dir / "checkm1_summary.tsv").write_text(MOCK_CHECKM1_TSV)

    run_checkm1(str(input_dir), str(output_dir), str(tmp_path / "out.tsv"), threads=4)

    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    # Without conda, we invoke checkm directly
    assert cmd[0] == "checkm"
    assert cmd[1] == "lineage_wf"
    assert "--tab_table" in cmd
    assert "--threads" in cmd
    assert "4" in cmd  # the threads value
