# meta-pipeline-MAGQC: Build Instructions for Claude

## Overview

You are building **meta-pipeline-MAGQC**, a modular Snakemake pipeline for quality assessment and taxonomic classification of metagenome-assembled genomes (MAGs) at scale (≥10,000 genomes). This pipeline is a sibling project to **meta-pipeline-ORFanno** and must mirror its architectural conventions exactly.

The pipeline is developed by the Diamond Lab at UC Berkeley's Innovative Genomics Institute.

---

## Architecture Reference: meta-pipeline-ORFanno

meta-pipeline-MAGQC must replicate the following architectural patterns from meta-pipeline-ORFanno:

### Project Layout

```
meta-pipeline-MAGQC/
│
├── meta-pipeline-MAGQC              # Bash shim launcher (see below)
├── Snakefile                        # Master orchestrator
├── pyproject.toml                   # Package metadata
├── README.md
├── mkdocs.yml                       # MkDocs Material documentation config
│
├── config/
│   ├── config.yaml                  # Default configuration
│   └── profiles/
│       ├── local/config.yaml        # Local execution profile
│       └── slurm/config.yaml        # SLURM cluster profile
│
├── rules/                           # Snakemake rule modules
│   ├── common.smk                   # MAG discovery, batch helpers, wildcard constraints
│   ├── genome_stats.smk             # Per-MAG: assembly statistics via SeqKit
│   ├── checkm2.smk                  # Batch: completeness and contamination
│   ├── gunc.smk                     # Batch: chimerism detection
│   ├── gtdbtk.smk                   # Batch: taxonomy classification
│   ├── aggregate.smk                # Merge all outputs + quality classification
│   └── dereplicate.smk              # Species-level dereplication via skani
│
├── scripts/                         # Python scripts called by Snakemake rules
│   ├── __init__.py
│   ├── genome_stats.py              # SeqKit wrapper + N50 calculation
│   ├── run_checkm2.py               # Batch runner for CheckM2 predict
│   ├── run_gunc.py                  # Batch runner for GUNC run
│   ├── run_gtdbtk.py                # Batch runner for GTDB-Tk classify_wf
│   ├── merge_reports.py             # Left-join all outputs + quality tier assignment
│   └── dereplicate.py               # skani triangle + greedy clustering + rep selection
│
├── src/meta_pipeline_magqc/         # Python package (CLI, config, runner, resources)
│   ├── __init__.py                  # Contains __version__ = "0.1.0"
│   ├── cli.py                       # Click CLI entry point
│   ├── config.py                    # YAML config load/merge/validate
│   ├── runner.py                    # Snakemake API (local) / CLI (SLURM) dispatch
│   └── resources.py                 # CPU/RAM/GPU auto-detection
│
├── container/
│   ├── environment.yml              # Conda/mamba environment specification
│   └── Dockerfile                   # Container build (micromamba-based)
│
├── tests/
│   ├── conftest.py                  # Shared fixtures (tmp dirs, mock FASTAs)
│   ├── data/
│   │   └── mags/                    # Small synthetic test FASTA files
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_genome_stats.py
│   ├── test_checkm2.py
│   ├── test_gunc.py
│   ├── test_gtdbtk.py
│   ├── test_merge_reports.py
│   ├── test_dereplicate.py
│   ├── test_runner.py
│   └── test_integration.py          # @pytest.mark.slow — requires installed tools
│
└── docs/                            # MkDocs Material documentation
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

### Bash Shim Launcher

File: `meta-pipeline-MAGQC` (executable, no extension)

```bash
#!/usr/bin/env bash
# meta-pipeline-MAGQC launcher
# Thin shim that delegates to the Python CLI entry point.
set -euo pipefail

