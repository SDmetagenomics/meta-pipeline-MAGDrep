import pytest
from click.testing import CliRunner
from meta_pipeline_magdrep.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_version_flag(runner):
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "1.0.0" in result.output


def test_help_flag(runner):
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "qc" in result.output
    assert "db" in result.output


def test_qc_requires_input(runner):
    result = runner.invoke(main, ["qc"])
    assert result.exit_code != 0
    assert "input" in result.output.lower() or "Missing" in result.output


def test_qc_requires_output(runner, tmp_path):
    mag_dir = tmp_path / "mags"
    mag_dir.mkdir()
    result = runner.invoke(main, ["qc", "-i", str(mag_dir)])
    assert result.exit_code != 0


def test_qc_invalid_step(runner, tmp_path):
    mag_dir = tmp_path / "mags"
    mag_dir.mkdir()
    out_dir = tmp_path / "out"
    result = runner.invoke(main, [
        "qc", "-i", str(mag_dir), "-o", str(out_dir),
        "--steps", "bogus_step", "--dry-run"
    ])
    assert result.exit_code != 0
    assert "Invalid" in result.output or "bogus_step" in result.output


def test_db_status_subcommand(runner):
    result = runner.invoke(main, ["db", "status"])
    assert result.exit_code == 0
