# Quick Start

## 1. Clone and Install

```bash
git clone https://github.com/SDmetagenomics/meta-pipeline-MAGDrep.git
cd meta-pipeline-MAGDrep
make install          # creates magdrep + magdrep-checkm1 envs
conda activate magdrep
```

## 2. Download Databases

CheckM2 and GTDB-Tk each require reference databases. The `db` subcommand handles downloads:

```bash
# Download all databases to the default location (./databases)
meta-pipeline-MAGDrep db update

# Or specify a custom directory (saved persistently for future runs)
meta-pipeline-MAGDrep db update --db-dir /data/magdrep_dbs
```

You can also set the `MAGDREP_DB_DIR` environment variable so every invocation finds the databases automatically:

```bash
export MAGDREP_DB_DIR=/data/magdrep_dbs
```

Resolution order: `--db-dir` flag > `$MAGDREP_DB_DIR` > persistent config (saved by `db update --db-dir`) > `./databases/`.

!!! note "Database sizes"
    - CheckM2: ~3 GB
    - CheckM1 (optional): ~1.4 GB
    - GTDB-Tk (R10-RS226): ~85 GB

## 3. Run the Pipeline

```bash
meta-pipeline-MAGDrep run -i mags/ -o results/
```

Input can be a directory of MAG FASTA files or a text file with one MAG directory per line (`#` comments allowed).

### Common Options

```bash
# Dry run -- show the job DAG without executing
meta-pipeline-MAGDrep run -i mags/ -o results/ --dry-run

# Run only genome stats and CheckM2
meta-pipeline-MAGDrep run -i mags/ -o results/ --steps genome_stats,checkm2

# Include optional CheckM1 step (provides strain heterogeneity)
meta-pipeline-MAGDrep run -i mags/ -o results/ --steps genome_stats,checkm1,checkm2,gtdbtk,dereplicate

# Skip taxonomy (saves time if GTDB-Tk DB is not available)
meta-pipeline-MAGDrep run -i mags/ -o results/ --skip gtdbtk

# Rename duplicate genome IDs and rewrite contig headers
meta-pipeline-MAGDrep run -i mags/ -o results/ --rename

# Use a custom config file
meta-pipeline-MAGDrep run -i mags/ -o results/ --config my_config.yaml
```

## 4. Inspect Results

```
results/
├── summary_report.tsv              # Compact per-genome summary (stats + quality + taxonomy)
├── combined_report.tsv             # All genomes, all columns from every tool
├── filtered_report.tsv             # Genomes passing quality filter
├── genome_stats/
│   └── {mag_id}/
│       └── genome_stats.tsv
├── checkm2/
│   └── checkm2_quality.tsv
├── gtdbtk/
│   └── gtdbtk_taxonomy.tsv
└── dereplicate/
    ├── species_clusters.tsv
    └── dereplicated_report.tsv
```

The main file to start with is `summary_report.tsv`, which provides a compact overview of each genome's assembly stats, quality tier, and taxonomy. For all columns from every tool, see `combined_report.tsv`.
