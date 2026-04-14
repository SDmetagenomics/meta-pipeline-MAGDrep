import pytest
import yaml
from pathlib import Path
from meta_pipeline_magdrep.config import (
    load_config, validate_config, merge_config,
    load_and_merge_config, ConfigError, VALID_STEPS,
    resolve_db_dir, DB_DIR_ENV_VAR,
)

CONFIG_YAML = Path(__file__).parent.parent / "config" / "config.yaml"


def test_valid_steps_contains_all_expected():
    expected = {"genome_stats", "checkm2", "gtdbtk", "dereplicate"}
    assert VALID_STEPS == expected


def test_default_config_yaml_is_valid_yaml():
    with open(CONFIG_YAML) as f:
        cfg = yaml.safe_load(f)
    assert isinstance(cfg, dict)


def test_load_config_returns_dict(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("outdir: test_out\n")
    cfg = load_config(cfg_file)
    assert cfg["outdir"] == "test_out"


def test_load_config_nonexistent_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_config(tmp_path / "nonexistent.yaml")


def test_merge_config_user_overrides_default():
    default = {"outdir": "results", "batch_size": 1000}
    user = {"batch_size": 500}
    merged = merge_config(default, user)
    assert merged["batch_size"] == 500
    assert merged["outdir"] == "results"


def test_merge_config_nested_merge():
    default = {"quality_filter": {"high_completeness": 90.0, "high_contamination": 5.0}}
    user = {"quality_filter": {"high_completeness": 95.0}}
    merged = merge_config(default, user)
    assert merged["quality_filter"]["high_completeness"] == 95.0
    assert merged["quality_filter"]["high_contamination"] == 5.0


def test_validate_config_valid():
    cfg = {
        "steps": ["genome_stats", "checkm2", "gtdbtk", "dereplicate"],
        "batch_size": 1000,
        "fasta_extensions": [".fna"],
    }
    validate_config(cfg)  # should not raise


def test_validate_config_invalid_step():
    cfg = {"steps": ["checkm2", "bogus_step"], "batch_size": 1000}
    with pytest.raises(ConfigError, match="bogus_step"):
        validate_config(cfg)


def test_validate_config_invalid_batch_size():
    cfg = {"steps": ["checkm2"], "batch_size": 0}
    with pytest.raises(ConfigError, match="batch_size"):
        validate_config(cfg)


def test_load_and_merge_config_returns_validated():
    cfg = load_and_merge_config()
    assert "steps" in cfg
    assert "quality_filter" in cfg


def test_resolve_db_dir_explicit_wins(monkeypatch):
    """Explicit path beats env var beats default."""
    monkeypatch.setenv(DB_DIR_ENV_VAR, "/tmp/from-env")
    path, source = resolve_db_dir("/tmp/from-arg")
    assert str(path) == "/tmp/from-arg"
    assert source == "explicit"


def test_resolve_db_dir_env_var(monkeypatch, tmp_path):
    """Env var is used when no explicit path is given (and no persistent cfg)."""
    monkeypatch.setenv(DB_DIR_ENV_VAR, "/tmp/shared-db-location")
    # Isolate from any real user/conda persistent config
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path, source = resolve_db_dir()
    assert str(path) == "/tmp/shared-db-location"
    assert source.startswith("$")


def test_resolve_db_dir_default(monkeypatch, tmp_path):
    """Falls back to project-relative databases/ when nothing else is set."""
    monkeypatch.delenv(DB_DIR_ENV_VAR, raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    path, source = resolve_db_dir()
    assert str(path).endswith("databases")
    assert source == "project default"


def test_resolve_db_dir_from_persistent_config(monkeypatch, tmp_path):
    """Persistent config takes precedence over the project default but
    is overridden by env var / explicit arg."""
    from pathlib import Path as _P
    from meta_pipeline_magdrep.config import write_persistent_db_config
    monkeypatch.delenv(DB_DIR_ENV_VAR, raising=False)
    monkeypatch.delenv("CONDA_PREFIX", raising=False)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    target = tmp_path / "lab-shared-dbs"
    target.mkdir()
    write_persistent_db_config(target)
    path, source = resolve_db_dir()
    # write_persistent_db_config stores the resolved absolute path
    assert path == _P(target).resolve()
    assert "persistent" in source


def test_load_and_merge_config_honors_env_var(monkeypatch):
    """load_and_merge_config should pick up MAGDREP_DB_DIR when config
    doesn't override db_dir explicitly."""
    monkeypatch.setenv(DB_DIR_ENV_VAR, "/tmp/lab-db")
    cfg = load_and_merge_config()
    assert cfg["db_dir"] == "/tmp/lab-db"
    assert cfg["checkm2_db_path"] == "/tmp/lab-db/checkm2"
    assert cfg["gtdbtk_db_path"] == "/tmp/lab-db/gtdbtk"
