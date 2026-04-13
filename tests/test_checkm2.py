import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from scripts.run_checkm2 import run_checkm2, parse_checkm2_output


MOCK_CHECKM2_TSV = (
    "Name\tCompleteness\tContamination\tCompleteness_Model_Used\tTranslation_Table_Used\tAdditional_Notes\n"
    "synthetic_mag_001\t95.5\t1.2\tNeural Network (Specific Model)\t11\tNone\n"
    "synthetic_mag_002\t78.3\t3.4\tNeural Network (General Model)\t11\tNone\n"
)


def test_parse_checkm2_output(tmp_path):
    """Test parsing of CheckM2 quality_report.tsv."""
    report = tmp_path / "quality_report.tsv"
    report.write_text(MOCK_CHECKM2_TSV)
    rows = parse_checkm2_output(report)
    assert len(rows) == 2
    assert rows[0]["mag_id"] == "synthetic_mag_001"
    assert rows[0]["completeness"] == pytest.approx(95.5)
    assert rows[0]["contamination"] == pytest.approx(1.2)
    assert rows[0]["completeness_model_used"] == "Neural Network (Specific Model)"
    assert rows[1]["mag_id"] == "synthetic_mag_002"


@patch("subprocess.run")
def test_run_checkm2_calls_correct_command(mock_run, tmp_path):
    """Test that CheckM2 is invoked with correct arguments."""
    mock_run.return_value = MagicMock(returncode=0)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "output"
    output_tsv = tmp_path / "results.tsv"

    output_dir.mkdir(parents=True)
    (output_dir / "quality_report.tsv").write_text(MOCK_CHECKM2_TSV)

    run_checkm2(str(input_dir), str(output_dir), str(output_tsv), threads=16)

    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    # We invoke checkm2 via a python wrapper to force fork multiprocessing;
    # verify the wrapper includes the expected checkm2 arguments.
    assert cmd[0] == "python"
    assert cmd[1] == "-c"
    wrapper = cmd[2]
    assert "checkm2" in wrapper
    assert "predict" in wrapper
    assert "--threads" in wrapper