exec python -m meta_pipeline_magqc.cli "$@"
```

### pyproject.toml

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

---

## CLI Design (src/meta_pipeline_magqc/cli.py)

Mirror ORFanno's Click CLI structure exactly. The CLI must support:

```
meta-pipeline-MAGQC --version
meta-pipeline-MAGQC qc --input/-i DIR --output/-o DIR [OPTIONS]
meta-pipeline-MAGQC db update [--db-dir DIR] [--force]
meta-pipeline-MAGQC db status [--db-dir DIR]
```

### `qc` command options (replaces ORFanno's `annotate`):

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--input / -i` | Path (dir, required) | — | Directory of input MAG FASTA files |
| `--output / -o` | Path (required) | — | Output directory |
| `--profile` | Choice[local, slurm] | local | Execution profile |
| `--steps` | String (comma-sep) | None (=all) | Steps to run: genome_stats,checkm2,gunc,gtdbtk,dereplicate |
| `--skip` | String (comma-sep) | None | Steps to skip |
| `--config` | Path | None | Custom config YAML |
| `--dry-run` | Flag | False | Show DAG without executing |
| `--jobs / -j` | Int | None | Override max parallel jobs |

### Config, Runner, Resources modules

Copy the patterns from ORFanno exactly:

- **config.py**: `load_config()`, `merge_config()` (deep merge), `validate_config()`, `load_and_merge_config()`. Define `VALID_STEPS = {"genome_stats", "checkm2", "gunc", "gtdbtk", "dereplicate"}`.
- **runner.py**: `run_snakemake()` dispatching to `_run_snakemake_api()` (local) or `_run_snakemake_cli()` (SLURM). Uses Snakemake 8/9 Python API with `SnakemakeApi`, `ConfigSettings`, `ResourceSettings`, etc.
- **resources.py**: `ResourceInfo` dataclass with `cpu_count`, `gpu_available`, `gpu_type`, `gpu_device_count`. Same `detect_cpu_count()`, `detect_gpu()`, `detect_resources()` functions as ORFanno.

---

## Default Configuration (config/config.yaml)

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
  # Both AF(query→ref) and AF(ref→query) must exceed this value.
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

---

## SLURM Profile (config/profiles/slurm/config.yaml)

Target hardware: multi-node HPC or GCP with 64 cores and 512 GB RAM per node.

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
  dereplicate:
    runtime: 30
    mem_mb: 16000

group-components: 4
```

### Local Profile (config/profiles/local/config.yaml)

```yaml
# Local profile: run everything on the current machine.
printshellcmds: true
keep-going: true
rerun-incomplete: true
```

---

## Snakemake Rules — Detailed Specifications

### Snakefile (master orchestrator)

Mirror ORFanno's Snakefile structure:

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

# Always include common and genome_stats
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

### rules/common.smk

Must provide:

1. **`discover_mag_ids(input_dir)`** — Return sorted list of MAG IDs from FASTA files. Support extensions: `.fasta`, `.fa`, `.fna`, `.fasta.gz`, `.fa.gz`, `.fna.gz`. Strip the extension to derive the MAG ID.

2. **`mag_fasta(input_dir, mag_id)`** — Return the path to the FASTA file for a given MAG ID.

3. **`make_batches(mag_ids, batch_size)`** — Split MAG IDs into numbered batches. Return a dict mapping batch ID strings (e.g., `"batch_000"`, `"batch_001"`) to lists of MAG IDs. Example: 2,500 MAGs with batch_size=1000 → `{"batch_000": [...1000...], "batch_001": [...1000...], "batch_002": [...500...]}`.

4. **`create_batch_dir(batch_id, mag_ids, input_dir, batch_dir)`** — Create a directory of symlinks for a batch. For each MAG ID in the batch, symlink the original FASTA into `batch_dir/batch_id/`. This is how batch tools (CheckM2, GUNC, GTDB-Tk) receive their input — they take a directory of genomes.

5. **Wildcard constraints**: `mag_id="[A-Za-z0-9_.\\-]+"`, `batch_id="batch_\\d+"`.

### rules/genome_stats.smk — Per-MAG Assembly Statistics

**Tool**: SeqKit (Shen et al., 2016, PLOS ONE)

**Justification**: SeqKit is written in Go, processes 10k+ genomes in minutes, and is the standard CLI toolkit for FASTA/Q manipulation. At 10k+ genomes this is orders of magnitude faster than BioPython.

**Rule**:
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

**scripts/genome_stats.py** must:

1. Run `seqkit stats --tabular` on the input FASTA to get num_seqs, sum_len, min_len, avg_len, max_len.
2. Run `seqkit fx2tab --name --only-id --gc` to get per-contig GC content, then compute a length-weighted genome-wide GC%.
3. Compute N50 from per-contig lengths (pure Python — sort lengths descending, cumulative sum to half total, return the length at that threshold).
4. Write a two-row TSV (header + data) with columns: `mag_id`, `total_length_bp`, `gc_percent`, `contig_count`, `n50_bp`, `largest_contig_bp`.

**Fallback**: If SeqKit is not available, fall back to BioPython (same logic as ORFanno's genome_stats.py). Use `shutil.which("seqkit")` to check availability.

### rules/checkm2.smk — Batch Quality Estimation

**Tool**: CheckM2 v1.0.2 (Chklovski et al., 2023, Nature Methods)

**Justification**: CheckM2 uses a gradient-boosted ML model for completeness/contamination estimation. It is ~5–10× faster than CheckM1, more robust for novel lineages, and is the recommended tool for MAG quality in contemporary metagenomics workflows. The GTDB R10-RS226 release now requires CheckM2 quality estimates as part of its QC criteria.

**Rule pattern** (batch-mode):

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
        # Concatenate TSVs, keeping header from first file only
        ...
```

