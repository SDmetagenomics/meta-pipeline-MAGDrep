from __future__ import annotations
import copy
import os
from pathlib import Path
import yaml

VALID_STEPS = {"genome_stats", "checkm1", "checkm2", "gtdbtk", "dereplicate"}

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.yaml"

# Environment variable for a shared/external database directory.
# Set to the absolute path of your `meta-pipeline-MAGDrep-db` folder:
#   export MAGDREP_DB_DIR=/shared/lab/meta-pipeline-MAGDrep-db
DB_DIR_ENV_VAR = "MAGDREP_DB_DIR"


def _persistent_config_paths() -> list[Path]:
    """Locations (highest-priority first) where persistent db config can live.

    Conda-env scoped first — a lab admin running `db update --db-dir X` once
    configures the location for everyone else sharing that env. Falls back
    to a user-scoped config in XDG_CONFIG_HOME.
    """
    paths: list[Path] = []
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        paths.append(Path(conda_prefix) / "etc" / "meta-pipeline-MAGDrep" / "db_config.yaml")
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    paths.append(Path(xdg) / "meta-pipeline-MAGDrep" / "db_config.yaml")
    return paths


def _read_persistent_db_config() -> tuple[Path | None, Path | None]:
    """Return (db_dir, source_file) for the first readable persistent config,
    or (None, None) if no config is found."""
    for path in _persistent_config_paths():
        if path.exists():
            try:
                with open(path) as f:
                    data = yaml.safe_load(f) or {}
                db_dir = data.get("db_dir")
                if db_dir:
                    return Path(db_dir).expanduser(), path
            except (OSError, yaml.YAMLError):
                continue
    return None, None


def write_persistent_db_config(db_dir: str | Path) -> Path:
    """Persist the chosen db_dir so future invocations (same env) find it.

    Writes to the first location in `_persistent_config_paths()` that we
    can write to — conda-env-scoped if available, user-scoped otherwise.
    Returns the path written.
    """
    last_err: Exception | None = None
    for path in _persistent_config_paths():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w") as f:
                yaml.safe_dump({"db_dir": str(Path(db_dir).resolve())}, f)
            return path
        except OSError as err:
            last_err = err
            continue
    raise OSError(f"Could not write persistent db config: {last_err}")


def resolve_db_dir(
    explicit: str | Path | None = None,
) -> tuple[Path, str]:
    """Resolve the database directory and report where the value came from.

    Priority:
      1. Explicit argument (--db-dir flag or config file)
      2. $MAGDREP_DB_DIR environment variable
      3. Persistent config (conda env first, then user XDG config)
      4. Project-local "databases/" directory
    """
    if explicit:
        p = Path(explicit)
        return (p if p.is_absolute() else _PROJECT_ROOT / p), "explicit"

    env_val = os.environ.get(DB_DIR_ENV_VAR)
    if env_val:
        return Path(env_val).expanduser(), f"${DB_DIR_ENV_VAR}"

    persisted, source = _read_persistent_db_config()
    if persisted:
        return persisted, f"persistent config ({source})"

    return _PROJECT_ROOT / "databases", "project default"


class ConfigError(ValueError):
    pass


def load_config(path: Path) -> dict:
    """Load a YAML config file and return as dict."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def merge_config(default: dict, user: dict) -> dict:
    """
    Deep-merge user config into default config.
    User values override defaults; nested dicts are merged recursively.
    """
    result = copy.deepcopy(default)
    for key, value in user.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    return result


def validate_config(cfg: dict) -> None:
    """Raise ConfigError if any config value is invalid."""
    steps = cfg.get("steps", [])
    invalid = set(steps) - VALID_STEPS
    if invalid:
        raise ConfigError(f"Invalid step(s): {invalid}. Valid steps: {VALID_STEPS}")

    batch_size = cfg.get("batch_size", 1000)
    if not isinstance(batch_size, int) or batch_size < 1:
        raise ConfigError(f"batch_size must be a positive integer, got: {batch_size}")


def load_and_merge_config(
    user_config_path: Path | None = None, overrides: dict | None = None
) -> dict:
    """
    Load default config, optionally merge a user config file, then apply
    any key=value overrides. Returns validated merged config.
    """
    default = load_config(_DEFAULT_CONFIG_PATH)
    cfg = default

    if user_config_path is not None:
        user = load_config(user_config_path)
        cfg = merge_config(cfg, user)

    if overrides:
        cfg = merge_config(cfg, overrides)

    validate_config(cfg)

    # Resolve db_dir: explicit config > MAGDREP_DB_DIR env var > default "databases/"
    explicit = cfg.get("db_dir")
    # Treat the literal shipped default as "not explicit" so the env var wins
    if explicit == "databases":
        explicit = None
    db_dir, _source = resolve_db_dir(explicit)
    cfg["db_dir"] = str(db_dir)

    # Resolve per-tool database paths: if null, default to db_dir/<tool>
    for tool in ("checkm1", "checkm2", "gtdbtk"):
        key = f"{tool}_db_path"
        val = cfg.get(key)
        if val:
            p = Path(val)
            if not p.is_absolute():
                cfg[key] = str(_PROJECT_ROOT / p)
        else:
            cfg[key] = str(db_dir / tool)

    return cfg
