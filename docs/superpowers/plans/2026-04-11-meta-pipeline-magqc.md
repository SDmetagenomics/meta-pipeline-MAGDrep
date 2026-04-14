# meta-pipeline-MAGQC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a modular Snakemake pipeline for quality assessment and taxonomic classification of MAGs at scale, mirroring the architecture of meta-pipeline-ORFanno.

**Architecture:** Snakemake orchestrates per-MAG genome stats and batch-mode QC tools (CheckM2, GUNC, GTDB-Tk). Results are left-joined into a combined report with quality tiers, then optionally dereplicated via skani. Python Click CLI dispatches to Snakemake via API (local) or CLI (SLURM).

**Tech Stack:** Python 3.11+, Snakemake 8/9, Click, PyYAML, SeqKit (with BioPython fallback), CheckM2, GUNC, GTDB-Tk, skani

---

## File Structure

```
meta-pipeline-MAGQC/
├── meta-pipeline-MAGQC              # Bash shim launcher (executable)
├── Snakefile                        # Master Snakemake orchestrator
├── pyproject.toml                   # Package metadata and deps
├── README.md
├── mkdocs.yml
├── config/
│   ├── config.yaml                  # Default config
│   └── profiles/
│       ├── local/config.yaml
│       └── slurm/config.yaml
├── rules/
│   ├── common.smk                   # MAG discovery, batching, symlinks
│   ├── genome_stats.smk             # Per-MAG: SeqKit assembly stats
│   ├── checkm2.smk                  # Batch: completeness/contamination
│   ├── gunc.smk                     # Batch: chimerism detection
│   ├── gtdbtk.smk                   # Batch: taxonomy classification
│   ├── aggregate.smk                # Merge + quality tier assignment
│   └── dereplicate.smk              # Species-level dereplication
├── scripts/
│   ├── __init__.py
│   ├── genome_stats.py              # SeqKit wrapper + N50 + BioPython fallback
│   ├── run_checkm2.py               # CheckM2 predict batch runner
│   ├── run_gunc.py                  # GUNC batch runner
│   ├── run_gtdbtk.py                # GTDB-Tk classify_wf batch runner
│   ├── merge_reports.py             # Left-join + quality tiers
│   └── dereplicate.py               # skani triangle + greedy clustering
├── src/meta_pipeline_magqc/
│   ├── __init__.py                  # __version__ = "0.1.0"
│   ├── cli.py                       # Click CLI entry point
│   ├── config.py                    # YAML load/merge/validate
│   ├── runner.py                    # Snakemake API/CLI dispatch
│   └── resources.py                 # CPU/RAM/GPU detection
├── container/
│   ├── environment.yml
│   └── Dockerfile
├── tests/
│   ├── conftest.py
│   ├── data/mags/                   # Synthetic test FASTAs
│   ├── test_config.py
│   ├── test_cli.py
│   ├── test_runner.py
│   ├── test_genome_stats.py
│   ├── test_checkm2.py
│   ├── test_gunc.py
│   ├── test_gtdbtk.py
│   ├── test_merge_reports.py
│   ├── test_dereplicate.py
│   └── test_integration.py
└── docs/
    ├── index.md
    ├── quickstart.md
    ├── installation.md
    ├── usage/
    │   ├── inputs-outputs.md
    │   └── configuration.md
    ├── pipeline/
    │   ├── overview.md
    │   ├── genome-stats.md
    │   ├── checkm2.md
    │   ├── gunc.md
    │   ├── gtdbtk.md
    │   └── dereplicate.md
    └── outputs/
        └── combined-report.md
```

---

### Task 1: Project Scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `meta-pipeline-MAGQC` (bash shim)
- Create: `src/meta_pipeline_magqc/__init__.py`
- Create: `scripts/__init__.py`
- Create: `tests/__init__.py` (empty, not needed but harmless)
- Create: `tests/data/mags/synthetic_mag_001.fna`
- Create: `tests/data/mags/synthetic_mag_002.fna`
- Create: `tests/data/mags/synthetic_mag_003.fa.gz`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "meta-pipeline-MAGQC"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "snakemake>=8.0",
    "pyyaml>=6.0",
]

[project.scripts]
meta-pipeline-MAGQC = "meta_pipeline_magqc.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
markers = ["slow: marks tests as slow (requires installed tools and databases)"]
```

- [ ] **Step 2: Create bash shim launcher**

File: `meta-pipeline-MAGQC` (executable, no extension)

```bash
#!/usr/bin/env bash
# meta-pipeline-MAGQC launcher
# Thin shim that delegates to the Python CLI entry point.
set -euo pipefail

exec python -m meta_pipeline_magqc.cli "$@"
```

Run: `chmod +x meta-pipeline-MAGQC`

- [ ] **Step 3: Create __init__.py files**

`src/meta_pipeline_magqc/__init__.py`:
```python
__version__ = "0.1.0"
```

`scripts/__init__.py`:
```python
```

- [ ] **Step 4: Create synthetic test FASTA files**

Create 3 synthetic MAG FASTAs in `tests/data/mags/`. Each should have 3-5 contigs of varying length (1000-5000 bp) with realistic GC content. These are used for genome_stats unit tests only.

`tests/data/mags/synthetic_mag_001.fna`:
```
>contig_1 length=3000
ATGCGTACGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCG
ATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGA
TCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGATCGAT
...
```

Generate these programmatically with a small Python script:

```python
# Run once to generate test data
import random
import gzip
from pathlib import Path

random.seed(42)
out = Path("tests/data/mags")
out.mkdir(parents=True, exist_ok=True)

def make_seq(length):
    return "".join(random.choices("ATCG", k=length))

def write_fasta(path, contigs, compress=False):
    opener = gzip.open if compress else open
    mode = "wt" if compress else "w"
    with opener(path, mode) as f:
        for name, seq in contigs:
            f.write(f">{name}\n")
            for i in range(0, len(seq), 80):
                f.write(seq[i:i+80] + "\n")

# MAG 001: 4 contigs, total ~12kb
write_fasta(out / "synthetic_mag_001.fna", [
    ("contig_1", make_seq(5000)),
    ("contig_2", make_seq(3000)),
    ("contig_3", make_seq(2500)),
    ("contig_4", make_seq(1500)),
])

# MAG 002: 3 contigs, total ~9kb
write_fasta(out / "synthetic_mag_002.fna", [
    ("contig_1", make_seq(4000)),
    ("contig_2", make_seq(3000)),
    ("contig_3", make_seq(2000)),
])

# MAG 003: 5 contigs, gzipped .fa.gz, total ~15kb
write_fasta(out / "synthetic_mag_003.fa.gz", [
    ("contig_1", make_seq(5000)),
    ("contig_2", make_seq(4000)),
    ("contig_3", make_seq(3000)),
    ("contig_4", make_seq(2000)),
    ("contig_5", make_seq(1000)),
], compress=True)
```

- [ ] **Step 5: Create all required directories**

```bash
mkdir -p src/meta_pipeline_magqc
mkdir -p scripts
mkdir -p config/profiles/local
mkdir -p config/profiles/slurm
mkdir -p rules
mkdir -p tests/data/mags
mkdir -p container
mkdir -p docs/usage docs/pipeline docs/outputs
```

- [ ] **Step 6: Verify scaffold**

Run: `ls -R` to confirm the directory tree matches the spec.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "feat: project scaffold with pyproject.toml, bash shim, test data"
```

---

### Task 2: Config Module

**Files:**
- Create: `src/meta_pipeline_magqc/config.py`
- Create: `tests/test_config.py`
- Create: `config/config.yaml`

- [ ] **Step 1: Write failing tests for config module**

`tests/test_config.py`:
```python
import pytest
import yaml
from pathlib import Path
from meta_pipeline_magqc.config import (
    load_config, validate_config, merge_config,
    load_and_merge_config, ConfigError, VALID_STEPS,
)

CONFIG_YAML = Path(__file__).parent.parent / "config" / "config.yaml"


def test_valid_steps_contains_all_expected():
    expected = {"genome_stats", "checkm2", "gunc", "gtdbtk", "dereplicate"}
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
        "steps": ["genome_stats", "checkm2", "gunc", "gtdbtk", "dereplicate"],
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/sdiamond/Dropbox/Informatics/Dev/Claude_Projects/meta-pipeline-MAGQC && python -m pytest tests/test_config.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'meta_pipeline_magqc'`

- [ ] **Step 3: Create config/config.yaml**

```yaml
# meta-pipeline-MAGQC default configuration
# Override any value by passing --config key=value on the CLI

# Output directory
outdir: results

# Steps to run (all enabled by default)
# Valid values: genome_stats, checkm2, gunc, gtdbtk, dereplicate
steps:
  - genome_stats
  - checkm2
  - gunc
  - gtdbtk
  - dereplicate

# Compute resources (auto = detect at runtime)
threads_per_job: auto
max_parallel_jobs: auto

# Batching: number of genomes per batch for batch-mode tools
# (CheckM2, GUNC, GTDB-Tk). Keeps memory bounded for 10k+ datasets.
batch_size: 1000

# Input FASTA extensions to discover in the input directory
fasta_extensions:
  - .fasta
  - .fa
  - .fna
  - .fasta.gz
  - .fa.gz
  - .fna.gz

# Database directory (relative to working directory or absolute)
db_dir: databases

# Optional: paths to pre-existing databases (null = expect in db_dir)
checkm2_db_path: null
gunc_db_path: null
gtdbtk_db_path: null

# Pinned database versions
db_versions:
  checkm2: "1.0.2"
  gunc: "gtdb_214"
  gtdbtk: "r226"

# GTDB-Tk specific options
gtdbtk:
  skip_ani_screen: false
  # pplacer is single-threaded per placement; keep at 1 to avoid
  # memory multiplication (each pplacer thread needs ~85 GB)
  pplacer_cpus: 1

# GUNC specific options
gunc:
  # Reference database type: progenomes, gtdb_214, or path to custom DB
  db_type: "gtdb_214"

# Quality filter thresholds
# These control the quality_tier column in combined_report.tsv
# and which genomes appear in filtered_report.tsv
quality_filter:
  # --- MIMAG-style thresholds ---
  high_completeness: 90.0
  high_contamination: 5.0
  medium_completeness: 60.0
  medium_contamination: 10.0
  # --- GTDB quality score: completeness - 5*contamination ---
  min_quality_score: 50.0
  # --- GUNC chimerism ---
  gunc_css_threshold: 0.45
  # --- Default tier for filtered_report.tsv ---
  # Genomes at or above this tier are included in the filtered report.
  # Options: high_quality, medium_quality
  default_filter: medium_quality

# Dereplication settings (skani-based species clustering)
# Only genomes passing the default_filter are included in dereplication.
dereplicate:
  # ANI threshold for species-level clustering (%)
  ani_threshold: 95.0
  # Minimum bi-directional aligned fraction (%).
  # Both AF(query->ref) and AF(ref->query) must exceed this value.
  min_af: 10.0
  # Composite quality score weights for selecting cluster representatives.
  # Score = w_qscore * norm(quality_score)
  #       + w_completeness * norm(completeness)
  #       + w_n50 * norm(log10(N50))
  #       + w_contam * norm(100 - contamination)
  #       + w_gunc * norm(1 - CSS)
  # Higher composite score = better representative.
  score_weights:
    w_qscore: 1.0
    w_completeness: 1.0
    w_n50: 0.5
    w_contam: 0.5
    w_gunc: 0.5
```

- [ ] **Step 4: Implement config.py**

`src/meta_pipeline_magqc/config.py`:
```python
from __future__ import annotations
import copy
from pathlib import Path
import yaml

VALID_STEPS = {"genome_stats", "checkm2", "gunc", "gtdbtk", "dereplicate"}

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
        cfg["db_dir"] = str(_PROJECT_ROOT / db_dir)

    return cfg
```

- [ ] **Step 5: Run tests and verify they pass**

Run: `cd /Users/sdiamond/Dropbox/Informatics/Dev/Claude_Projects/meta-pipeline-MAGQC && python -m pytest tests/test_config.py -v`

Expected: All 10 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add src/meta_pipeline_magqc/config.py config/config.yaml tests/test_config.py
git commit -m "feat: config module with load, merge, validate, and default config.yaml"
```

---

### Task 3: Resources Module

**Files:**
- Create: `src/meta_pipeline_magqc/resources.py`

- [ ] **Step 1: Create resources.py**

Copy directly from ORFanno — identical module, no changes needed.

`src/meta_pipeline_magqc/resources.py`:
```python
from __future__ import annotations
import os
import subprocess
from dataclasses import dataclass


@dataclass
class ResourceInfo:
    cpu_count: int
    gpu_available: bool
    gpu_type: str          # "cuda" | "mps" | "none"
    gpu_device_count: int


def detect_cpu_count() -> int:
    """Return number of logical CPUs available."""
    return os.cpu_count() or 1