**scripts/run_checkm2.py** must:

1. Accept args: `input_dir`, `output_dir`, `output_tsv`, `threads`.
2. Run: `checkm2 predict --input <input_dir> --output-directory <output_dir> --threads <threads> --force`
3. Parse the CheckM2 output file (`quality_report.tsv` in the output directory).
4. Copy/rename to the expected output location.
5. The output TSV must contain at minimum: `mag_id`, `completeness`, `contamination`, `completeness_model_used`, `translation_table_used`.

### rules/gunc.smk — Batch Chimerism Detection

**Tool**: GUNC v1.1.0 (Orakov et al., 2021, Genome Biology)

**Justification**: GUNC detects non-redundant genome chimerism that CheckM2 systematically misses. It estimates that 15–30% of pre-filtered "high-quality" MAGs are undetected chimeras. GUNC is complementary to CheckM2: CheckM2 detects redundant contamination (duplicate marker genes), while GUNC detects non-redundant contamination (contigs from unrelated lineages). Using both together is increasingly standard practice in high-impact metagenomics publications.

**GitHub**: grp-bork/gunc — ~87 stars, actively maintained, v1.1.0 released 2025 with GTDB r214 DB support.

**Rule pattern**: Same batch setup/run/merge pattern as CheckM2.

```python
rule gunc_setup_batch:
    input:
        fastas=lambda wc: [mag_fasta(INPUT_DIR, mid) for mid in BATCHES[wc.batch_id]]
    output:
        batch_dir=directory(str(OUTDIR / "batches" / "gunc" / "{batch_id}" / "input"))
    threads: 1
    run:
        create_batch_dir(wildcards.batch_id, BATCHES[wildcards.batch_id],
                         INPUT_DIR, output.batch_dir)


rule gunc_batch:
    input:
        batch_dir=str(OUTDIR / "batches" / "gunc" / "{batch_id}" / "input")
    output:
        results=str(OUTDIR / "batches" / "gunc" / "{batch_id}" / "gunc_output.tsv")
    threads: 16
    params:
        outdir=str(OUTDIR / "batches" / "gunc" / "{batch_id}" / "output"),
        db_path=config.get("gunc_db_path") or "",
        db_type=config.get("gunc", {}).get("db_type", "gtdb_214")
    shell:
        "python scripts/run_gunc.py {input.batch_dir} {params.outdir} {output.results} {threads} {params.db_type}"


rule gunc_merge:
    input:
        expand(str(OUTDIR / "batches" / "gunc" / "{batch_id}" / "gunc_output.tsv"),
               batch_id=BATCH_IDS)
    output:
        str(OUTDIR / "gunc_chimerism.tsv")
    threads: 1
    run:
        # Concatenate TSVs, keeping header from first file only
        ...
```

