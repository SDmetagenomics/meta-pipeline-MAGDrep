<div align="center">

# meta-pipeline-MAGDrep

**Quality assessment, taxonomic classification, and species-level dereplication of metagenome-assembled genomes -- at scale.**

[![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Snakemake](https://img.shields.io/badge/snakemake-9.16-039475?logo=snakemake&logoColor=white)](https://snakemake.readthedocs.io/)
[![License](https://img.shields.io/badge/license-MIT-yellow)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-93%2F93%20passing-brightgreen)]()
[![Version](https://img.shields.io/badge/version-1.3.0-brightgreen)]()

</div>

---

## What it does

Take a directory of MAGs (or a list of MAG directories), get back a clean species-level catalog with taxonomy, quality metrics, and per-cluster representatives.

```mermaid
flowchart LR
    A["<b>MAGs</b><br/>10-100,000 FASTA"] --> B["<b>genome_stats</b><br/>SeqKit"]
    A --> C1["<b>checkm1</b><br/>marker-gene QC<br/>(optional)"]
    A --> C2["<b>checkm2</b><br/>neural-net QC"]
    A --> D["<b>gtdbtk</b><br/>taxonomy"]
    B --> E["<b>merge_reports</b><br/>quality tiers"]
    C1 --> E
    C2 --> E
    D --> E
    E --> F["<b>skani triangle</b><br/>all-vs-all ANI"]
    F --> G["<b>dereplicate</b><br/>UPGMA at 95% ANI"]
    G --> H["<b>summary</b><br/>species-level catalog"]
```

---

## Quick start

```bash
# 1. Clone + install (creates magdrep conda env with all tools)
git clone https://github.com/SDmetagenomics/meta-pipeline-MAGDrep.git
cd meta-pipeline-MAGDrep
make install
conda activate magdrep

# 2. Download reference databases (~88 GB total, one-time)
meta-pipeline-MAGDrep db update
meta-pipeline-MAGDrep db status      # should read "All databases ready"

# 3. Run the pipeline
meta-pipeline-MAGDrep run -i mags/ -o results/
```

Need more detail? See the [**Program Guide**](docs/program-guide.md) for rationale, installation, functionality, runtime, and use-case walkthroughs.

---

## Pipeline steps

| Step | Tool | What | Database |
|---|---|---|---|
| `genome_stats` | SeqKit 2.13 | Length, GC, N50, contig count | -- |
| `checkm1` *(optional)* | CheckM1 1.2.5 | Marker-gene completeness/contamination + **strain heterogeneity** | CheckM1 DB (~1.4 GB) |
| `checkm2` | CheckM2 1.1.0 | Completeness + contamination (neural net) | CheckM2 diamond DB (~3 GB) |
| `gtdbtk` | GTDB-Tk 2.5.2 | Taxonomy -- GTDB release 226 | GTDB-Tk r226 (~85 GB) |
| `dereplicate` | skani 0.3.1 + scipy | Species clustering (UPGMA at 95% ANI) | -- |

Each step is batched so memory stays bounded on 10k+ genome datasets. CheckM1, CheckM2, and GTDB-Tk run **concurrently** by default and can be routed to different SLURM partitions.

### Running CheckM1

CheckM1 lives in a sibling conda environment (`magdrep-checkm1`, created automatically by `make install`) because CheckM1 requires Python < 3.12 while CheckM2 requires Python >= 3.12. The pipeline calls CheckM1 via `conda run -n magdrep-checkm1` -- no manual environment switching needed.

By default only CheckM2 runs. To add CheckM1 (or swap for it), include it in `--steps`:

```bash
# CheckM1 + CheckM2 side-by-side (unlocks strain_heterogeneity for the composite score)
meta-pipeline-MAGDrep run -i mags/ -o results/ \
    --steps genome_stats,checkm1,checkm2,gtdbtk,dereplicate

# Only CheckM1 (skip CheckM2 entirely)
meta-pipeline-MAGDrep run -i mags/ -o results/ --skip checkm2 \
    --steps genome_stats,checkm1,gtdbtk,dereplicate
```

When both run:
- **CheckM2 values** populate the canonical `completeness` / `contamination` columns (better neural-net model).
- **CheckM1 values** are preserved as `checkm1_completeness` / `checkm1_contamination` for side-by-side comparison.
- **`strain_heterogeneity`** always comes from CheckM1 -- which activates the `C` term in the dereplication composite score.

On local execution, CheckM1 claims all cores first (pplacer bottleneck, capped at 4 pplacer threads by default). After it finishes, CheckM2 and GTDB-Tk run concurrently.

---

## Specifying input MAGs

Two options for `-i / --input`:

**1. A directory** of FASTAs (`.fna`, `.fa`, `.fasta`, optionally gzipped):

```bash
meta-pipeline-MAGDrep run -i /path/to/mags/ -o results/
```

**2. A text file** with one MAG **directory** per line -- useful when MAGs are spread across multiple sample-specific bin directories:

```bash
# mag_dirs.txt
/lab/project_A/binning/bins/
/lab/project_B/reassembly/bins/
~/other_project/drep_output/dereplicated_genomes/
# lines starting with # are comments; blanks are ignored
```

```bash
meta-pipeline-MAGDrep run -i mag_dirs.txt -o results/
```

Relative paths resolve against the list file's directory. `~` expands to `$HOME`. Every FASTA in each listed directory is discovered automatically. The MAG ID for each genome is the filename stem (minus a recognized FASTA suffix); duplicate IDs produce a clear error unless `--rename` is used.

### The `--rename` flag

When genome IDs collide (common when combining bins from multiple assemblies) or contig headers are duplicated, pass `--rename`:

```bash
meta-pipeline-MAGDrep run -i mag_dirs.txt -o results/ --rename
```

This resolves duplicate genome IDs by appending `_A`, `_B`, ... suffixes and rewrites every contig header to `{genome_id}_scaffold_{N}`. Normalized copies are written to `results/input_genomes/`. Without `--rename`, duplicates produce a loud error.

---

## Output layout

```
results/
├── summary_report.tsv          # compact: stats + quality + taxonomy, one row per MAG
├── combined_report.tsv         # full: every column from every tool
├── filtered_report.tsv         # quality-filtered subset
├── genome_stats/<mag>/genome_stats.tsv
├── checkm1/                    # (present only when checkm1 step is enabled)
│   ├── checkm1_quality.tsv     # merged CheckM1 output
│   └── batches/<batch>/raw/    # full CheckM1 run
├── checkm2/
│   ├── checkm2_quality.tsv     # merged CheckM2 output
│   └── batches/<batch>/raw/    # full CheckM2 run: protein_files/, diamond/, quality_report.tsv
├── gtdbtk/
│   ├── gtdbtk_taxonomy.tsv     # merged, with parsed lineage columns
│   └── batches/<batch>/raw/    # full GTDB-Tk run: identify/, align/, classify/
├── dereplicate/
│   ├── skani_edges.tsv
│   ├── species_clusters.tsv    # every MAG -> its cluster + representative
│   └── dereplicated_report.tsv # one row per species
└── benchmarks/                 # per-rule timing for tuning
```

---

## Quality tiers

| Tier | Completeness | Contamination | Quality score (comp - 5 * contam) |
|---|---|---|---|
| `high_quality` | >= 90% | < 5% | >= 50 |
| `medium_quality` | >= 60% | < 10% | >= 50 |
| `low_quality` | everything else | -- | -- |

The dereplication step operates on `filtered_report.tsv` -- by default, `high_quality` + `medium_quality` genomes. An additional **60% completeness gate** applies before representative selection.

---

## Dereplication algorithm

1. **skani triangle** -- all-vs-all ANI with bi-directional alignment-fraction filter (>= 10% both directions).
2. **Connected components at 90% ANI** -- partitions the similarity graph so each component's distance matrix stays small. Scales to 100k+ genomes.
3. **Average-linkage hierarchical clustering** within each component (UPGMA on ANI distance).
4. **Cut at 95% ANI** -- species-level clusters.
5. **60% completeness gate** -- genomes below this threshold are excluded from representative selection (they still appear in the cluster assignment table).
6. **Representative selection** -- highest composite quality score per cluster.

### Composite dereplication score

```
Score = A * Completeness
      - B * Contamination
      + C * (Contamination * strain_heterogeneity / 100)
      + D * log10(N50)
      + E * log10(genome_size)
```

| Weight | Default | Controls |
|---|---|---|
| `A` | 1.0 | Completeness |
| `B` | 5.0 | Contamination penalty |
| `C` | 1.0 | Strain-heterogeneity recovery (requires CheckM1) |
| `D` | 0.5 | Assembly contiguity bonus (log10 N50) |
| `E` | 0.0 | Genome size bonus (log10 total length; disabled by default) |

The `C` term rewards genomes whose contamination is explained by strain heterogeneity rather than true chimeric contamination. It is only active when CheckM1 runs (CheckM2 does not emit `strain_heterogeneity`). All weights are configurable in `config/config.yaml` under `dereplicate.score_weights`.

---

## Putting databases anywhere you want

By default, databases live in `databases/` inside the project. To point at a shared lab location instead:

**Option 1: Environment variable**

```bash
# One-time: set in your shell profile
export MAGDREP_DB_DIR=/shared/lab/meta-pipeline-MAGDrep-db

# Now every command finds them automatically
meta-pipeline-MAGDrep db update
meta-pipeline-MAGDrep run -i mags/ -o results/
```

**Option 2: Persistent config via `db update`**

```bash
# Pass --db-dir once; the path is saved to a per-conda-env config
meta-pipeline-MAGDrep db update --db-dir /shared/lab/meta-pipeline-MAGDrep-db

# Future commands find it automatically (no env var needed)
meta-pipeline-MAGDrep db status
meta-pipeline-MAGDrep run -i mags/ -o results/
```

Resolution order: `--db-dir` flag > `$MAGDREP_DB_DIR` env var > persistent config (conda env, then `~/.config/`) > project-local `databases/`.

---

## CLI reference

### `meta-pipeline-MAGDrep`

```
Usage: meta-pipeline-MAGDrep [OPTIONS] COMMAND [ARGS]...

  meta-pipeline-MAGDrep: quality assessment and taxonomy of MAGs at scale.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  benchmark  Summarize step timing from a completed pipeline run.
  db         Manage reference databases.
  run        Run the pipeline on a directory or path-list of MAGs.
```

### `run` -- run the pipeline

```
Usage: meta-pipeline-MAGDrep run [OPTIONS]

Options:
  -i, --input PATH                Directory of MAG FASTA files OR a text file
                                  with one MAG directory per line (# comments
                                  allowed).  [required]
  -o, --output PATH               Output directory.  [required]
  --profile [gcp|local|slurm]     Execution profile.  [default: local]
  --steps TEXT                    Comma-separated steps to run (e.g. checkm2,gtdbtk). Default: all.
  --skip TEXT                     Comma-separated steps to skip (e.g. gtdbtk).
  --rename                        Resolve duplicate genome IDs (append _A,_B,...)
                                  and rewrite every contig header to
                                  {genome}_scaffold_{N}.
  --config PATH                   Path to a custom config YAML.
  --dry-run                       Show what would be run without executing.
  -j, --jobs INTEGER              Maximum parallel jobs. Overrides config.
  --cluster-cpus INTEGER          CPUs per standard compute node for SLURM/GCP.
                                  Auto-detected from sinfo if not set.
  --cluster-mem-gb INTEGER        Memory (GB) per standard compute node.
                                  Auto-detected from sinfo if not set.
  --cluster-mem-node-cpus INTEGER CPUs on memory-partition nodes (for GTDB-Tk).
                                  Defaults to --cluster-cpus.
  --cluster-mem-node-mem-gb INTEGER
                                  Memory (GB) on memory-partition nodes.
                                  Defaults to --cluster-mem-gb.
  --slurm-standard-partition TEXT SLURM partition for CheckM2 and most rules.  [default: normal]
  --slurm-memory-partition TEXT   SLURM partition for GTDB-Tk (memory).
                                  Defaults to --slurm-standard-partition.
  --help                          Show this message and exit.
```

### `db update` -- download reference databases

```
Usage: meta-pipeline-MAGDrep db update [OPTIONS]

Options:
  --db-dir PATH    Directory to download databases into. If given, the path is
                   saved to a per-env config so future commands find it
                   automatically. Defaults to $MAGDREP_DB_DIR or persistent
                   config or ./databases/.
  --only TEXT      Download only this database (checkm2 or gtdbtk).
  --force          Re-download even if already present.
  --save/--no-save Save the resolved --db-dir to a per-env config (default: save).
  --help           Show this message and exit.
```

### `db status` -- check what's installed

```
Usage: meta-pipeline-MAGDrep db status [OPTIONS]

Options:
  --db-dir PATH  Database directory to inspect.
                 Defaults to $MAGDREP_DB_DIR or persistent config or ./databases/.
  --help         Show this message and exit.
```

### `benchmark` -- summarize step timing

```
Usage: meta-pipeline-MAGDrep benchmark [OPTIONS] RESULTS_DIR

  Summarize step timing from a completed pipeline run.
```

### Common patterns

```bash
# Basic run
meta-pipeline-MAGDrep run -i mags/ -o results/

# Run with CheckM1 + CheckM2 (adds strain_heterogeneity to composite score)
meta-pipeline-MAGDrep run -i mags/ -o results/ \
    --steps genome_stats,checkm1,checkm2,gtdbtk,dereplicate

# Input from a text file of MAG directories + normalize names
meta-pipeline-MAGDrep run -i mag_dirs.txt -o results/ --rename

# Skip the taxonomy step (fast dev iteration)
meta-pipeline-MAGDrep run -i mags/ -o results/ --skip gtdbtk

# Run with a custom config
meta-pipeline-MAGDrep run -i mags/ -o results/ --config my-config.yaml

# HPC with separate standard + memory partitions
meta-pipeline-MAGDrep run -i mags/ -o results/ --profile slurm \
    --slurm-standard-partition standard --slurm-memory-partition memory

# GCP Google Batch (see docs/deployment/gcp.md for setup)
meta-pipeline-MAGDrep run -i gs://bucket/mags/ -o gs://bucket/results/ --profile gcp

# Check how long each step took
meta-pipeline-MAGDrep benchmark results/

# Inspect which databases are installed
meta-pipeline-MAGDrep db status
```

---

## Deployment

| Where | Profile | Docs |
|---|---|---|
| Laptop / workstation | `--profile local` (default) | [Program Guide](docs/program-guide.md) |
| HPC / SLURM | `--profile slurm` | [docs/deployment/slurm.md](docs/deployment/slurm.md) |
| Google Cloud (Batch) | `--profile gcp` | [docs/deployment/gcp.md](docs/deployment/gcp.md) |

**Per-partition SLURM routing.** On heterogeneous clusters, route compute-bound steps (CheckM1, CheckM2, genome_stats) to standard nodes and memory-bound steps (GTDB-Tk) to high-memory nodes:

```bash
meta-pipeline-MAGDrep run -i mags/ -o results/ --profile slurm \
    --slurm-standard-partition standard \
    --slurm-memory-partition highmem
```

Node specs are auto-detected via `sinfo` per partition, or set explicitly with `--cluster-cpus` / `--cluster-mem-gb` and `--cluster-mem-node-cpus` / `--cluster-mem-node-mem-gb`.

---

## Citing

If you use this pipeline, please cite the component tools:

- **CheckM1** -- Parks DH, Imelfort M, Skennerton CT, Hugenholtz P, Tyson GW (2015) *Genome Res* 25:1043-1055.
- **CheckM2** -- Chklovski A, Parks DH, Woodcroft BJ, Tyson GW (2023) *Nat Methods* 20:1203-1212.
- **GTDB-Tk** -- Chaumeil P-A, Mussig AJ, Hugenholtz P, Parks DH (2022) *Bioinformatics* 38:5315-5316.
- **GTDB r226** -- Parks DH, et al. (2026) *Nucleic Acids Res* 54:D743-D754.
- **skani** -- Shaw J, Yu YW (2023) *Nat Methods* 20:1633-1634.
- **SeqKit** -- Shen W, Le S, Li Y, Hu F (2016) *PLoS ONE* 11:e0163962.
- **Snakemake** -- Koster J, Rahmann S (2012) *Bioinformatics* 28:2520-2522.

---

<div align="center">

Made by the [Diamond Lab](https://diamondlab.com) | [Issues](https://github.com/SDmetagenomics/meta-pipeline-MAGDrep/issues) | [Program Guide](docs/program-guide.md)

</div>
