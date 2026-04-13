from __future__ import annotations
import copy
from pathlib import Path
import yaml

VALID_STEPS = {"genome_stats", "checkm2", "gtdbtk", "dereplicate"}

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_DEFAULT_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.yaml"


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

    # Resolve db_dir to absolute path relative to project root
    db_dir = Path(cfg.get("db_dir", "databases"))
    if not db_dir.is_absolute():
        db_dir = _PROJECT_ROOT / db_dir
    cfg["db_dir"] = str(db_dir)

    # Resolve per-tool database paths: if null, default to db_dir/<tool>
    for tool in ("checkm2", "gtdbtk"):
        key = f"{tool}_db_path"
        val = cfg.get(key)
        if val:
            p = Path(val)
            if not p.is_absolute():
                cfg[key] = str(_PROJECT_ROOT / p)
        else:
            cfg[key] = str(db_dir / tool)

    return cfg