**scripts/run_gunc.py** must:

1. Run: `gunc run --input_dir <input_dir> --out_dir <out_dir> --threads <threads> --db_file <db_path>`
2. Parse GUNC's `GUNC.maxCSS_level.tsv` output.
3. Output TSV with columns: `mag_id`, `css` (clade separation score), `rrs` (reference representation score), `contamination_portion`, `taxonomic_level`, `pass_gunc` (boolean: css < threshold).

### rules/gtdbtk.smk — Batch Taxonomy Classification

**Tool**: GTDB-Tk v2.5.0+ (Chaumeil et al., 2022, Bioinformatics)

**Justification**: GTDB-Tk is the de facto standard for genome-based prokaryotic taxonomy. There is no credible competitor. It uses the GTDB (Genome Taxonomy Database), which provides a phylogenetically consistent and rank-normalized taxonomy. Pinned to GTDB R10-RS226 (732,475 genomes, 143,614 species clusters).

**GitHub**: Ecogenomics/GTdBTk — ~600+ stars, actively maintained, aligned with GTDB releases.

**Memory note**: The pplacer step requires ~85 GB RAM per instance. `pplacer_cpus` should be kept at 1 to avoid memory multiplication. This is the primary bottleneck for GTDB-Tk at scale.

**Rule pattern**: Same batch setup/run/merge as above.

```python
rule gtdbtk_setup_batch:
    input:
        fastas=lambda wc: [mag_fasta(INPUT_DIR, mid) for mid in BATCHES[wc.batch_id]]
    output:
        batch_dir=directory(str(OUTDIR / "batches" / "gtdbtk" / "{batch_id}" / "input"))
    threads: 1
    run:
        create_batch_dir(wildcards.batch_id, BATCHES[wildcards.batch_id],
                         INPUT_DIR, output.batch_dir)


rule gtdbtk_batch:
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
        skip_ani=config.get("gtdbtk", {}).get("skip_ani_screen", False)
    shell:
        "python scripts/run_gtdbtk.py {input.batch_dir} {params.outdir} {output.results} "
        "{threads} {params.pplacer_cpus} {params.skip_ani}"


rule gtdbtk_merge:
    input:
        expand(str(OUTDIR / "batches" / "gtdbtk" / "{batch_id}" / "gtdbtk_output.tsv"),
               batch_id=BATCH_IDS)
    output:
        str(OUTDIR / "gtdbtk_taxonomy.tsv")
    threads: 1
    run:
        # Concatenate TSVs, keeping header from first file only
        ...
```

**scripts/run_gtdbtk.py** must:

1. Run: `gtdbtk classify_wf --genome_dir <input_dir> --out_dir <out_dir> --cpus <threads> --pplacer_cpus <pplacer_cpus> [--skip_ani_screen if flag set] --extension <ext>`
2. Parse both `gtdbtk.bac120.summary.tsv` and `gtdbtk.ar53.summary.tsv` (bacteria and archaea results).
3. Merge into a single output TSV with columns: `mag_id`, `domain`, `phylum`, `class`, `order`, `family`, `genus`, `species`, `classification` (full GTDB string), `fastani_reference`, `fastani_ani`, `fastani_af`, `classification_method`, `note`, `warnings`.

