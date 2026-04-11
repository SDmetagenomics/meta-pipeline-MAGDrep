# meta-pipeline-MAGDrep

Quality assessment, taxonomic classification, and species-level dereplication of metagenome-assembled genomes (MAGs) at scale.

![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![Snakemake](https://img.shields.io/badge/snakemake-9.x-blue)
![License](https://img.shields.io/badge/license-MIT-lightgrey)
![Status](https://img.shields.io/badge/status-active%20development-orange)

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/SDmetagenomics/meta-pipeline-MAGDrep.git
cd meta-pipeline-MAGDrep

# 2. Install
pip install -e . --no-deps

# 3. Download databases
meta-pipeline-MAGDrep db update

# 4. Run
meta-pipeline-MAGDrep qc -i mags/ -o results/
```

> **Note:** External tools (CheckM2, GUNC, GTDB-Tk, SeqKit, skani) must be installed separately via conda/mamba. See [container/environment.yml](container/environment.yml) for pinned versions.

---

## Overview

`meta-pipeline-MAGDrep` takes a directory of MAG FASTA files and produces:

- **Assembly statistics** per genome (N50, GC%, contig count, total length) via SeqKit
- **Completeness and contamination** estimates via CheckM2
- **Chimerism detection** via GUNC (non-redundant contamination)
- **Taxonomic classification** via GTDB-Tk (GTDB R10-RS226)
- **Quality-filtered reports** with MIMAG-style quality tiers
- **Species-level dereplication** via skani with composite quality scoring

Designed for datasets of 10,000+ genomes. Batch processing keeps memory bounded. Runs on a laptop, a SLURM cluster, or in a Docker container.

---

## Input

Directory of prokaryotic MAG FASTA files. Accepted extensions: `.fna`, `.fa`, `.fasta` (optionally gzip-compressed).

```
mags/
├── GCA_000001405_MAG001.fna
├── GCA_000001405_MAG002.fna.gz
└── SRR12345_bin_003.fasta
```

---

## Output

```
results/
├── combined_report.tsv          # All genomes, all metrics, quality tiers
├── filtered_report.tsv          # Genomes passing quality filter
├── species_clusters.tsv         # Cluster assignments (if dereplicate step)
├── dereplicated_report.tsv      # One genome per species (if dereplicate step)
├── checkm2_quality.tsv          # Raw CheckM2 output
├── gunc_chimerism.tsv           # Raw GUNC output
├── gtdbtk_taxonomy.tsv          # Raw GTDB-Tk output
└── individual/                  # Per-MAG genome stats
    └── {mag_id}/
        └── genome_stats.tsv
```

---

## Quality Tiers

| Tier | Completeness | Contamination | Quality Score | GUNC |
|------|-------------|---------------|---------------|------|
| high_quality | >= 90% | < 5% | >= 50 | pass |
| medium_quality | >= 60% | < 10% | >= 50 | pass |
| medium_chimeric | >= 60% | < 10% | >= 50 | fail |
| low_quality | < 60% or >= 10% or < 50 | - | - | pass |
| low_chimeric | (any) | (any) | (any) | fail |

Quality score = completeness - 5 * contamination

---

## CLI Reference

```
meta-pipeline-MAGDrep --version
meta-pipeline-MAGDrep qc -i DIR -o DIR [OPTIONS]
meta-pipeline-MAGDrep db update [--db-dir DIR]
meta-pipeline-MAGDrep db status [--db-dir DIR]
```

### `qc` options

| Option | Default | Description |
|--------|---------|-------------|
| `--input / -i` | (required) | Input MAG directory |
| `--output / -o` | (required) | Output directory |
| `--profile` | local | Execution profile: local, slurm |
| `--steps` | all | Comma-separated steps |
| `--skip` | none | Steps to skip |
| `--config` | none | Custom config YAML |
| `--dry-run` | false | Show DAG without executing |
| `--jobs / -j` | auto | Max parallel jobs |

---

## Tool Versions

| Tool | Version | Purpose |
|------|---------|---------|
| SeqKit | 2.8 | Assembly statistics |
| CheckM2 | 1.0.2 | Completeness/contamination |
| GUNC | 1.1.0 | Chimerism detection |
| GTDB-Tk | 2.5+ | Taxonomy (GTDB R10-RS226) |
| skani | 0.2+ | Species-level ANI |

---

## References

- **CheckM2**: Chklovski A, et al. (2023) *Nature Methods*, 20:1203-1212.
- **GUNC**: Orakov A, et al. (2021) *Genome Biology*, 22:178.
- **GTDB-Tk**: Chaumeil P-A, et al. (2022) *Bioinformatics*, 38:5315-5316.
- **GTDB R10-RS226**: Parks DH, et al. (2026) *Nucleic Acids Research*, 54:D743-D754.
- **SeqKit**: Shen W, et al. (2016) *PLOS ONE*, 11:e0163962.
- **skani**: Shaw J & Yu YW (2023) *Nature Methods*, 20:1633-1634.
- **MIMAG**: Bowers RM, et al. (2017) *Nature Biotechnology*, 35:725-731.
