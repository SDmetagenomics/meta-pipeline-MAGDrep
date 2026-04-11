import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from scripts.run_gunc import parse_gunc_output, run_gunc

MOCK_GUNC_TSV = (
    "genome\tn_genes_called\tn_genes_mapped\tn_contigs\ttaxonomic_level\t"
    "proportion_genes_retained_in_major_clade\tgenes_retained_index\t"
    "clade_separation_score\tcontamination_portion\tn_effective_surplus_clades\t"
    "mean_hit_identity\treference_representation_score\tpass.GUNC\n"
    "synthetic_mag_001\t1500\t1400\t10\tgenus\t0.85\t0.9\t0.12\t0.08\t1.2\t0.95\t0.88\ttrue\n"
    "synthetic_mag_002\t1200\t1100\t8\tphylum\t0.65\t0.7\t0.55\t0.25\t3.1\t0.82\t0.65\tfalse\n"
)


def test_parse_gunc_output(tmp_path):
    report = tmp_path / "GUNC.maxCSS_level.tsv"
    report.write_text(MOCK_GUNC_TSV)
    rows = parse_gunc_output(report)
    assert len(rows) == 2
    assert rows[0]["mag_id"] == "synthetic_mag_001"
    assert rows[0]["css"] == pytest.approx(0.12)
    assert rows[0]["rrs"] == pytest.approx(0.88)
    assert rows[0]["contamination_portion"] == pytest.approx(0.08)
    assert rows[0]["taxonomic_level"] == "genus"
    assert rows[0]["pass_gunc"] is True
    assert rows[1]["pass_gunc"] is False


def test_parse_gunc_output_css_threshold(tmp_path):
    report = tmp_path / "GUNC.maxCSS_level.tsv"
    report.write_text(MOCK_GUNC_TSV)
    rows = parse_gunc_output(report, css_threshold=0.45)
    assert rows[0]["pass_gunc"] is True
    assert rows[1]["pass_gunc"] is False


@patch("subprocess.run")
def test_run_gunc_calls_correct_command(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)
    output_tsv = tmp_path / "results.tsv"

    (output_dir / "GUNC.maxCSS_level.tsv").write_text(MOCK_GUNC_TSV)

    run_gunc(str(input_dir), str(output_dir), str(output_tsv),
             threads=16, db_type="gtdb_214")

    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "gunc" in cmd[0]
    assert "run" in cmd