### rules/aggregate.smk — Merge + Quality Filter

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
        quality_cfg=config.get("quality_filter", {})
    shell:
        "python scripts/merge_reports.py "
        "--stats-dir {OUTDIR}/individual "
        "--checkm2 {input.checkm2} "
        "--gunc {input.gunc} "
        "--gtdbtk {input.gtdbtk} "
        "--output-combined {output.combined} "
        "--output-filtered {output.filtered} "
        "--quality-config '{params.quality_cfg}'"
```

**scripts/merge_reports.py** must:

1. Read all per-MAG genome_stats.tsv files from the individual/ directory and concatenate.
2. Left-join checkm2_quality.tsv on mag_id.
3. Left-join gunc_chimerism.tsv on mag_id.
4. Left-join gtdbtk_taxonomy.tsv on mag_id.
5. Compute derived columns:
   - `quality_score`: completeness − 5 × contamination
   - `quality_tier`: assigned using the logic below
6. Write `combined_report.tsv` (all genomes, all columns).
7. Write `filtered_report.tsv` (genomes at or above the `default_filter` tier).

### Quality Tier Assignment Logic

```python
def assign_quality_tier(row, cfg):
    """
    Assign a quality tier to a genome based on CheckM2 and GUNC results.

    Tiers (in order of precedence):
      high_quality       : comp >= 90, contam < 5,  qscore >= 50, GUNC pass
      medium_quality     : comp >= 60, contam < 10, qscore >= 50, GUNC pass
      medium_chimeric    : meets medium_quality thresholds but GUNC flagged chimeric
      low_quality        : comp < 60 OR contam >= 10 OR qscore < 50
      low_chimeric       : meets low_quality AND GUNC flagged chimeric
    """
    comp = row.get("completeness", 0)
    contam = row.get("contamination", 100)
    qscore = comp - 5 * contam
    gunc_pass = row.get("pass_gunc", True)  # True if GUNC not run

    is_high = (comp >= cfg["high_completeness"]
               and contam < cfg["high_contamination"]
               and qscore >= cfg["min_quality_score"])
    is_medium = (comp >= cfg["medium_completeness"]
                 and contam < cfg["medium_contamination"]
                 and qscore >= cfg["min_quality_score"])

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
```

### combined_report.tsv Column Schema

The final combined report must contain one row per genome with these columns (in order):

```
mag_id
total_length_bp
gc_percent
contig_count
n50_bp
largest_contig_bp
completeness
contamination
completeness_model_used
quality_score
css
rrs
contamination_portion
gunc_taxonomic_level
pass_gunc
domain
phylum
class
order
family
genus
species
classification
fastani_reference
fastani_ani
fastani_af
classification_method
quality_tier
```

### rules/dereplicate.smk — Species-Level Genome Dereplication

**Tool**: skani v0.2+ (Shaw & Yu, 2023, Nature Methods)

**Justification**: skani computes ANI via sparse approximate alignments and is >20× faster than FastANI while being more accurate for fragmented, incomplete MAGs. It natively reports bi-directional aligned fraction, which is essential for the user's requirement of ≥10% bi-directional genome overlap. The `skani triangle` command computes all-vs-all ANI as an edge list — the exact input needed for clustering. GitHub (bluenote-1577/skani) has ~230 stars and is actively developed.

**Design**: Dereplication operates on the filtered set of genomes (those passing the `default_filter` quality tier). It uses a greedy clustering approach: genomes are sorted by a composite quality score, then iteratively assigned to clusters based on ANI and aligned fraction thresholds.

**Rule pattern**:

```python
rule skani_triangle:
    """Compute all-vs-all ANI for filtered genomes using skani triangle."""
    input:
        filtered_report=str(OUTDIR / "filtered_report.tsv")
    output:
        edge_list=str(OUTDIR / "dereplicate" / "skani_edges.tsv"),
        genome_list=str(OUTDIR / "dereplicate" / "genome_list.txt")
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
        filtered_report=str(OUTDIR / "filtered_report.tsv")
    output:
        clusters=str(OUTDIR / "species_clusters.tsv"),
        derep_report=str(OUTDIR / "dereplicated_report.tsv")
    threads: 1
    params:
        derep_cfg=config.get("dereplicate", {}),
        quality_cfg=config.get("quality_filter", {})
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