def detect_gpu() -> dict:
    """
    Detect GPU availability.
    Checks NVIDIA CUDA first, then Apple MPS, then falls back to none.
    """
    # Check NVIDIA CUDA via nvidia-smi
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            devices = [line.strip() for line in result.stdout.strip().splitlines() if line.strip()]
            if devices:
                return {"available": True, "type": "cuda", "device_count": len(devices)}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # Check Apple Silicon MPS via torch if available
    try:
        import torch  # type: ignore
        if torch.backends.mps.is_available():
            return {"available": True, "type": "mps", "device_count": 1}
    except ImportError:
        pass

    # Fallback: detect Apple Silicon via system_profiler
    try:
        import platform
        if platform.system() == "Darwin" and platform.processor() == "arm":
            result = subprocess.run(
                ["system_profiler", "SPDisplaysDataType"],
                capture_output=True, text=True, timeout=5
            )
            if "Apple M" in result.stdout:
                return {"available": True, "type": "mps", "device_count": 1}
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    return {"available": False, "type": "none", "device_count": 0}


def detect_resources() -> ResourceInfo:
    """Detect all available compute resources."""
    cpu_count = detect_cpu_count()
    gpu_info = detect_gpu()
    return ResourceInfo(
        cpu_count=cpu_count,
        gpu_available=gpu_info["available"],
        gpu_type=gpu_info["type"],
        gpu_device_count=gpu_info["device_count"],
    )
```

- [ ] **Step 2: Commit**

```bash
git add src/meta_pipeline_magqc/resources.py
git commit -m "feat: resources module for CPU/GPU detection"
```

---

### Task 4: Runner Module

**Files:**
- Create: `src/meta_pipeline_magqc/runner.py`
- Create: `tests/test_runner.py`

- [ ] **Step 1: Write failing tests**

`tests/test_runner.py`:
```python
import pytest
from pathlib import Path
from meta_pipeline_magqc.runner import build_snakemake_config


@pytest.fixture
def sample_config():
    return {
        "outdir": "results",
        "steps": ["genome_stats", "checkm2"],
        "batch_size": 1000,
        "max_parallel_jobs": 4,
    }


def test_build_snakemake_config_includes_input_dir(tmp_path, sample_config):
    snk_cfg = build_snakemake_config(input_dir=tmp_path, config=sample_config)
    assert snk_cfg["input_dir"] == str(tmp_path)


def test_build_snakemake_config_includes_all_keys(tmp_path, sample_config):
    snk_cfg = build_snakemake_config(input_dir=tmp_path, config=sample_config)
    for key in ("outdir", "steps", "batch_size"):
        assert key in snk_cfg, f"Missing key: {key}"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_runner.py -v`

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement runner.py**

`src/meta_pipeline_magqc/runner.py`:
```python
from __future__ import annotations
import sys
from pathlib import Path
import click

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_SNAKEFILE = _PROJECT_ROOT / "Snakefile"
_PROFILES_DIR = _PROJECT_ROOT / "config" / "profiles"


def build_snakemake_config(input_dir: Path, config: dict) -> dict:
    """Build the config dict passed to Snakemake."""
    snk_config = dict(config)
    snk_config["input_dir"] = str(input_dir)
    return snk_config


def run_snakemake(
    input_dir: Path,
    config: dict,
    profile: str = "local",
    dry_run: bool = False,
) -> None:
    """
    Invoke Snakemake via its Python API (local) or CLI (SLURM).

    For local execution, runs all jobs in-process using the local executor.
    For SLURM, delegates to snakemake CLI with the SLURM profile so that
    Snakemake handles job submission, grouping, and resource allocation.
    """
    snk_config = build_snakemake_config(input_dir=input_dir, config=config)

    if profile != "local":
        _run_snakemake_cli(snk_config, profile, dry_run, config)
    else:
        _run_snakemake_api(snk_config, config, dry_run)


def _run_snakemake_api(snk_config: dict, config: dict, dry_run: bool) -> None:
    """Run Snakemake in-process via the Python API (local executor)."""
    try:
        from snakemake.api import SnakemakeApi
        from snakemake.settings.types import (
            ConfigSettings,
            DAGSettings,
            DeploymentSettings,
            ExecutionSettings,
            OutputSettings,
            ResourceSettings,
            StorageSettings,
            WorkflowSettings,
        )
    except ImportError:
        click.echo("Error: Snakemake is not installed. Run: pip install snakemake", err=True)
        sys.exit(1)

    cores = config.get("max_parallel_jobs", 1)

    try:
        with SnakemakeApi(OutputSettings(printshellcmds=True, verbose=False)) as api:
            workflow = api.workflow(
                snakefile=_SNAKEFILE,
                workdir=_PROJECT_ROOT,
                resource_settings=ResourceSettings(cores=cores, nodes=cores),
                config_settings=ConfigSettings(config=snk_config),
                storage_settings=StorageSettings(),
                workflow_settings=WorkflowSettings(),
                deployment_settings=DeploymentSettings(),
            )
            dag = workflow.dag(dag_settings=DAGSettings())
            executor = "dryrun" if dry_run else "local"
            dag.execute_workflow(executor=executor)
    except SystemExit as e:
        if e.code != 0:
            raise
    except Exception as e:
        click.echo(f"Snakemake error: {e}", err=True)
        raise


def _run_snakemake_cli(
    snk_config: dict, profile: str, dry_run: bool, config: dict
) -> None:
    """Run Snakemake via CLI subprocess with a cluster profile."""
    import subprocess

    profile_dir = _PROFILES_DIR / profile
    if not profile_dir.exists():
        click.echo(f"Error: Profile '{profile}' not found at {profile_dir}", err=True)
        sys.exit(1)

    cmd = [
        "snakemake",
        "--snakefile", str(_SNAKEFILE),
        "--directory", str(_PROJECT_ROOT),
        "--profile", str(profile_dir),
    ]

    config_args = []
    for k, v in snk_config.items():
        if isinstance(v, list):
            config_args.append(f"{k}={v}")
        else:
            config_args.append(f"{k}={v}")
    if config_args:
        cmd.extend(["--config"] + config_args)

    cores_per_node = config.get("slurm_cores_per_node", 64)
    cmd.extend(["--cores", str(cores_per_node)])

    if dry_run:
        cmd.append("--dry-run")

    click.echo(f"Running Snakemake with {profile} profile...")
    result = subprocess.run(cmd, cwd=_PROJECT_ROOT)
    if result.returncode != 0:
        click.echo(f"Snakemake error: exited with code {result.returncode}", err=True)
        sys.exit(result.returncode)
```

- [ ] **Step 4: Run tests and verify they pass**

Run: `python -m pytest tests/test_runner.py -v`

Expected: All 2 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/meta_pipeline_magqc/runner.py tests/test_runner.py
git commit -m "feat: runner module for Snakemake API/CLI dispatch"
```

---

### Task 5: CLI Module

