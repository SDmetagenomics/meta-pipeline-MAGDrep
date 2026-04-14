# Quick Start

## 1. Clone and Install

```bash
git clone https://github.com/SDmetagenomics/meta-pipeline-MAGDrep.git
cd meta-pipeline-MAGDrep
pip install -e . --no-deps
```

## 2. Download Databases

CheckM2, GUNC, and GTDB-Tk each require reference databases. The `db` subcommand handles downloads:

```bash
# Download all databases to the default location (./databases)
meta-pipeline-MAGDrep db update

# Or specify a custom directory
meta-pipeline-MAGDrep db update --db-dir /data/magdrep_dbs
```

!!! note "Database sizes"
    - CheckM2: ~3 GB
    - GUNC (GTDB 214): ~14 GB
    - GTDB-Tk (R10-RS226): ~85 GB

## 3. Run the Pipeline

```bash
meta-pipeline-MAGDrep run -i mags/ -o results/
```

### Common Options

```bash
# Dry run -- show the job DAG without executing
meta-pipeline-MAGDrep run -i mags/ -o results/ --dry-run

# Run only genome stats and CheckM2
meta-pipeline-MAGDrep run -i mags/ -o results/ --steps genome_stats,checkm2

# Skip taxonomy (saves time if GTDB-Tk DB is not available)
meta-pipeline-MAGDrep run -i mags/ -o results/ --skip gtdbtk

# Use a custom config file
meta-pipeline-MAGDrep run -i mags/ -o results/ --config my_config.yaml
```

## 4. Inspect Results

```
results/
├── combined_report.tsv          # All genomes, all metrics
├── filtered_report.tsv          # Genomes passing quality filter
├── species_clusters.tsv         # Cluster assignments
├── dereplicated_report.tsv      # One representative per species
├── checkm2_quality.tsv
├── gunc_chimerism.tsv
├── gtdbtk_taxonomy.tsv
└── individual/
    └── {mag_id}/
        └── genome_stats.tsv
```

The main file to look at is `combined_report.tsv`, which merges all per-tool outputs into a single table with quality tiers assigned.