**scripts/dereplicate.py** must implement two subcommands:

#### Subcommand: `triangle`

1. Read `filtered_report.tsv` to get the list of MAG IDs that passed quality filtering.
2. For each MAG ID, resolve its FASTA path in the input directory.
3. Write a `genome_list.txt` (one path per line) for the filtered genomes.
4. Run: `skani triangle -l <genome_list.txt> -t <threads> -E --min-af 10 -o <edge_list.tsv>`
   - `-E` outputs edge list format (not matrix)
   - `--min-af 10` pre-filters pairs below 10% AF to reduce output size
5. The edge list output has columns: `Ref_file`, `Query_file`, `ANI`, `Align_fraction_ref`, `Align_fraction_query`, `Ref_name`, `Query_name`.

#### Subcommand: `cluster`

1. Read the skani edge list and the filtered_report.tsv.

2. **Compute composite quality score** for each genome:

```python
def compute_composite_score(row, weights):
    """
    Compute a normalized composite quality score for representative selection.

    Each metric is min-max normalized to [0, 1] across the filtered genome set,
    then weighted and summed. Higher score = better representative.

    Metrics:
      - quality_score:  completeness - 5*contamination (higher is better)
      - completeness:   raw completeness (higher is better)
      - log10(N50):     assembly contiguity (higher is better)
      - 100 - contam:   inverse contamination (higher is better)
      - 1 - CSS:        inverse chimerism score (higher is better, 1.0 if GUNC not run)
    """
    raw = {
        "qscore": row["quality_score"],
        "completeness": row["completeness"],
        "n50": math.log10(max(row["n50_bp"], 1)),
        "contam": 100.0 - row["contamination"],
        "gunc": 1.0 - row.get("css", 0.0),
    }
    # normalize() is min-max across all filtered genomes, pre-computed
    score = (
        weights["w_qscore"] * normalize(raw["qscore"]) +
        weights["w_completeness"] * normalize(raw["completeness"]) +
        weights["w_n50"] * normalize(raw["n50"]) +
        weights["w_contam"] * normalize(raw["contam"]) +
        weights["w_gunc"] * normalize(raw["gunc"])
    )
    return score
```

3. **Greedy clustering algorithm**:

```python
def greedy_cluster(genomes, edges, ani_threshold, min_af):
    """
    Greedy species-level clustering.

    1. Sort genomes by composite_score descending.
    2. Initialize: all genomes unclustered.
    3. For each genome in sorted order:
       a. If already assigned to a cluster, skip.
       b. Make it a new cluster representative.
       c. For all unclustered genomes connected to it in the edge list
          where ANI >= ani_threshold AND
                AF(ref→query) >= min_af AND
                AF(query→ref) >= min_af:
          → Assign them to this cluster.
    4. Return cluster assignments.
    """
    ...
```

The **bi-directional AF check** is critical: both `Align_fraction_ref >= min_af` AND `Align_fraction_query >= min_af` must be true. This ensures neither genome is a small fragment that happens to be contained within the other — both genomes must share at least 10% overlap in both directions.

4. **Output files**:

**`species_clusters.tsv`** — One row per genome, columns:
```
mag_id
cluster_id          # e.g., "cluster_0001"
representative      # mag_id of the cluster representative
is_representative   # True/False
composite_score     # the score used for ranking
ani_to_rep          # ANI to the cluster representative (100.0 for the rep itself)
af_to_rep           # aligned fraction to rep
cluster_size        # number of genomes in this cluster
```

**`dereplicated_report.tsv`** — Subset of `combined_report.tsv` containing only cluster representative genomes, with additional columns: `cluster_id`, `cluster_size`, `composite_score`. This is the final "one genome per species" output.

### Updated combined_report.tsv Column Schema