**Files:**
- Create: `src/meta_pipeline_magqc/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

`tests/test_cli.py`:
```python
import pytest
from click.testing import CliRunner
from meta_pipeline_magqc.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_version_flag(runner):
    result = runner.invoke(main, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.output


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cli.py -v`

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement cli.py**

`src/meta_pipeline_magqc/cli.py`:
```python
from __future__ import annotations
import sys
from pathlib import Path
import click
from meta_pipeline_magqc import __version__
from meta_pipeline_magqc.config import load_and_merge_config, VALID_STEPS, ConfigError
from meta_pipeline_magqc.resources import detect_resources

VALID_PROFILES = {"local", "slurm"}


@click.group()
@click.version_option(version=__version__)
def main():
    """meta-pipeline-MAGQC: quality assessment and taxonomy of MAGs at scale."""
    pass


@main.command()
@click.option("--input", "-i", "input_dir", required=True,
              type=click.Path(exists=True, file_okay=False, path_type=Path),
              help="Directory of input MAG FASTA files.")
@click.option("--output", "-o", "output_dir", required=True,
              type=click.Path(path_type=Path),
              help="Output directory.")
@click.option("--profile", default="local", show_default=True,
              type=click.Choice(list(VALID_PROFILES)),
              help="Execution profile: local or slurm.")
@click.option("--steps", default=None,
              help="Comma-separated steps to run (e.g. checkm2,gtdbtk). Default: all.")
@click.option("--skip", default=None,
              help="Comma-separated steps to skip (e.g. gunc).")
@click.option("--config", "config_file", default=None,
              type=click.Path(exists=True, path_type=Path),
              help="Path to a custom config YAML.")
@click.option("--dry-run", is_flag=True, default=False,
              help="Show what would be run without executing.")
@click.option("--jobs", "-j", default=None, type=int,
              help="Maximum parallel jobs. Overrides config.")
def qc(input_dir, output_dir, profile, steps, skip, config_file, dry_run, jobs):
    """Run quality assessment on a directory of MAG FASTA files."""
    overrides = {"outdir": str(output_dir)}
    if jobs:
        overrides["max_parallel_jobs"] = jobs

    try:
        cfg = load_and_merge_config(config_file, overrides)
    except ConfigError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    # Resolve which steps to run
    active_steps = set(cfg["steps"])
    if steps:
        requested = set(s.strip() for s in steps.split(","))
        invalid = requested - VALID_STEPS
        if invalid:
            click.echo(f"Error: Invalid step(s): {invalid}", err=True)
            sys.exit(1)
        active_steps = requested
    if skip:
        to_skip = set(s.strip() for s in skip.split(","))
        active_steps -= to_skip

    cfg["steps"] = sorted(active_steps)

    # Detect and resolve resources
    resources = detect_resources()
    if cfg["threads_per_job"] == "auto":
        cfg["threads_per_job"] = min(resources.cpu_count, 8)
    if cfg["max_parallel_jobs"] == "auto":
        cfg["max_parallel_jobs"] = max(1, resources.cpu_count // cfg["threads_per_job"])

    from meta_pipeline_magqc.runner import run_snakemake
    run_snakemake(
        input_dir=input_dir,
        config=cfg,
        profile=profile,
        dry_run=dry_run,
    )


@main.group()
def db():
    """Manage reference databases."""
    pass


@db.command("update")
@click.option("--db-dir", default="databases", show_default=True,
              type=click.Path(path_type=Path),
              help="Directory to download databases into.")
@click.option("--force", is_flag=True, default=False,
              help="Re-download even if already present.")
def db_update(db_dir, force):
    """Download required databases (CheckM2, GUNC, GTDB-Tk)."""
    click.echo("Database download not yet implemented.")
    click.echo("Please download manually:")
    click.echo("  CheckM2: checkm2 database --download --path <db_dir>")
    click.echo("  GUNC: gunc download_db <db_dir> -db gtdb_214")
    click.echo("  GTDB-Tk: download-db.sh <db_dir>")


@db.command("status")
@click.option("--db-dir", default="databases", show_default=True,
              type=click.Path(path_type=Path),
              help="Database directory to inspect.")
def db_status(db_dir):
    """Show installed database versions."""
    project_root = Path(__file__).parent.parent.parent
    db_path = Path(db_dir)
    if not db_path.is_absolute():
        db_path = project_root / db_path
    click.echo(f"Checking databases in: {db_path}")
    if not db_path.exists():
        click.echo("  No databases directory found.")
        return
    for child in sorted(db_path.iterdir()):
        if child.is_dir():
            click.echo(f"  {child.name}: present")
```

- [ ] **Step 4: Run tests and verify they pass**

Run: `python -m pytest tests/test_cli.py -v`

Expected: All 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/meta_pipeline_magqc/cli.py tests/test_cli.py
git commit -m "feat: Click CLI with qc and db subcommands"
```

---

### Task 6: Config Profiles

**Files:**
- Create: `config/profiles/local/config.yaml`
- Create: `config/profiles/slurm/config.yaml`

- [ ] **Step 1: Create local profile**

`config/profiles/local/config.yaml`:
```yaml
# Local profile: run everything on the current machine.
printshellcmds: true
keep-going: true
rerun-incomplete: true
```

- [ ] **Step 2: Create SLURM profile**

`config/profiles/slurm/config.yaml`:
```yaml
# SLURM profile for meta-pipeline-MAGQC
#
# Designed for nodes with 64 cores and 512 GB RAM.
# Snakemake runs locally within each node, packing multiple rule-jobs.
#
# Usage:
#   meta-pipeline-MAGQC qc -i mags/ -o results/ --profile slurm
#
# To customize for your cluster:
#   meta-pipeline-MAGQC qc -i mags/ -o results/ --profile slurm \
#     --config slurm_partition=mypartition slurm_cores_per_node=64

executor: slurm
jobs: 60
keep-going: true
rerun-incomplete: true
printshellcmds: true
latency-wait: 60

default-resources:
  slurm_partition: "normal"
  mem_mb: 64000
  runtime: 120
  nodes: 1
  tasks: 1

set-resources:
  genome_stats:
    runtime: 5
    mem_mb: 4000
  checkm2_batch:
    runtime: 240
    mem_mb: 32000
  gunc_batch:
    runtime: 120
    mem_mb: 32000
  gtdbtk_batch:
    runtime: 480
    mem_mb: 120000
  merge_reports:
    runtime: 10
    mem_mb: 8000
  skani_triangle:
    runtime: 120
    mem_mb: 64000
  dereplicate_cluster:
    runtime: 30
    mem_mb: 16000

group-components: 4
```

- [ ] **Step 3: Commit**

```bash
git add config/profiles/
git commit -m "feat: local and SLURM execution profiles"
```

---

### Task 7: Snakemake Common Helpers (rules/common.smk)

**Files:**
- Create: `rules/common.smk`

- [ ] **Step 1: Implement common.smk**

`rules/common.smk`:
```python
from pathlib import Path


def discover_mag_ids(input_dir):
    """Return sorted list of MAG IDs from FASTA files in input_dir."""
    patterns = ["*.fasta", "*.fa", "*.fna", "*.fasta.gz", "*.fa.gz", "*.fna.gz"]
    paths = []
    for pattern in patterns:
        paths.extend(Path(input_dir).glob(pattern))
    ids = []
    for p in paths:
        name = p.name
        for suffix in (".fasta.gz", ".fa.gz", ".fna.gz", ".fasta", ".fna", ".fa"):
            if name.endswith(suffix):
                ids.append(name[: -len(suffix)])
                break
    return sorted(set(ids))


def mag_fasta(input_dir, mag_id):
    """Return path to FASTA file for a given MAG ID."""
    for suffix in (".fna", ".fasta", ".fa", ".fna.gz", ".fasta.gz", ".fa.gz"):
        candidate = Path(input_dir) / f"{mag_id}{suffix}"
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(f"No FASTA file found for MAG ID: {mag_id}")


def make_batches(mag_ids, batch_size):
    """
    Split MAG IDs into numbered batches.
    Returns dict mapping batch_id strings to lists of MAG IDs.
    E.g. 2500 MAGs with batch_size=1000 ->
      {"batch_000": [...1000...], "batch_001": [...1000...], "batch_002": [...500...]}
    """
    batches = {}
    # Determine zero-padding width: at least 3 digits
    num_batches = max(1, (len(mag_ids) + batch_size - 1) // batch_size)
    width = max(3, len(str(num_batches - 1)))
    for i in range(0, len(mag_ids), batch_size):
        batch_id = f"batch_{str(i // batch_size).zfill(width)}"
        batches[batch_id] = mag_ids[i : i + batch_size]
    return batches


def create_batch_dir(batch_id, mag_ids, input_dir, batch_dir):
    """
    Create a directory of symlinks for a batch.
    For each MAG ID, symlink the original FASTA into batch_dir/.
    """
    import os
    batch_path = Path(batch_dir)
    batch_path.mkdir(parents=True, exist_ok=True)
    for mid in mag_ids:
        src = Path(mag_fasta(input_dir, mid))
        dst = batch_path / src.name
        if not dst.exists():
            os.symlink(src.resolve(), dst)


# Wildcard constraints
wildcard_constraints:
    mag_id="[A-Za-z0-9_.\\-]+",
    batch_id="batch_\\d+",
```

- [ ] **Step 2: Commit**

```bash
git add rules/common.smk
git commit -m "feat: common.smk with MAG discovery, batching, symlink helpers"
```

---

### Task 8: Snakefile Master Orchestrator

**Files:**
- Create: `Snakefile`

- [ ] **Step 1: Create Snakefile**

```python
from pathlib import Path

include: "rules/common.smk"

# --- Configuration ---
INPUT_DIR = Path(config.get("input_dir", "mags"))
OUTDIR = Path(config.get("outdir", "results"))
BATCH_SIZE = int(config.get("batch_size", 1000))
STEPS = set(config.get("steps", []))

# Discover MAG IDs from input directory
MAG_IDS = discover_mag_ids(INPUT_DIR)
if not MAG_IDS:
    raise ValueError(f"No FASTA files found in input directory: {INPUT_DIR}")

# Compute batch assignments
BATCHES = make_batches(MAG_IDS, BATCH_SIZE)
BATCH_IDS = list(BATCHES.keys())  # ["batch_000", "batch_001", ...]

# Always include genome_stats and aggregate
include: "rules/genome_stats.smk"
include: "rules/aggregate.smk"

if "checkm2" in STEPS:
    include: "rules/checkm2.smk"

if "gunc" in STEPS:
    include: "rules/gunc.smk"

if "gtdbtk" in STEPS:
    include: "rules/gtdbtk.smk"

if "dereplicate" in STEPS:
    include: "rules/dereplicate.smk"


def all_outputs():
    """Build the list of expected final outputs based on selected steps."""
    outputs = [str(OUTDIR / "combined_report.tsv")]
    outputs.append(str(OUTDIR / "filtered_report.tsv"))
    if "dereplicate" in STEPS:
        outputs.append(str(OUTDIR / "dereplicated_report.tsv"))
        outputs.append(str(OUTDIR / "species_clusters.tsv"))
    return outputs


rule all:
    input:
        all_outputs()
```

- [ ] **Step 2: Commit**

```bash
git add Snakefile
git commit -m "feat: master Snakefile with conditional step includes and batching"
```

---

### Task 9: Genome Stats (rules + script)

**Files:**
- Create: `rules/genome_stats.smk`
- Create: `scripts/genome_stats.py`
- Create: `tests/test_genome_stats.py`

- [ ] **Step 1: Write failing tests**

`tests/test_genome_stats.py`:
```python
import pytest
from pathlib import Path
from scripts.genome_stats import compute_genome_stats, _compute_n50, write_stats_tsv


def test_compute_n50_simple():
    # Contigs: 100, 200, 300. Total=600, half=300.
    # Sorted desc: 300, 200, 100. Cumsum: 300 >= 300. N50=300.
    assert _compute_n50([100, 200, 300]) == 300


def test_compute_n50_single_contig():
    assert _compute_n50([5000]) == 5000


def test_compute_n50_equal_contigs():
    # 4 x 1000. Total=4000, half=2000. Cumsum: 1000, 2000 >= 2000. N50=1000.
    assert _compute_n50([1000, 1000, 1000, 1000]) == 1000


def test_compute_n50_empty():
    assert _compute_n50([]) == 0


def test_compute_genome_stats_synthetic(tmp_path):
    """Test genome stats on a small synthetic FASTA."""
    fasta = tmp_path / "test_mag.fna"
    # 2 contigs: 100bp and 200bp, all G+C to get GC ~100%
    fasta.write_text(
        ">contig_1\n" + "G" * 100 + "\n"
        ">contig_2\n" + "C" * 200 + "\n"
    )
    stats = compute_genome_stats(fasta)
    assert stats["mag_id"] == "test_mag"
    assert stats["total_length_bp"] == 300
    assert stats["contig_count"] == 2
    assert stats["n50_bp"] == 200
    assert stats["largest_contig_bp"] == 200
    assert stats["gc_percent"] == pytest.approx(100.0, abs=0.1)


def test_compute_genome_stats_mixed_gc(tmp_path):
    """Test GC computation with mixed bases."""
    fasta = tmp_path / "mixed.fna"
    # 1 contig: 50% GC (equal ATGC)
    fasta.write_text(">contig_1\n" + "ATGC" * 50 + "\n")
    stats = compute_genome_stats(fasta)
    assert stats["gc_percent"] == pytest.approx(50.0, abs=0.1)


def test_compute_genome_stats_gzipped(tmp_path):
    """Test that gzipped FASTAs are handled."""
    import gzip
    fasta = tmp_path / "gz_mag.fna.gz"
    with gzip.open(fasta, "wt") as f:
        f.write(">contig_1\n" + "ATGC" * 100 + "\n")
    stats = compute_genome_stats(fasta)
    assert stats["mag_id"] == "gz_mag"
    assert stats["total_length_bp"] == 400


def test_write_stats_tsv(tmp_path):
    """Test TSV output format."""
    stats = {
        "mag_id": "test",
        "total_length_bp": 1000,
        "gc_percent": 45.5,
        "contig_count": 3,
        "n50_bp": 500,
        "largest_contig_bp": 600,
    }
    out = tmp_path / "stats.tsv"
    write_stats_tsv(stats, out)
    lines = out.read_text().strip().split("\n")
    assert len(lines) == 2
    assert lines[0] == "mag_id\ttotal_length_bp\tgc_percent\tcontig_count\tn50_bp\tlargest_contig_bp"
    assert lines[1].startswith("test\t")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_genome_stats.py -v`

Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.genome_stats'`

- [ ] **Step 3: Implement scripts/genome_stats.py**

`scripts/genome_stats.py`:
```python
"""Compute genome-level statistics from a FASTA file.

Primary: SeqKit (fast, Go-based). Fallback: BioPython (pure Python).
Uses shutil.which() to check SeqKit availability at runtime.
"""
from __future__ import annotations
import gzip
import json
import shutil
import subprocess
from pathlib import Path


def _compute_n50(lengths: list[int]) -> int:
    """Return N50 for a list of contig lengths."""
    if not lengths:
        return 0
    lengths = sorted(lengths, reverse=True)
    half_total = sum(lengths) / 2
    cumsum = 0
    for length in lengths:
        cumsum += length
        if cumsum >= half_total:
            return length
    return 0


def _stats_via_seqkit(fasta_path: Path) -> dict:
    """Compute stats using SeqKit (fast path)."""
    fasta_path = Path(fasta_path)

    # Get basic stats
    result = subprocess.run(
        ["seqkit", "stats", "--tabular", str(fasta_path)],
        capture_output=True, text=True, check=True,
    )
    lines = result.stdout.strip().split("\n")
    header = lines[0].split("\t")
    values = lines[1].split("\t")
    seqkit_stats = dict(zip(header, values))

    # Get per-contig GC and lengths
    result = subprocess.run(
        ["seqkit", "fx2tab", "--name", "--only-id", "--gc", "--length", str(fasta_path)],
        capture_output=True, text=True, check=True,
    )
    lengths = []
    gc_weighted_sum = 0.0
    total_length = 0
    for line in result.stdout.strip().split("\n"):
        parts = line.split("\t")
        if len(parts) >= 3:
            length = int(parts[2])
            gc = float(parts[1])
            lengths.append(length)
            gc_weighted_sum += gc * length
            total_length += length

    gc_pct = round(gc_weighted_sum / total_length, 2) if total_length > 0 else 0.0

    return {
        "total_length_bp": total_length,
        "gc_percent": gc_pct,
        "contig_count": len(lengths),
        "n50_bp": _compute_n50(lengths),
        "largest_contig_bp": max(lengths) if lengths else 0,
    }


def _stats_via_biopython(fasta_path: Path) -> dict:
    """Compute stats using BioPython (fallback path)."""
    from Bio import SeqIO
    from Bio.SeqUtils import gc_fraction

    fasta_path = Path(fasta_path)
    opener = gzip.open if fasta_path.suffix == ".gz" else open

    with opener(fasta_path, "rt") as f:
        records = list(SeqIO.parse(f, "fasta"))

    lengths = [len(r.seq) for r in records]
    total_length = sum(lengths)

    # Length-weighted GC across all contigs
    total_gc = sum(gc_fraction(r.seq) * len(r.seq) for r in records)
    gc_pct = round((total_gc / total_length) * 100, 2) if total_length > 0 else 0.0

    return {
        "total_length_bp": total_length,
        "gc_percent": gc_pct,
        "contig_count": len(records),
        "n50_bp": _compute_n50(lengths),
        "largest_contig_bp": max(lengths) if lengths else 0,
    }


def compute_genome_stats(fasta_path: Path) -> dict:
    """
    Compute genome stats from a FASTA file (plain or gzipped).
    Uses SeqKit if available, falls back to BioPython.
    """
    fasta_path = Path(fasta_path)

    # Derive MAG ID from filename
    mag_id = fasta_path.name
    for suffix in (".fasta.gz", ".fa.gz", ".fna.gz", ".fasta", ".fna", ".fa"):
        if mag_id.endswith(suffix):
            mag_id = mag_id[: -len(suffix)]
            break

    if shutil.which("seqkit"):
        stats = _stats_via_seqkit(fasta_path)
    else:
        stats = _stats_via_biopython(fasta_path)

    stats["mag_id"] = mag_id
    # Reorder with mag_id first
    return {
        "mag_id": mag_id,
        "total_length_bp": stats["total_length_bp"],
        "gc_percent": stats["gc_percent"],
        "contig_count": stats["contig_count"],
        "n50_bp": stats["n50_bp"],
        "largest_contig_bp": stats["largest_contig_bp"],
    }


def write_stats_tsv(stats: dict, output_path: Path) -> None:
    """Write stats dict as a two-row TSV (header + data)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(stats.keys())
    with open(output_path, "w") as f:
        f.write("\t".join(keys) + "\n")
        f.write("\t".join(str(stats[k]) for k in keys) + "\n")


if __name__ == "__main__":
    import sys
    fasta = Path(sys.argv[1])
    output = Path(sys.argv[2])
    stats = compute_genome_stats(fasta)
    write_stats_tsv(stats, output)
```

- [ ] **Step 4: Create rules/genome_stats.smk**

```python
rule genome_stats:
    input:
        fasta=lambda wc: mag_fasta(INPUT_DIR, wc.mag_id)
    output:
        stats=str(OUTDIR / "individual" / "{mag_id}" / "genome_stats.tsv")
    threads: 1
    group: "fast_{mag_id}"
    shell:
        "python scripts/genome_stats.py {input.fasta} {output.stats}"
```

- [ ] **Step 5: Run tests and verify they pass**

Run: `python -m pytest tests/test_genome_stats.py -v`

Expected: All 8 tests PASS (will use BioPython fallback since SeqKit likely not in PATH during testing).

- [ ] **Step 6: Commit**

```bash
git add scripts/genome_stats.py rules/genome_stats.smk tests/test_genome_stats.py
git commit -m "feat: genome stats with SeqKit primary and BioPython fallback"
```

---

### Task 10: CheckM2 Batch (rules + script)

**Files:**
- Create: `rules/checkm2.smk`
- Create: `scripts/run_checkm2.py`
- Create: `tests/test_checkm2.py`

- [ ] **Step 1: Write failing tests**

`tests/test_checkm2.py`:
```python
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

    # Create a fake CheckM2 output for the script to find
    output_dir.mkdir(parents=True)
    (output_dir / "quality_report.tsv").write_text(MOCK_CHECKM2_TSV)

    run_checkm2(str(input_dir), str(output_dir), str(output_tsv), threads=16)

    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "checkm2" in cmd[0]
    assert "predict" in cmd
    assert "--threads" in cmd
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_checkm2.py -v`

Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement scripts/run_checkm2.py**

```python
"""Batch runner for CheckM2 predict."""
from __future__ import annotations
import shutil
import subprocess
from pathlib import Path


def parse_checkm2_output(report_path: Path) -> list[dict]:
    """
    Parse CheckM2 quality_report.tsv into a list of dicts.
    Renames 'Name' -> 'mag_id' and normalizes column names.
    """
    rows = []
    with open(report_path) as f:
        header = f.readline().strip().split("\t")
        for line in f:
            values = line.strip().split("\t")
            row = dict(zip(header, values))
            rows.append({
                "mag_id": row["Name"],
                "completeness": float(row["Completeness"]),
                "contamination": float(row["Contamination"]),
                "completeness_model_used": row.get("Completeness_Model_Used", ""),
                "translation_table_used": row.get("Translation_Table_Used", ""),
            })
    return rows


def write_output_tsv(rows: list[dict], output_path: Path) -> None:
    """Write parsed CheckM2 results to a TSV."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(output_path, "w") as f:
        f.write("\t".join(keys) + "\n")
        for row in rows:
            f.write("\t".join(str(row[k]) for k in keys) + "\n")


def run_checkm2(input_dir: str, output_dir: str, output_tsv: str, threads: int = 16) -> None:
    """Run CheckM2 predict on a directory of genomes."""
    cmd = [
        "checkm2", "predict",
        "--input", input_dir,
        "--output-directory", output_dir,
        "--threads", str(threads),
        "--force",
    ]
    subprocess.run(cmd, check=True)

    # Parse and write normalized output
    report = Path(output_dir) / "quality_report.tsv"
    if not report.exists():
        raise FileNotFoundError(f"CheckM2 output not found: {report}")

    rows = parse_checkm2_output(report)
    write_output_tsv(rows, Path(output_tsv))


if __name__ == "__main__":
    import sys
    run_checkm2(
        input_dir=sys.argv[1],
        output_dir=sys.argv[2],
        output_tsv=sys.argv[3],
        threads=int(sys.argv[4]),
    )
```

- [ ] **Step 4: Create rules/checkm2.smk**

```python
rule checkm2_setup_batch:
    """Create a directory of symlinks for one batch of genomes."""
    input:
        fastas=lambda wc: [mag_fasta(INPUT_DIR, mid) for mid in BATCHES[wc.batch_id]]
    output:
        batch_dir=directory(str(OUTDIR / "batches" / "checkm2" / "{batch_id}" / "input"))
    threads: 1
    run:
        create_batch_dir(wildcards.batch_id, BATCHES[wildcards.batch_id],
                         INPUT_DIR, output.batch_dir)


rule checkm2_batch:
    """Run CheckM2 predict on one batch."""
    input:
        batch_dir=str(OUTDIR / "batches" / "checkm2" / "{batch_id}" / "input")
    output:
        results=str(OUTDIR / "batches" / "checkm2" / "{batch_id}" / "quality_report.tsv")
    threads: 16
    params:
        outdir=str(OUTDIR / "batches" / "checkm2" / "{batch_id}" / "output")
    shell:
        "python scripts/run_checkm2.py {input.batch_dir} {params.outdir} {output.results} {threads}"


rule checkm2_merge:
    """Concatenate all batch quality reports into one file."""
    input:
        expand(str(OUTDIR / "batches" / "checkm2" / "{batch_id}" / "quality_report.tsv"),
               batch_id=BATCH_IDS)
    output:
        str(OUTDIR / "checkm2_quality.tsv")
    threads: 1
    run:
        header = None
        with open(output[0], "w") as out:
            for tsv in input:
                with open(tsv) as f:
                    h = f.readline()
                    if header is None:
                        header = h
                        out.write(header)
                    for line in f:
                        if line.strip():
                            out.write(line)
```

- [ ] **Step 5: Run tests and verify they pass**

Run: `python -m pytest tests/test_checkm2.py -v`

Expected: All 2 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/run_checkm2.py rules/checkm2.smk tests/test_checkm2.py
git commit -m "feat: CheckM2 batch runner with setup/run/merge rules"
```

---

### Task 11: GUNC Batch (rules + script)

**Files:**
- Create: `rules/gunc.smk`
- Create: `scripts/run_gunc.py`
- Create: `tests/test_gunc.py`

- [ ] **Step 1: Write failing tests**

`tests/test_gunc.py`:
```python
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
    """Test that pass_gunc reflects the CSS threshold."""
    report = tmp_path / "GUNC.maxCSS_level.tsv"
    report.write_text(MOCK_GUNC_TSV)
    rows = parse_gunc_output(report, css_threshold=0.45)
    # mag_001 CSS=0.12 < 0.45 -> pass
    assert rows[0]["pass_gunc"] is True
    # mag_002 CSS=0.55 >= 0.45 -> fail
    assert rows[1]["pass_gunc"] is False


@patch("subprocess.run")
def test_run_gunc_calls_correct_command(mock_run, tmp_path):
    mock_run.return_value = MagicMock(returncode=0)
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True)
    output_tsv = tmp_path / "results.tsv"

    # Create mock GUNC output
    (output_dir / "GUNC.maxCSS_level.tsv").write_text(MOCK_GUNC_TSV)

    run_gunc(str(input_dir), str(output_dir), str(output_tsv),
             threads=16, db_type="gtdb_214")

    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert "gunc" in cmd[0]
    assert "run" in cmd
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_gunc.py -v`

Expected: FAIL

- [ ] **Step 3: Implement scripts/run_gunc.py**

```python
"""Batch runner for GUNC chimerism detection."""
from __future__ import annotations
import subprocess
from pathlib import Path


def parse_gunc_output(report_path: Path, css_threshold: float = 0.45) -> list[dict]:
    """
    Parse GUNC's GUNC.maxCSS_level.tsv output.
    Returns list of dicts with normalized column names.
    The pass_gunc field is recomputed from css_threshold rather than
    relying on GUNC's built-in pass column, for configurability.
    """
    rows = []
    with open(report_path) as f:
        header = f.readline().strip().split("\t")
        for line in f:
            values = line.strip().split("\t")
            if not values or not values[0]:
                continue
            row = dict(zip(header, values))
            css = float(row.get("clade_separation_score", 0))
            rows.append({
                "mag_id": row["genome"],
                "css": css,
                "rrs": float(row.get("reference_representation_score", 0)),
                "contamination_portion": float(row.get("contamination_portion", 0)),
                "taxonomic_level": row.get("taxonomic_level", ""),
                "pass_gunc": css < css_threshold,
            })
    return rows


def write_output_tsv(rows: list[dict], output_path: Path) -> None:
    """Write parsed GUNC results to a TSV."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(output_path, "w") as f:
        f.write("\t".join(keys) + "\n")
        for row in rows:
            f.write("\t".join(str(row[k]) for k in keys) + "\n")


def run_gunc(
    input_dir: str, output_dir: str, output_tsv: str,
    threads: int = 16, db_type: str = "gtdb_214"
) -> None:
    """Run GUNC on a directory of genomes."""
    cmd = [
        "gunc", "run",
        "--input_dir", input_dir,
        "--out_dir", output_dir,
        "--threads", str(threads),
        "--db_file", db_type,
    ]
    subprocess.run(cmd, check=True)

    # Parse output
    report = Path(output_dir) / "GUNC.maxCSS_level.tsv"
    if not report.exists():
        raise FileNotFoundError(f"GUNC output not found: {report}")

    rows = parse_gunc_output(report)
    write_output_tsv(rows, Path(output_tsv))


if __name__ == "__main__":
    import sys
    run_gunc(
        input_dir=sys.argv[1],
        output_dir=sys.argv[2],
        output_tsv=sys.argv[3],
        threads=int(sys.argv[4]),
        db_type=sys.argv[5] if len(sys.argv) > 5 else "gtdb_214",
    )
```

- [ ] **Step 4: Create rules/gunc.smk**

```python
rule gunc_setup_batch:
    """Create a directory of symlinks for one batch of genomes."""
    input:
        fastas=lambda wc: [mag_fasta(INPUT_DIR, mid) for mid in BATCHES[wc.batch_id]]
    output:
        batch_dir=directory(str(OUTDIR / "batches" / "gunc" / "{batch_id}" / "input"))
    threads: 1
    run:
        create_batch_dir(wildcards.batch_id, BATCHES[wildcards.batch_id],
                         INPUT_DIR, output.batch_dir)


rule gunc_batch:
    """Run GUNC on one batch."""
    input:
        batch_dir=str(OUTDIR / "batches" / "gunc" / "{batch_id}" / "input")
    output:
        results=str(OUTDIR / "batches" / "gunc" / "{batch_id}" / "gunc_output.tsv")
    threads: 16
    params:
        outdir=str(OUTDIR / "batches" / "gunc" / "{batch_id}" / "output"),
        db_path=config.get("gunc_db_path") or "",
        db_type=config.get("gunc", {}).get("db_type", "gtdb_214"),
    shell:
        "python scripts/run_gunc.py {input.batch_dir} {params.outdir} {output.results} {threads} {params.db_type}"


rule gunc_merge:
    """Concatenate all batch GUNC reports into one file."""
    input:
        expand(str(OUTDIR / "batches" / "gunc" / "{batch_id}" / "gunc_output.tsv"),
               batch_id=BATCH_IDS)
    output:
        str(OUTDIR / "gunc_chimerism.tsv")
    threads: 1
    run:
        header = None
        with open(output[0], "w") as out:
            for tsv in input:
                with open(tsv) as f:
                    h = f.readline()
                    if header is None:
                        header = h
                        out.write(header)
                    for line in f:
                        if line.strip():
                            out.write(line)
```

- [ ] **Step 5: Run tests and verify they pass**

Run: `python -m pytest tests/test_gunc.py -v`

Expected: All 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/run_gunc.py rules/gunc.smk tests/test_gunc.py
git commit -m "feat: GUNC batch runner with chimerism detection and CSS threshold"
```

---

### Task 12: GTDB-Tk Batch (rules + script)

**Files:**
- Create: `rules/gtdbtk.smk`
- Create: `scripts/run_gtdbtk.py`
- Create: `tests/test_gtdbtk.py`

- [ ] **Step 1: Write failing tests**

`tests/test_gtdbtk.py`:
```python
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from scripts.run_gtdbtk import parse_gtdbtk_output, run_gtdbtk

MOCK_BAC120_TSV = (
    "user_genome\tclassification\tfastani_reference\tfastani_radius\tfastani_ani\t"
    "fastani_af\tclosest_placement_reference\tclosest_placement_radius\t"
    "closest_placement_ani\tclosest_placement_af\tpplacer_taxonomy\t"
    "classification_method\tnote\tother_related_references(genome_id,species_name,radius,ANI,AF)\taa_percent\ttranslation_table\tred_value\twarnings\n"
    "synthetic_mag_001\td__Bacteria;p__Proteobacteria;c__Gammaproteobacteria;"
    "o__Enterobacterales;f__Enterobacteriaceae;g__Escherichia;s__Escherichia coli\t"
    "GCF_000005845.2\t95.0\t98.5\t0.92\tGCF_000005845.2\t95.0\t98.5\t0.92\t"
    "d__Bacteria;p__Proteobacteria\tANI\tN/A\tN/A\t95.2\t11\t0.95\tN/A\n"
)

MOCK_AR53_TSV = (
    "user_genome\tclassification\tfastani_reference\tfastani_radius\tfastani_ani\t"
    "fastani_af\tclosest_placement_reference\tclosest_placement_radius\t"
    "closest_placement_ani\tclosest_placement_af\tpplacer_taxonomy\t"
    "classification_method\tnote\tother_related_references(genome_id,species_name,radius,ANI,AF)\taa_percent\ttranslation_table\tred_value\twarnings\n"
    "synthetic_mag_002\td__Archaea;p__Euryarchaeota;c__Methanobacteria;"
    "o__Methanobacteriales;f__Methanobacteriaceae;g__Methanobacterium;s__Methanobacterium sp001\t"
    "GCF_000007345.1\t95.0\t96.1\t0.85\tGCF_000007345.1\t95.0\t96.1\t0.85\t"
    "d__Archaea;p__Euryarchaeota\tANI\tN/A\tN/A\t88.4\t11\t0.91\tN/A\n"
)


def test_parse_gtdbtk_bac120(tmp_path):
    bac = tmp_path / "gtdbtk.bac120.summary.tsv"
    bac.write_text(MOCK_BAC120_TSV)
    rows = parse_gtdbtk_output(bac120_path=bac)
    assert len(rows) == 1
    assert rows[0]["mag_id"] == "synthetic_mag_001"
    assert rows[0]["domain"] == "Bacteria"
    assert rows[0]["genus"] == "Escherichia"
    assert rows[0]["species"] == "Escherichia coli"
    assert rows[0]["fastani_ani"] == pytest.approx(98.5)
    assert rows[0]["classification_method"] == "ANI"


def test_parse_gtdbtk_both_domains(tmp_path):
    bac = tmp_path / "gtdbtk.bac120.summary.tsv"
    bac.write_text(MOCK_BAC120_TSV)
    ar = tmp_path / "gtdbtk.ar53.summary.tsv"
    ar.write_text(MOCK_AR53_TSV)
    rows = parse_gtdbtk_output(bac120_path=bac, ar53_path=ar)
    assert len(rows) == 2
    domains = {r["domain"] for r in rows}
    assert domains == {"Bacteria", "Archaea"}


def test_parse_gtdbtk_empty_results(tmp_path):
    """Handle case where no genomes classified in one domain."""
    bac = tmp_path / "gtdbtk.bac120.summary.tsv"
    # Header only, no data
    header = MOCK_BAC120_TSV.split("\n")[0] + "\n"
    bac.write_text(header)
    rows = parse_gtdbtk_output(bac120_path=bac)
    assert len(rows) == 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_gtdbtk.py -v`

Expected: FAIL

- [ ] **Step 3: Implement scripts/run_gtdbtk.py**

```python
"""Batch runner for GTDB-Tk classify_wf."""
from __future__ import annotations
import subprocess
from pathlib import Path


# GTDB taxonomy ranks in order
_RANKS = ["domain", "phylum", "class", "order", "family", "genus", "species"]
_RANK_PREFIXES = ["d__", "p__", "c__", "o__", "f__", "g__", "s__"]


def _parse_classification(classification_string: str) -> dict:
    """Parse GTDB classification string into individual rank columns."""
    result = {r: "" for r in _RANKS}
    if not classification_string or classification_string == "N/A":
        return result
    parts = classification_string.split(";")
    for part in parts:
        for rank, prefix in zip(_RANKS, _RANK_PREFIXES):
            if part.startswith(prefix):
                result[rank] = part[len(prefix):]
                break
    return result


def _parse_summary_tsv(path: Path) -> list[dict]:
    """Parse a single GTDB-Tk summary TSV (bac120 or ar53)."""
    rows = []
    if not path.exists():
        return rows
    with open(path) as f:
        header = f.readline().strip().split("\t")
        for line in f:
            values = line.strip().split("\t")
            if not values or not values[0]:
                continue
            raw = dict(zip(header, values))
            ranks = _parse_classification(raw.get("classification", ""))

            # Parse numeric fields safely
            def safe_float(val):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None

            rows.append({
                "mag_id": raw["user_genome"],
                **ranks,
                "classification": raw.get("classification", ""),
                "fastani_reference": raw.get("fastani_reference", ""),
                "fastani_ani": safe_float(raw.get("fastani_ani")),
                "fastani_af": safe_float(raw.get("fastani_af")),
                "classification_method": raw.get("classification_method", ""),
                "note": raw.get("note", ""),
                "warnings": raw.get("warnings", ""),
            })
    return rows


def parse_gtdbtk_output(
    bac120_path: Path | None = None,
    ar53_path: Path | None = None,
) -> list[dict]:
    """Parse both bac120 and ar53 summary files, merge into one list."""
    rows = []
    if bac120_path:
        rows.extend(_parse_summary_tsv(Path(bac120_path)))
    if ar53_path:
        rows.extend(_parse_summary_tsv(Path(ar53_path)))
    return rows


def write_output_tsv(rows: list[dict], output_path: Path) -> None:
    """Write parsed GTDB-Tk results to a TSV."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        # Write header-only file
        keys = ["mag_id"] + _RANKS + [
            "classification", "fastani_reference", "fastani_ani",
            "fastani_af", "classification_method", "note", "warnings",
        ]
        with open(output_path, "w") as f:
            f.write("\t".join(keys) + "\n")
        return
    keys = list(rows[0].keys())
    with open(output_path, "w") as f:
        f.write("\t".join(keys) + "\n")
        for row in rows:
            f.write("\t".join(str(row.get(k, "")) for k in keys) + "\n")


def run_gtdbtk(
    input_dir: str, output_dir: str, output_tsv: str,
    threads: int = 64, pplacer_cpus: int = 1,
    skip_ani_screen: bool = False,
) -> None:
    """Run GTDB-Tk classify_wf on a directory of genomes."""
    cmd = [
        "gtdbtk", "classify_wf",
        "--genome_dir", input_dir,
        "--out_dir", output_dir,
        "--cpus", str(threads),
        "--pplacer_cpus", str(pplacer_cpus),
    ]
    if skip_ani_screen:
        cmd.append("--skip_ani_screen")

    # Detect FASTA extension from first file in directory
    input_path = Path(input_dir)
    for ext in (".fna", ".fasta", ".fa", ".fna.gz", ".fasta.gz", ".fa.gz"):
        if list(input_path.glob(f"*{ext}")):
            cmd.extend(["--extension", ext.lstrip(".")])
            break

    subprocess.run(cmd, check=True)

    # Parse both bacterial and archaeal results
    out_path = Path(output_dir)
    bac = out_path / "classify" / "gtdbtk.bac120.summary.tsv"
    ar = out_path / "classify" / "gtdbtk.ar53.summary.tsv"
    rows = parse_gtdbtk_output(
        bac120_path=bac if bac.exists() else None,
        ar53_path=ar if ar.exists() else None,
    )
    write_output_tsv(rows, Path(output_tsv))


if __name__ == "__main__":
    import sys
    run_gtdbtk(
        input_dir=sys.argv[1],
        output_dir=sys.argv[2],
        output_tsv=sys.argv[3],
        threads=int(sys.argv[4]),
        pplacer_cpus=int(sys.argv[5]) if len(sys.argv) > 5 else 1,
        skip_ani_screen=sys.argv[6].lower() == "true" if len(sys.argv) > 6 else False,
    )
```

- [ ] **Step 4: Create rules/gtdbtk.smk**

```python
rule gtdbtk_setup_batch:
    """Create a directory of symlinks for one batch of genomes."""
    input:
        fastas=lambda wc: [mag_fasta(INPUT_DIR, mid) for mid in BATCHES[wc.batch_id]]
    output:
        batch_dir=directory(str(OUTDIR / "batches" / "gtdbtk" / "{batch_id}" / "input"))
    threads: 1
    run:
        create_batch_dir(wildcards.batch_id, BATCHES[wildcards.batch_id],
                         INPUT_DIR, output.batch_dir)


rule gtdbtk_batch:
    """Run GTDB-Tk classify_wf on one batch."""
    input:
        batch_dir=str(OUTDIR / "batches" / "gtdbtk" / "{batch_id}" / "input")
    output:
        results=str(OUTDIR / "batches" / "gtdbtk" / "{batch_id}" / "gtdbtk_output.tsv")
    threads: 64
    resources:
        mem_mb=120000
    params:
        outdir=str(OUTDIR / "batches" / "gtdbtk" / "{batch_id}" / "output"),
        pplacer_cpus=config.get("gtdbtk", {}).get("pplacer_cpus", 1),
        skip_ani=config.get("gtdbtk", {}).get("skip_ani_screen", False),
    shell:
        "python scripts/run_gtdbtk.py {input.batch_dir} {params.outdir} {output.results} "
        "{threads} {params.pplacer_cpus} {params.skip_ani}"


rule gtdbtk_merge:
    """Concatenate all batch GTDB-Tk reports into one file."""
    input:
        expand(str(OUTDIR / "batches" / "gtdbtk" / "{batch_id}" / "gtdbtk_output.tsv"),
               batch_id=BATCH_IDS)
    output:
        str(OUTDIR / "gtdbtk_taxonomy.tsv")
    threads: 1
    run:
        header = None
        with open(output[0], "w") as out:
            for tsv in input:
                with open(tsv) as f:
                    h = f.readline()
                    if header is None:
                        header = h
                        out.write(header)
                    for line in f:
                        if line.strip():
                            out.write(line)
```

- [ ] **Step 5: Run tests and verify they pass**

Run: `python -m pytest tests/test_gtdbtk.py -v`

Expected: All 3 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/run_gtdbtk.py rules/gtdbtk.smk tests/test_gtdbtk.py
git commit -m "feat: GTDB-Tk batch runner with bac120/ar53 parsing"
```

---

### Task 13: Merge Reports + Quality Tiers (aggregate)

**Files:**
- Create: `rules/aggregate.smk`
- Create: `scripts/merge_reports.py`
- Create: `tests/test_merge_reports.py`

- [ ] **Step 1: Write failing tests**

`tests/test_merge_reports.py`:
```python
import pytest
from scripts.merge_reports import assign_quality_tier, merge_all_reports

DEFAULT_QUALITY_CFG = {
    "high_completeness": 90.0,
    "high_contamination": 5.0,
    "medium_completeness": 60.0,
    "medium_contamination": 10.0,
    "min_quality_score": 50.0,
    "gunc_css_threshold": 0.45,
    "default_filter": "medium_quality",
}


def test_assign_high_quality():
    row = {"completeness": 95.0, "contamination": 1.0, "pass_gunc": True}
    assert assign_quality_tier(row, DEFAULT_QUALITY_CFG) == "high_quality"


def test_assign_medium_quality():
    row = {"completeness": 75.0, "contamination": 3.0, "pass_gunc": True}
    assert assign_quality_tier(row, DEFAULT_QUALITY_CFG) == "medium_quality"


def test_assign_medium_chimeric():
    row = {"completeness": 75.0, "contamination": 3.0, "pass_gunc": False}
    assert assign_quality_tier(row, DEFAULT_QUALITY_CFG) == "medium_chimeric"


def test_assign_low_quality():
    row = {"completeness": 40.0, "contamination": 2.0, "pass_gunc": True}
    assert assign_quality_tier(row, DEFAULT_QUALITY_CFG) == "low_quality"


def test_assign_low_chimeric():
    row = {"completeness": 40.0, "contamination": 2.0, "pass_gunc": False}
    assert assign_quality_tier(row, DEFAULT_QUALITY_CFG) == "low_chimeric"


def test_assign_high_contamination_is_low():
    """High completeness but contamination >= 10 -> low_quality."""
    row = {"completeness": 95.0, "contamination": 12.0, "pass_gunc": True}
    assert assign_quality_tier(row, DEFAULT_QUALITY_CFG) == "low_quality"


def test_assign_quality_score_below_threshold():
    """Completeness 65, contamination 5 -> qscore=40 < 50 -> low_quality."""
    row = {"completeness": 65.0, "contamination": 5.0, "pass_gunc": True}
    assert assign_quality_tier(row, DEFAULT_QUALITY_CFG) == "low_quality"


def test_assign_missing_gunc_defaults_to_pass():
    """When GUNC not run, pass_gunc defaults to True."""
    row = {"completeness": 95.0, "contamination": 1.0}
    assert assign_quality_tier(row, DEFAULT_QUALITY_CFG) == "high_quality"


def test_merge_all_reports(tmp_path):
    """Test full merge pipeline with mock data."""
    # Create genome stats files
    indiv = tmp_path / "individual"
    for mag_id in ["mag_001", "mag_002"]:
        mag_dir = indiv / mag_id
        mag_dir.mkdir(parents=True)
        (mag_dir / "genome_stats.tsv").write_text(
            "mag_id\ttotal_length_bp\tgc_percent\tcontig_count\tn50_bp\tlargest_contig_bp\n"
            f"{mag_id}\t1000000\t45.0\t10\t200000\t300000\n"
        )

    # Create checkm2 report
    (tmp_path / "checkm2_quality.tsv").write_text(
        "mag_id\tcompleteness\tcontamination\tcompleteness_model_used\ttranslation_table_used\n"
        "mag_001\t95.5\t1.2\tNeural Network\t11\n"
        "mag_002\t55.0\t8.0\tNeural Network\t11\n"
    )

    # Create gunc report
    (tmp_path / "gunc_chimerism.tsv").write_text(
        "mag_id\tcss\trrs\tcontamination_portion\ttaxonomic_level\tpass_gunc\n"
        "mag_001\t0.1\t0.9\t0.05\tgenus\tTrue\n"
        "mag_002\t0.6\t0.5\t0.3\tphylum\tFalse\n"
    )

    combined = tmp_path / "combined_report.tsv"
    filtered = tmp_path / "filtered_report.tsv"

    merge_all_reports(
        stats_dir=str(indiv),
        checkm2_path=str(tmp_path / "checkm2_quality.tsv"),
        gunc_path=str(tmp_path / "gunc_chimerism.tsv"),
        gtdbtk_path=None,
        output_combined=str(combined),
        output_filtered=str(filtered),
        quality_cfg=DEFAULT_QUALITY_CFG,
    )

    # Check combined report
    lines = combined.read_text().strip().split("\n")
    assert len(lines) == 3  # header + 2 rows
    assert "quality_tier" in lines[0]

    # Check filtered report: mag_001 is high_quality (passes), mag_002 is low_chimeric (excluded)
    filt_lines = filtered.read_text().strip().split("\n")
    assert len(filt_lines) == 2  # header + 1 row (only mag_001)
    assert "mag_001" in filt_lines[1]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_merge_reports.py -v`

Expected: FAIL

- [ ] **Step 3: Implement scripts/merge_reports.py**

```python
"""Merge genome_stats + CheckM2 + GUNC + GTDB-Tk reports and assign quality tiers."""
from __future__ import annotations
import ast
from pathlib import Path


def _read_tsv(path: str | Path) -> list[dict]:
    """Read a TSV file into a list of dicts."""
    rows = []
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return rows
    with open(path) as f:
        header = f.readline().strip().split("\t")
        for line in f:
            values = line.strip().split("\t")
            if values and values[0]:
                rows.append(dict(zip(header, values)))
    return rows


def _to_float(val, default=None):
    """Safely convert a value to float."""
    if val is None or val == "" or val == "None" or val == "N/A":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _to_bool(val, default=True):
    """Safely convert a value to bool."""
    if val is None or val == "":
        return default
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("true", "1", "yes")


def assign_quality_tier(row: dict, cfg: dict) -> str:
    """
    Assign a quality tier to a genome based on CheckM2 and GUNC results.

    Tiers (in order of precedence):
      high_quality     : comp >= 90, contam < 5,  qscore >= 50, GUNC pass
      medium_quality   : comp >= 60, contam < 10, qscore >= 50, GUNC pass
      medium_chimeric  : meets medium_quality thresholds but GUNC flagged chimeric
      low_quality      : comp < 60 OR contam >= 10 OR qscore < 50
      low_chimeric     : meets low_quality AND GUNC flagged chimeric
    """
    comp = _to_float(row.get("completeness"), 0)
    contam = _to_float(row.get("contamination"), 100)
    qscore = comp - 5 * contam
    gunc_pass = _to_bool(row.get("pass_gunc"), True)  # True if GUNC not run

    is_high = (
        comp >= cfg["high_completeness"]
        and contam < cfg["high_contamination"]
        and qscore >= cfg["min_quality_score"]
    )
    is_medium = (
        comp >= cfg["medium_completeness"]
        and contam < cfg["medium_contamination"]
        and qscore >= cfg["min_quality_score"]
    )

    if is_high and gunc_pass:
        return "high_quality"
    elif is_medium and gunc_pass:
        return "medium_quality"
    elif is_medium and not gunc_pass:
        return "medium_chimeric"
    elif not gunc_pass:
        return "low_chimeric"
    else:
        return "low_quality"


# Tiers ordered from highest to lowest quality
_TIER_ORDER = ["high_quality", "medium_quality", "medium_chimeric", "low_quality", "low_chimeric"]

# Which tiers pass each filter level
_FILTER_TIERS = {
    "high_quality": {"high_quality"},
    "medium_quality": {"high_quality", "medium_quality"},
}


def merge_all_reports(
    stats_dir: str,
    checkm2_path: str | None,
    gunc_path: str | None,
    gtdbtk_path: str | None,
    output_combined: str,
    output_filtered: str,
    quality_cfg: dict,
) -> None:
    """
    Left-join all reports on mag_id, compute quality tiers,
    write combined and filtered reports.
    """
    # 1. Read all per-MAG genome_stats.tsv files
    stats_rows = []
    stats_path = Path(stats_dir)
    for mag_dir in sorted(stats_path.iterdir()):
        if mag_dir.is_dir():
            tsv = mag_dir / "genome_stats.tsv"
            if tsv.exists():
                stats_rows.extend(_read_tsv(tsv))

    # Build lookup by mag_id
    data = {row["mag_id"]: dict(row) for row in stats_rows}

    # 2. Left-join CheckM2
    if checkm2_path:
        for row in _read_tsv(checkm2_path):
            mid = row.get("mag_id", "")
            if mid in data:
                data[mid].update(row)

    # 3. Left-join GUNC
    if gunc_path:
        for row in _read_tsv(gunc_path):
            mid = row.get("mag_id", "")
            if mid in data:
                data[mid].update(row)

    # 4. Left-join GTDB-Tk
    if gtdbtk_path:
        for row in _read_tsv(gtdbtk_path):
            mid = row.get("mag_id", "")
            if mid in data:
                data[mid].update(row)

    # 5. Compute derived columns and assign quality tiers
    for mid, row in data.items():
        comp = _to_float(row.get("completeness"), 0)
        contam = _to_float(row.get("contamination"), 0)
        row["quality_score"] = round(comp - 5 * contam, 2)
        row["quality_tier"] = assign_quality_tier(row, quality_cfg)

    # 6. Define output column order
    columns = [
        "mag_id", "total_length_bp", "gc_percent", "contig_count", "n50_bp",
        "largest_contig_bp", "completeness", "contamination",
        "completeness_model_used", "quality_score", "css", "rrs",
        "contamination_portion", "gunc_taxonomic_level", "pass_gunc",
        "domain", "phylum", "class", "order", "family", "genus", "species",
        "classification", "fastani_reference", "fastani_ani", "fastani_af",
        "classification_method", "quality_tier",
    ]
    # Use only columns that exist in at least one row
    available_cols = set()
    for row in data.values():
        available_cols.update(row.keys())
    # Remap GUNC taxonomic_level -> gunc_taxonomic_level
    for row in data.values():
        if "taxonomic_level" in row and "gunc_taxonomic_level" not in row:
            row["gunc_taxonomic_level"] = row.pop("taxonomic_level")
    output_cols = [c for c in columns if c in available_cols or c in ("quality_score", "quality_tier")]

    # 7. Write combined report
    rows_sorted = sorted(data.values(), key=lambda r: r.get("mag_id", ""))
    _write_tsv(rows_sorted, output_cols, output_combined)

    # 8. Write filtered report
    filter_level = quality_cfg.get("default_filter", "medium_quality")
    passing_tiers = _FILTER_TIERS.get(filter_level, {"high_quality", "medium_quality"})
    filtered_rows = [r for r in rows_sorted if r.get("quality_tier") in passing_tiers]
    _write_tsv(filtered_rows, output_cols, output_filtered)


def _write_tsv(rows: list[dict], columns: list[str], output_path: str) -> None:
    """Write rows to a TSV with specified column order."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        f.write("\t".join(columns) + "\n")
        for row in rows:
            f.write("\t".join(str(row.get(c, "")) for c in columns) + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Merge QC reports and assign quality tiers")
    parser.add_argument("--stats-dir", required=True)
    parser.add_argument("--checkm2", default=None)
    parser.add_argument("--gunc", default=None)
    parser.add_argument("--gtdbtk", default=None)
    parser.add_argument("--output-combined", required=True)
    parser.add_argument("--output-filtered", required=True)
    parser.add_argument("--quality-config", default="{}")
    args = parser.parse_args()

    quality_cfg = ast.literal_eval(args.quality_config) if args.quality_config else {}

    merge_all_reports(
        stats_dir=args.stats_dir,
        checkm2_path=args.checkm2 if args.checkm2 else None,
        gunc_path=args.gunc if args.gunc else None,
        gtdbtk_path=args.gtdbtk if args.gtdbtk else None,
        output_combined=args.output_combined,
        output_filtered=args.output_filtered,
        quality_cfg=quality_cfg,
    )
```

- [ ] **Step 4: Create rules/aggregate.smk**

```python
rule merge_reports:
    """Left-join genome_stats + checkm2 + gunc + gtdbtk on mag_id, assign quality tiers."""
    input:
        stats=expand(str(OUTDIR / "individual" / "{mag_id}" / "genome_stats.tsv"), mag_id=MAG_IDS),
        checkm2=str(OUTDIR / "checkm2_quality.tsv") if "checkm2" in STEPS else [],
        gunc=str(OUTDIR / "gunc_chimerism.tsv") if "gunc" in STEPS else [],
        gtdbtk=str(OUTDIR / "gtdbtk_taxonomy.tsv") if "gtdbtk" in STEPS else [],
    output:
        combined=str(OUTDIR / "combined_report.tsv"),
        filtered=str(OUTDIR / "filtered_report.tsv"),
    threads: 1
    params:
        stats_dir=str(OUTDIR / "individual"),
        checkm2=str(OUTDIR / "checkm2_quality.tsv") if "checkm2" in STEPS else "",
        gunc=str(OUTDIR / "gunc_chimerism.tsv") if "gunc" in STEPS else "",
        gtdbtk=str(OUTDIR / "gtdbtk_taxonomy.tsv") if "gtdbtk" in STEPS else "",
        quality_cfg=config.get("quality_filter", {}),
    shell:
        "python scripts/merge_reports.py "
        "--stats-dir {params.stats_dir} "
        "--checkm2 {params.checkm2} "
        "--gunc {params.gunc} "
        "--gtdbtk {params.gtdbtk} "
        "--output-combined {output.combined} "
        "--output-filtered {output.filtered} "
        "--quality-config '{params.quality_cfg}'"
```

- [ ] **Step 5: Run tests and verify they pass**

Run: `python -m pytest tests/test_merge_reports.py -v`

Expected: All 9 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/merge_reports.py rules/aggregate.smk tests/test_merge_reports.py
git commit -m "feat: merge reports with quality tier assignment and MIMAG filtering"
```

---

### Task 14: Dereplication (rules + script)

**Files:**
- Create: `rules/dereplicate.smk`
- Create: `scripts/dereplicate.py`
- Create: `tests/test_dereplicate.py`

- [ ] **Step 1: Write failing tests**

`tests/test_dereplicate.py`:
```python
import math
import pytest
from scripts.dereplicate import (
    compute_composite_scores,
    greedy_cluster,
    parse_edge_list,
)


def test_compute_composite_scores_basic():
    """Test composite score computation with simple data."""
    genomes = {
        "mag_A": {"quality_score": 90, "completeness": 95, "n50_bp": 100000,
                   "contamination": 1.0, "css": 0.1},
        "mag_B": {"quality_score": 50, "completeness": 65, "n50_bp": 10000,
                   "contamination": 8.0, "css": 0.4},
    }
    weights = {"w_qscore": 1.0, "w_completeness": 1.0, "w_n50": 0.5,
               "w_contam": 0.5, "w_gunc": 0.5}
    scores = compute_composite_scores(genomes, weights)
    # mag_A should score higher than mag_B on every metric
    assert scores["mag_A"] > scores["mag_B"]


def test_compute_composite_scores_identical_values():
    """When all genomes are identical, all normalized values should be 1.0."""
    genomes = {
        "mag_A": {"quality_score": 90, "completeness": 95, "n50_bp": 50000,
                   "contamination": 1.0, "css": 0.0},
        "mag_B": {"quality_score": 90, "completeness": 95, "n50_bp": 50000,
                   "contamination": 1.0, "css": 0.0},
    }
    weights = {"w_qscore": 1.0, "w_completeness": 1.0, "w_n50": 0.5,
               "w_contam": 0.5, "w_gunc": 0.5}
    scores = compute_composite_scores(genomes, weights)
    # Identical genomes should have identical scores
    assert scores["mag_A"] == pytest.approx(scores["mag_B"])


def test_parse_edge_list(tmp_path):
    """Test parsing of skani triangle edge list output."""
    edge_file = tmp_path / "edges.tsv"
    edge_file.write_text(
        "Ref_file\tQuery_file\tANI\tAlign_fraction_ref\tAlign_fraction_query\tRef_name\tQuery_name\n"
        "/mags/mag_A.fna\t/mags/mag_B.fna\t97.5\t85.0\t82.0\tmag_A\tmag_B\n"
        "/mags/mag_A.fna\t/mags/mag_C.fna\t96.0\t70.0\t5.0\tmag_A\tmag_C\n"
    )
    edges = parse_edge_list(edge_file)
    assert len(edges) == 2
    assert edges[0]["ani"] == pytest.approx(97.5)
    assert edges[0]["af_ref"] == pytest.approx(85.0)
    assert edges[0]["af_query"] == pytest.approx(82.0)


def test_greedy_cluster_single_cluster():
    """Three genomes all within ANI threshold -> one cluster."""
    scores = {"mag_A": 3.0, "mag_B": 2.0, "mag_C": 1.0}
    edges = [
        {"ref": "mag_A", "query": "mag_B", "ani": 98.0, "af_ref": 80.0, "af_query": 75.0},
        {"ref": "mag_A", "query": "mag_C", "ani": 97.0, "af_ref": 70.0, "af_query": 65.0},
        {"ref": "mag_B", "query": "mag_C", "ani": 96.5, "af_ref": 60.0, "af_query": 55.0},
    ]
    clusters = greedy_cluster(scores, edges, ani_threshold=95.0, min_af=10.0)
    # All in one cluster, mag_A is representative (highest score)
    assert len(set(c["cluster_id"] for c in clusters.values())) == 1
    assert clusters["mag_A"]["is_representative"] is True
    assert clusters["mag_B"]["representative"] == "mag_A"


def test_greedy_cluster_two_clusters():
    """Two genomes similar, one distant -> two clusters."""
    scores = {"mag_A": 3.0, "mag_B": 2.0, "mag_C": 1.0}
    edges = [
        {"ref": "mag_A", "query": "mag_B", "ani": 98.0, "af_ref": 80.0, "af_query": 75.0},
        # mag_A-mag_C below ANI threshold
        {"ref": "mag_A", "query": "mag_C", "ani": 90.0, "af_ref": 60.0, "af_query": 55.0},
        {"ref": "mag_B", "query": "mag_C", "ani": 89.0, "af_ref": 50.0, "af_query": 45.0},
    ]
    clusters = greedy_cluster(scores, edges, ani_threshold=95.0, min_af=10.0)
    # Two clusters: {mag_A, mag_B} and {mag_C}
    assert len(set(c["cluster_id"] for c in clusters.values())) == 2
    assert clusters["mag_A"]["cluster_id"] == clusters["mag_B"]["cluster_id"]
    assert clusters["mag_C"]["is_representative"] is True


def test_greedy_cluster_af_filter():
    """High ANI but low AF -> should NOT cluster together."""
    scores = {"mag_A": 3.0, "mag_B": 2.0}
    edges = [
        # High ANI but AF_query is below min_af=10
        {"ref": "mag_A", "query": "mag_B", "ani": 99.0, "af_ref": 80.0, "af_query": 5.0},
    ]
    clusters = greedy_cluster(scores, edges, ani_threshold=95.0, min_af=10.0)
    # Should be two separate clusters due to low bi-directional AF
    assert len(set(c["cluster_id"] for c in clusters.values())) == 2


def test_greedy_cluster_no_edges():
    """Genomes with no edges -> each is its own cluster."""
    scores = {"mag_A": 3.0, "mag_B": 2.0, "mag_C": 1.0}
    edges = []
    clusters = greedy_cluster(scores, edges, ani_threshold=95.0, min_af=10.0)
    assert len(set(c["cluster_id"] for c in clusters.values())) == 3
    for mid in scores:
        assert clusters[mid]["is_representative"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_dereplicate.py -v`

Expected: FAIL

- [ ] **Step 3: Implement scripts/dereplicate.py**

```python
"""Species-level genome dereplication via skani triangle + greedy clustering."""
from __future__ import annotations
import math
import subprocess
from pathlib import Path


def parse_edge_list(edge_path: Path) -> list[dict]:
    """Parse skani triangle edge list output."""
    edges = []
    with open(edge_path) as f:
        header = f.readline()  # skip header
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 7:
                continue
            # Extract MAG ID from filename stem
            ref_name = Path(parts[0]).stem
            query_name = Path(parts[1]).stem
            # Strip compressed extension if present
            for ext in (".fna", ".fasta", ".fa"):
                ref_name = ref_name.removesuffix(ext)
                query_name = query_name.removesuffix(ext)
            edges.append({
                "ref": ref_name,
                "query": query_name,
                "ani": float(parts[2]),
                "af_ref": float(parts[3]),
                "af_query": float(parts[4]),
            })
    return edges


def _min_max_normalize(values: list[float]) -> list[float]:
    """Min-max normalize values to [0, 1]. Returns 1.0 for all if range is 0."""
    if not values:
        return []
    vmin = min(values)
    vmax = max(values)
    if vmax == vmin:
        return [1.0] * len(values)
    return [(v - vmin) / (vmax - vmin) for v in values]


def compute_composite_scores(genomes: dict[str, dict], weights: dict) -> dict[str, float]:
    """
    Compute normalized composite quality scores for representative selection.

    Each metric is min-max normalized to [0, 1] across the filtered genome set,
    then weighted and summed. Higher score = better representative.
    """
    mag_ids = list(genomes.keys())
    if not mag_ids:
        return {}

    # Extract raw metric arrays
    raw_qscore = [float(genomes[m].get("quality_score", 0)) for m in mag_ids]
    raw_comp = [float(genomes[m].get("completeness", 0)) for m in mag_ids]
    raw_n50 = [math.log10(max(float(genomes[m].get("n50_bp", 1)), 1)) for m in mag_ids]
    raw_contam = [100.0 - float(genomes[m].get("contamination", 0)) for m in mag_ids]
    raw_gunc = [1.0 - float(genomes[m].get("css", 0)) for m in mag_ids]

    # Normalize
    norm_qscore = _min_max_normalize(raw_qscore)
    norm_comp = _min_max_normalize(raw_comp)
    norm_n50 = _min_max_normalize(raw_n50)
    norm_contam = _min_max_normalize(raw_contam)
    norm_gunc = _min_max_normalize(raw_gunc)

    # Compute weighted sum
    scores = {}
    for i, mid in enumerate(mag_ids):
        scores[mid] = (
            weights.get("w_qscore", 1.0) * norm_qscore[i]
            + weights.get("w_completeness", 1.0) * norm_comp[i]
            + weights.get("w_n50", 0.5) * norm_n50[i]
            + weights.get("w_contam", 0.5) * norm_contam[i]
            + weights.get("w_gunc", 0.5) * norm_gunc[i]
        )
    return scores


def greedy_cluster(
    scores: dict[str, float],
    edges: list[dict],
    ani_threshold: float,
    min_af: float,
) -> dict[str, dict]:
    """
    Greedy species-level clustering.

    1. Sort genomes by composite_score descending.
    2. Initialize: all genomes unclustered.
    3. For each genome in sorted order:
       a. If already assigned to a cluster, skip.
       b. Make it a new cluster representative.
       c. For all unclustered genomes connected to it in the edge list
          where ANI >= ani_threshold AND AF(ref->query) >= min_af AND
          AF(query->ref) >= min_af: assign them to this cluster.
    4. Return cluster assignments.
    """
    # Build adjacency map: mag_id -> [(other_mag_id, ani, af_ref, af_query)]
    adj: dict[str, list[tuple[str, float, float, float]]] = {m: [] for m in scores}
    for e in edges:
        ref, query = e["ref"], e["query"]
        if ref in scores and query in scores:
            adj[ref].append((query, e["ani"], e["af_ref"], e["af_query"]))
            adj[query].append((ref, e["ani"], e["af_query"], e["af_ref"]))

    sorted_mags = sorted(scores.keys(), key=lambda m: scores[m], reverse=True)

    clusters: dict[str, dict] = {}
    assigned: set[str] = set()
    cluster_counter = 0

    for mag_id in sorted_mags:
        if mag_id in assigned:
            continue

        cluster_counter += 1
        cluster_id = f"cluster_{str(cluster_counter).zfill(4)}"
        members = [mag_id]
        assigned.add(mag_id)

        # Find unclustered neighbors passing thresholds
        for neighbor, ani, af_to_neighbor, af_from_neighbor in adj[mag_id]:
            if neighbor in assigned:
                continue
            if (ani >= ani_threshold
                    and af_to_neighbor >= min_af
                    and af_from_neighbor >= min_af):
                members.append(neighbor)
                assigned.add(neighbor)

        # Record cluster assignments
        for member in members:
            # Find ANI to representative
            ani_to_rep = 100.0
            af_to_rep = 100.0
            if member != mag_id:
                for n, ani, af_r, af_q in adj[member]:
                    if n == mag_id:
                        ani_to_rep = ani
                        af_to_rep = af_r
                        break
            clusters[member] = {
                "mag_id": member,
                "cluster_id": cluster_id,
                "representative": mag_id,
                "is_representative": member == mag_id,
                "composite_score": scores.get(member, 0),
                "ani_to_rep": ani_to_rep,
                "af_to_rep": af_to_rep,
                "cluster_size": len(members),
            }

    return clusters


def run_triangle(
    filtered_report: str, input_dir: str,
    output_edges: str, output_genome_list: str, threads: int,
) -> None:
    """Run skani triangle on filtered genomes."""
    # Read filtered report to get MAG IDs
    mag_ids = []
    with open(filtered_report) as f:
        header = f.readline().strip().split("\t")
        mag_idx = header.index("mag_id")
        for line in f:
            parts = line.strip().split("\t")
            if parts:
                mag_ids.append(parts[mag_idx])

    # Resolve FASTA paths
    input_path = Path(input_dir)
    genome_paths = []
    for mid in mag_ids:
        for suffix in (".fna", ".fasta", ".fa", ".fna.gz", ".fasta.gz", ".fa.gz"):
            candidate = input_path / f"{mid}{suffix}"
            if candidate.exists():
                genome_paths.append(str(candidate.resolve()))
                break

    # Write genome list
    out_list = Path(output_genome_list)
    out_list.parent.mkdir(parents=True, exist_ok=True)
    with open(out_list, "w") as f:
        for p in genome_paths:
            f.write(p + "\n")

    # Run skani triangle
    out_edges = Path(output_edges)
    out_edges.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "skani", "triangle",
        "-l", str(out_list),
        "-t", str(threads),
        "-E",
        "--min-af", "10",
        "-o", str(out_edges),
    ]
    subprocess.run(cmd, check=True)


def run_cluster(
    edge_list: str, filtered_report: str,
    output_clusters: str, output_derep_report: str,
    ani_threshold: float, min_af: float,
    score_weights: dict,
) -> None:
    """Cluster genomes and select representatives."""
    # Read filtered report
    genomes = {}
    with open(filtered_report) as f:
        header = f.readline().strip().split("\t")
        for line in f:
            values = line.strip().split("\t")
            row = dict(zip(header, values))
            mid = row["mag_id"]
            genomes[mid] = row

    # Parse edges
    edges = parse_edge_list(Path(edge_list))

    # Compute scores and cluster
    scores = compute_composite_scores(genomes, score_weights)
    clusters = greedy_cluster(scores, edges, ani_threshold, min_af)

    # Write species_clusters.tsv
    cluster_cols = [
        "mag_id", "cluster_id", "representative", "is_representative",
        "composite_score", "ani_to_rep", "af_to_rep", "cluster_size",
    ]
    out_clusters = Path(output_clusters)
    out_clusters.parent.mkdir(parents=True, exist_ok=True)
    with open(out_clusters, "w") as f:
        f.write("\t".join(cluster_cols) + "\n")
        for mid in sorted(clusters.keys()):
            c = clusters[mid]
            f.write("\t".join(str(c[col]) for col in cluster_cols) + "\n")

    # Write dereplicated_report.tsv: combined_report columns + cluster info for reps only
    reps = {mid for mid, c in clusters.items() if c["is_representative"]}
    report_header = list(genomes[next(iter(genomes))].keys()) if genomes else []
    extra_cols = ["cluster_id", "cluster_size", "composite_score"]
    out_derep = Path(output_derep_report)
    out_derep.parent.mkdir(parents=True, exist_ok=True)
    with open(out_derep, "w") as f:
        f.write("\t".join(report_header + extra_cols) + "\n")
        for mid in sorted(reps):
            row = genomes[mid]
            c = clusters[mid]
            values = [str(row.get(col, "")) for col in report_header]
            values += [str(c["cluster_id"]), str(c["cluster_size"]),
                       str(round(c["composite_score"], 4))]
            f.write("\t".join(values) + "\n")


if __name__ == "__main__":
    import ast
    import sys

    subcommand = sys.argv[1]

    if subcommand == "triangle":
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--filtered-report", required=True)
        parser.add_argument("--input-dir", required=True)
        parser.add_argument("--output-edges", required=True)
        parser.add_argument("--output-genome-list", required=True)
        parser.add_argument("--threads", type=int, default=64)
        args = parser.parse_args(sys.argv[2:])
        run_triangle(args.filtered_report, args.input_dir,
                     args.output_edges, args.output_genome_list, args.threads)

    elif subcommand == "cluster":
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--edge-list", required=True)
        parser.add_argument("--filtered-report", required=True)
        parser.add_argument("--output-clusters", required=True)
        parser.add_argument("--output-derep-report", required=True)
        parser.add_argument("--ani-threshold", type=float, default=95.0)
        parser.add_argument("--min-af", type=float, default=10.0)
        parser.add_argument("--score-weights", default="{}")
        args = parser.parse_args(sys.argv[2:])
        weights = ast.literal_eval(args.score_weights) if args.score_weights else {}
        run_cluster(args.edge_list, args.filtered_report,
                    args.output_clusters, args.output_derep_report,
                    args.ani_threshold, args.min_af, weights)
```

- [ ] **Step 4: Create rules/dereplicate.smk**

```python
rule skani_triangle:
    """Compute all-vs-all ANI for filtered genomes using skani triangle."""
    input:
        filtered_report=str(OUTDIR / "filtered_report.tsv")
    output:
        edge_list=str(OUTDIR / "dereplicate" / "skani_edges.tsv"),
        genome_list=str(OUTDIR / "dereplicate" / "genome_list.txt"),
    threads: 64
    resources:
        mem_mb=64000
    params:
        input_dir=str(INPUT_DIR)
    shell:
        "python scripts/dereplicate.py triangle "
        "--filtered-report {input.filtered_report} "
        "--input-dir {params.input_dir} "
        "--output-edges {output.edge_list} "
        "--output-genome-list {output.genome_list} "
        "--threads {threads}"


rule dereplicate_cluster:
    """Cluster genomes at species level and select representatives."""
    input:
        edge_list=str(OUTDIR / "dereplicate" / "skani_edges.tsv"),
        filtered_report=str(OUTDIR / "filtered_report.tsv"),
    output:
        clusters=str(OUTDIR / "species_clusters.tsv"),
        derep_report=str(OUTDIR / "dereplicated_report.tsv"),
    threads: 1
    params:
        derep_cfg=config.get("dereplicate", {}),
        quality_cfg=config.get("quality_filter", {}),
    shell:
        "python scripts/dereplicate.py cluster "
        "--edge-list {input.edge_list} "
        "--filtered-report {input.filtered_report} "
        "--output-clusters {output.clusters} "
        "--output-derep-report {output.derep_report} "
        "--ani-threshold {params.derep_cfg[ani_threshold]} "
        "--min-af {params.derep_cfg[min_af]} "
        "--score-weights '{params.derep_cfg[score_weights]}'"
```

- [ ] **Step 5: Run tests and verify they pass**

Run: `python -m pytest tests/test_dereplicate.py -v`

Expected: All 7 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add scripts/dereplicate.py rules/dereplicate.smk tests/test_dereplicate.py
git commit -m "feat: species-level dereplication with skani triangle and greedy clustering"
```

---

### Task 15: Test Fixtures (conftest.py)

**Files:**
- Create: `tests/conftest.py`

- [ ] **Step 1: Create conftest.py**

```python
import os
import pytest
from pathlib import Path

TEST_DATA_DIR = Path(__file__).parent / "data"
TEST_MAGS_DIR = TEST_DATA_DIR / "mags"


@pytest.fixture
def test_mags_dir():
    return TEST_MAGS_DIR


@pytest.fixture
def tmp_output_dir(tmp_path):
    out = tmp_path / "results"
    out.mkdir()
    return out


@pytest.fixture
def default_config():
    return {
        "outdir": "results",
        "steps": ["genome_stats", "checkm2", "gunc", "gtdbtk", "dereplicate"],
        "batch_size": 1000,
        "threads_per_job": 4,
        "max_parallel_jobs": 8,
        "fasta_extensions": [".fna", ".fasta", ".fa", ".fna.gz", ".fasta.gz", ".fa.gz"],
        "db_dir": "databases",
        "db_versions": {
            "checkm2": "1.0.2",
            "gunc": "gtdb_214",
            "gtdbtk": "r226",
        },
        "quality_filter": {
            "high_completeness": 90.0,
            "high_contamination": 5.0,
            "medium_completeness": 60.0,
            "medium_contamination": 10.0,
            "min_quality_score": 50.0,
            "gunc_css_threshold": 0.45,
            "default_filter": "medium_quality",
        },
        "dereplicate": {
            "ani_threshold": 95.0,
            "min_af": 10.0,
            "score_weights": {
                "w_qscore": 1.0,
                "w_completeness": 1.0,
                "w_n50": 0.5,
                "w_contam": 0.5,
                "w_gunc": 0.5,
            },
        },
    }


@pytest.fixture
def tmp_mag_dir(tmp_path):
    """Create a temporary directory with small synthetic FASTA files."""
    mag_dir = tmp_path / "mags"
    mag_dir.mkdir()

    (mag_dir / "test_mag_001.fna").write_text(
        ">contig_1\n" + "ATGC" * 250 + "\n"
        ">contig_2\n" + "GCTA" * 200 + "\n"
    )
    (mag_dir / "test_mag_002.fna").write_text(
        ">contig_1\n" + "ATGC" * 300 + "\n"
    )

    return mag_dir
```

- [ ] **Step 2: Commit**

```bash
git add tests/conftest.py
git commit -m "feat: test fixtures for MAG dirs, config, and temp outputs"
```

---

### Task 16: Container Files

**Files:**
- Create: `container/environment.yml`
- Create: `container/Dockerfile`

- [ ] **Step 1: Create environment.yml**

```yaml
name: magqc
channels:
  - conda-forge
  - bioconda
  - defaults
dependencies:
  - python=3.11
  - pip
  - snakemake=9.18
  - snakemake-executor-plugin-slurm
  - click=8.1
  - pyyaml=6.0
  # Assembly stats
  - seqkit=2.8
  # Genome quality
  - checkm2=1.0.2
  # Chimerism detection (GUNC requires diamond and prodigal)
  - diamond=2.1
  - prodigal=2.6
  # Taxonomy
  - gtdbtk=2.5
  # Dereplication
  - skani=0.2
  # Utilities
  - parallel=20231022
  - pip:
    - gunc>=1.1.0
```

- [ ] **Step 2: Create Dockerfile**

```dockerfile
FROM mambaorg/micromamba:1.5.8

LABEL org.opencontainers.image.title="meta-pipeline-MAGQC"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.description="Quality assessment and taxonomy of MAGs at scale"

COPY container/environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml && \
    micromamba clean --all --yes

COPY . /opt/meta-pipeline-MAGQC
WORKDIR /opt/meta-pipeline-MAGQC

RUN micromamba run -n base pip install -e . --no-deps

RUN chmod +x /opt/meta-pipeline-MAGQC/meta-pipeline-MAGQC && \
    ln -s /opt/meta-pipeline-MAGQC/meta-pipeline-MAGQC /usr/local/bin/meta-pipeline-MAGQC

# Databases are mounted at runtime
VOLUME ["/databases"]
ENV MAGQC_DB_DIR=/databases

ENTRYPOINT ["micromamba", "run", "-n", "base", "meta-pipeline-MAGQC"]
CMD ["--help"]
```

- [ ] **Step 3: Commit**

```bash
git add container/
git commit -m "feat: container spec with Conda environment and Dockerfile"
```

---

### Task 17: MkDocs Documentation

**Files:**
- Create: `mkdocs.yml`
- Create: `docs/index.md`
- Create: `docs/quickstart.md`
- Create: `docs/installation.md`
- Create: `docs/usage/inputs-outputs.md`
- Create: `docs/usage/configuration.md`
- Create: `docs/pipeline/overview.md`
- Create: `docs/pipeline/genome-stats.md`
- Create: `docs/pipeline/checkm2.md`
- Create: `docs/pipeline/gunc.md`
- Create: `docs/pipeline/gtdbtk.md`
- Create: `docs/pipeline/dereplicate.md`
- Create: `docs/outputs/combined-report.md`

- [ ] **Step 1: Create mkdocs.yml**

```yaml
site_name: meta-pipeline-MAGQC
site_description: Quality assessment and taxonomy of MAGs at scale
site_author: Diamond Lab, UC Berkeley
repo_url: https://github.com/diamondlab-ucb/meta-pipeline-MAGQC
repo_name: diamondlab-ucb/meta-pipeline-MAGQC
edit_uri: edit/main/docs/

theme:
  name: material
  palette:
    - scheme: default
      primary: blue-grey
      accent: teal
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      primary: blue-grey
      accent: teal
      toggle:
        icon: material/brightness-4
        name: Switch to light mode
  features:
    - navigation.tabs
    - navigation.expand
    - navigation.top
    - search.suggest
    - search.highlight
    - content.code.copy
    - content.code.annotate

plugins:
  - search

markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.emoji:
      emoji_index: !!python/name:material.extensions.emoji.twemoji
      emoji_generator: !!python/name:material.extensions.emoji.to_svg
  - tables
  - attr_list
  - md_in_html

nav:
  - Overview: index.md
  - Quick Start: quickstart.md
  - Installation: installation.md
  - Using the Pipeline:
    - Inputs & Outputs: usage/inputs-outputs.md
    - Configuration: usage/configuration.md
  - Pipeline Steps:
    - Architecture: pipeline/overview.md
    - Genome Statistics: pipeline/genome-stats.md
    - CheckM2 Quality: pipeline/checkm2.md
    - GUNC Chimerism: pipeline/gunc.md
    - GTDB-Tk Taxonomy: pipeline/gtdbtk.md
    - Dereplication: pipeline/dereplicate.md
  - Output Reference:
    - Combined Report: outputs/combined-report.md
```

- [ ] **Step 2: Create docs pages**

Each docs page should follow the MkDocs Material conventions used in ORFanno. Content should cover: what the step does, which tool is used (with citation), key parameters, and example output. Each page should be concise (50-150 lines).

`docs/index.md`:
```markdown
# meta-pipeline-MAGQC

Quality assessment and taxonomic classification of metagenome-assembled genomes (MAGs) at scale.

## What it does

meta-pipeline-MAGQC takes a directory of MAG FASTA files and produces:

- **Assembly statistics** per genome (N50, GC%, contig count, total length)
- **Completeness and contamination** estimates via CheckM2
- **Chimerism detection** via GUNC
- **Taxonomic classification** via GTDB-Tk (GTDB R10-RS226)
- **Quality-filtered reports** with MIMAG-style quality tiers
- **Species-level dereplication** via skani

Designed for datasets of 10,000+ genomes. Runs on a laptop, a SLURM cluster, or in a Docker container.

## Quick Start

​```bash
pip install -e . --no-deps
meta-pipeline-MAGQC qc -i mags/ -o results/
​```

See [Quick Start](quickstart.md) for full setup instructions.
```

Create similar concise pages for each nav entry. Each pipeline step page should include the tool name, version, citation, and what columns it adds to the combined report.

- [ ] **Step 3: Commit**

```bash
git add mkdocs.yml docs/
git commit -m "docs: MkDocs documentation with pipeline step guides"
```

---

### Task 18: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Create README.md**

Follow ORFanno's README structure: badges, quick start (3-4 commands), overview, input format, output format, CLI reference, tool versions table. Adapt all content for MAGQC's tools and outputs. Include the combined_report.tsv column schema and quality tier definitions.

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: README with quick start, output schema, and quality tiers"
```

---

### Task 19: Integration Test

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Create integration test (slow, opt-in)**

`tests/test_integration.py`:
```python
"""
Integration tests — require installed tools and databases.
Run with: pytest tests/test_integration.py -m slow
"""
import pytest
from pathlib import Path

pytestmark = pytest.mark.slow


@pytest.fixture
def integration_output(tmp_path, test_mags_dir):
    """Run the pipeline on synthetic MAGs and return the output dir."""
    from meta_pipeline_magqc.config import load_and_merge_config
    from meta_pipeline_magqc.runner import run_snakemake

    output_dir = tmp_path / "results"
    cfg = load_and_merge_config(overrides={
        "outdir": str(output_dir),
        "steps": ["genome_stats"],  # Only genome_stats for fast integration test
        "batch_size": 10,
        "max_parallel_jobs": 1,
        "threads_per_job": 1,
    })

    run_snakemake(
        input_dir=test_mags_dir,
        config=cfg,
        profile="local",
        dry_run=False,
    )
    return output_dir


def test_combined_report_exists(integration_output):
    assert (integration_output / "combined_report.tsv").exists()


def test_combined_report_has_all_mags(integration_output):
    report = integration_output / "combined_report.tsv"
    lines = report.read_text().strip().split("\n")
    # Header + one row per MAG in tests/data/mags/
    assert len(lines) >= 2


def test_filtered_report_exists(integration_output):
    assert (integration_output / "filtered_report.tsv").exists()
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_integration.py
git commit -m "test: integration test for genome_stats-only pipeline run"
```

---

### Task 20: Run Full Test Suite

- [ ] **Step 1: Run all unit tests**

Run: `python -m pytest tests/ -v --ignore=tests/test_integration.py`

Expected: All tests PASS.

- [ ] **Step 2: Fix any failures**

Address any import issues, path problems, or test failures.

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: finalize test suite and fix any remaining issues"
```

---

## Notes

- **Test data generation** (Task 1, Step 4): Run the Python script once to create deterministic synthetic FASTAs, then commit them to `tests/data/mags/`.
- **SeqKit fallback**: The genome_stats tests will exercise the BioPython fallback path if SeqKit is not installed. Both paths produce identical output.
- **Batch merge rules** (Tasks 10-12): The `run:` block in merge rules is inline Python that concatenates TSVs with header deduplication — no external script needed.
- **Quality tier edge cases**: The `test_merge_reports.py` tests cover all 5 tiers plus missing-data scenarios.
- **Bi-directional AF**: `test_dereplicate.py::test_greedy_cluster_af_filter` explicitly tests that high ANI with low one-directional AF does NOT result in clustering.