The final combined report is unchanged — dereplication produces separate output files. The `species_clusters.tsv` and `dereplicated_report.tsv` are the dereplication-specific outputs.

---

## Container Specification

### container/environment.yml

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

### container/Dockerfile

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

---

## Testing Specifications

### Test Strategy

Two tiers:

1. **Unit tests** (always run, fast, no external tools needed):
   - `test_config.py`: config loading, merging, validation, invalid step rejection.
   - `test_genome_stats.py`: create small synthetic FASTAs, verify stats computation (N50, GC, length).
   - `test_checkm2.py`: mock `subprocess.run` for `checkm2 predict`, verify output parsing.
   - `test_gunc.py`: mock `subprocess.run` for `gunc run`, verify output parsing and pass/fail logic.
   - `test_gtdbtk.py`: mock `subprocess.run` for `gtdbtk classify_wf`, verify output parsing from both bac120 and ar53 summary files.
   - `test_merge_reports.py`: test quality tier assignment logic with known inputs. Cover all five tiers plus edge cases (missing GUNC data, missing CheckM2 data).
   - `test_cli.py`: test Click CLI invocation, argument validation, dry-run mode.
   - `test_runner.py`: mock Snakemake invocation, verify config is passed correctly.

2. **Integration tests** (`@pytest.mark.slow`, opt-in):
   - `test_integration.py`: run the full pipeline on 2-3 small synthetic genomes with real tools installed. Requires CheckM2, GUNC, GTDB-Tk, and SeqKit to be in PATH and databases downloaded.

### Test Data (tests/data/mags/)

Create 2-3 small synthetic FASTA files (e.g., random DNA sequences of 50-100 contigs, ~500kb total). These are for testing genome_stats computation only — CheckM2/GUNC/GTDB-Tk tests use mocked subprocess calls.

### conftest.py fixtures

```python
@pytest.fixture
def tmp_mag_dir(tmp_path):
    """Create a temporary directory with small synthetic FASTA files."""
    ...

@pytest.fixture
def sample_config():
    """Return a valid default config dict for testing."""
    ...

@pytest.fixture
def mock_checkm2_output():
    """Return mock CheckM2 quality_report.tsv content."""
    ...

@pytest.fixture
def mock_gunc_output():
    """Return mock GUNC maxCSS_level.tsv content."""
    ...

@pytest.fixture
def mock_gtdbtk_output():
    """Return mock GTDB-Tk summary TSV content."""
    ...
```

---

## MkDocs Documentation

### mkdocs.yml

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

---

## Build Order

Build the pipeline in this order, testing each module before proceeding:

1. **Project scaffold**: directory structure, pyproject.toml, bash shim, `__init__.py` files.
2. **src/meta_pipeline_magqc/**: config.py → resources.py → runner.py → cli.py (copy and adapt from ORFanno).
3. **config/**: config.yaml, profiles/local/config.yaml, profiles/slurm/config.yaml.
4. **rules/common.smk**: MAG discovery, batching, symlink helpers, wildcard constraints.
5. **Snakefile**: master orchestrator with conditional includes.
6. **rules/genome_stats.smk + scripts/genome_stats.py**: SeqKit-based stats with BioPython fallback.
7. **rules/checkm2.smk + scripts/run_checkm2.py**: batch setup, run, merge.
8. **rules/gunc.smk + scripts/run_gunc.py**: batch setup, run, merge.
9. **rules/gtdbtk.smk + scripts/run_gtdbtk.py**: batch setup, run, merge.
10. **rules/aggregate.smk + scripts/merge_reports.py**: left-join all outputs, quality tier logic.
11. **rules/dereplicate.smk + scripts/dereplicate.py**: skani triangle, greedy clustering, representative selection.
12. **tests/**: conftest.py, unit tests for each module.
13. **container/**: environment.yml, Dockerfile.
14. **docs/**: MkDocs documentation pages.

---

## Critical Implementation Notes

1. **All code must be well-commented and parsimonious.** Follow the coding style of ORFanno.

2. **Batch symlink directories**: CheckM2, GUNC, and GTDB-Tk all accept a directory of FASTA files as input. The batching strategy creates symlink directories so each batch tool sees only its assigned genomes. Never copy FASTA files — always symlink.

3. **Checkpointing**: Each batch produces independent output. If a pipeline run fails partway through, Snakemake's `--rerun-incomplete` flag will only re-run failed batches. This is critical for 10k+ genome datasets.

4. **GTDB-Tk memory**: pplacer needs ~85 GB RAM per instance. The SLURM profile allocates 120 GB to provide a safety buffer. Never set `pplacer_cpus` > 1 unless you have proportionally more RAM.

5. **GUNC database**: GUNC v1.1.0 supports ProGenomes 3, GTDB r214, and custom databases. Pin to `gtdb_214` by default for consistency with the GTDB taxonomy framework.

6. **SeqKit fallback**: If SeqKit is not installed, genome_stats.py must fall back to BioPython (using `Bio.SeqIO` and `Bio.SeqUtils.gc_fraction`). Use `shutil.which("seqkit")` to check at runtime.

7. **Merge logic**: Use pandas or pure Python dict-based left-joins. If a step was skipped (e.g., GUNC not in STEPS), the corresponding columns should be filled with NA/empty values in the combined report.

8. **Dereplication depends on quality filtering**: The dereplicate step takes `filtered_report.tsv` as input, meaning only genomes that pass the `default_filter` quality tier are considered for dereplication. The Snakemake DAG enforces this dependency. If `dereplicate` is in STEPS but `checkm2` is not, dereplication should still work but quality scores will be limited to assembly statistics only.

9. **skani bi-directional AF**: The user requires ≥10% bi-directional genome overlap. skani's edge list reports `Align_fraction_ref` and `Align_fraction_query` separately. Both must be ≥ the `min_af` threshold. This is critical because a small MAG fragment may have high AF to a complete genome but the reverse AF will be very low — such pairs should NOT be clustered together.

10. **Composite score normalization**: Min-max normalization must be computed across the full filtered genome set BEFORE clustering begins. If all genomes have identical values for a metric (e.g., all pass GUNC with CSS=0), that metric's normalized value should be set to 1.0 for all genomes (avoid division by zero).

8. **Naming convention**: All Python module files use snake_case. All output files use snake_case. Batch directories are named `batch_000`, `batch_001`, etc. (zero-padded to 3 digits, or more if needed for >1000 batches).

---

## References

- **CheckM2**: Chklovski A, et al. (2023) CheckM2: a rapid, scalable and accurate tool for assessing microbial genome quality using machine learning. *Nature Methods*, 20:1203–1212.
- **GUNC**: Orakov A, et al. (2021) GUNC: detection of chimerism and contamination in prokaryotic genomes. *Genome Biology*, 22:178.
- **GTDB-Tk**: Chaumeil P-A, et al. (2022) GTDB-Tk v2: memory friendly classification with the Genome Taxonomy Database. *Bioinformatics*, 38:5315–5316.
- **GTDB R10-RS226**: Parks DH, et al. (2026) GTDB release 10: a complete and systematic taxonomy for 715,230 bacterial and 17,245 archaeal genomes. *Nucleic Acids Research*, 54:D743–D754.
- **SeqKit**: Shen W, et al. (2016) SeqKit: a cross-platform and ultrafast toolkit for FASTA/Q file manipulation. *PLOS ONE*, 11:e0163962.
- **skani**: Shaw J & Yu YW (2023) Fast and robust metagenomic sequence comparison through sparse chaining with skani. *Nature Methods*, 20:1633–1634.
- **MIMAG**: Bowers RM, et al. (2017) Minimum information about a single amplified genome (MISAG) and a metagenome-assembled genome (MIMAG) of bacteria and archaea. *Nature Biotechnology*, 35:725–731.
