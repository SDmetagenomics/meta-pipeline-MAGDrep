# Inputs and Outputs

## Input Format

The pipeline expects a single directory containing prokaryotic MAG FASTA files:

```
mags/
├── GCA_000001405_MAG001.fna
├── GCA_000001405_MAG002.fna.gz
└── SRR12345_bin_003.fasta
```

### Accepted Extensions

`.fna`, `.fa`, `.fasta` -- optionally gzip-compressed (`.fna.gz`, `.fa.gz`, `.fasta.gz`).

The file stem (without extension) becomes the `mag_id` used throughout the pipeline. Files that do not match a recognized extension are silently skipped.

### Requirements

- Files must contain valid nucleotide sequences in FASTA format.
- One file per genome. Multi-genome files are not supported.
- Empty files are skipped with a warning.

## Output Structure

```
results/
├── combined_report.tsv          # All genomes, all columns, quality tiers
├── filtered_report.tsv          # Genomes passing the configured quality filter
├── species_clusters.tsv         # Cluster IDs and representative genome flags
├── dereplicated_report.tsv      # One row per species cluster (the representative)
├── checkm2_quality.tsv          # Raw CheckM2 output
├── gunc_chimerism.tsv           # Raw GUNC output
├── gtdbtk_taxonomy.tsv          # Raw GTDB-Tk output
└── individual/                  # Per-MAG intermediate results
    └── {mag_id}/
        └── genome_stats.tsv
```

### Key Output Files

| File | Description |
|------|-------------|
| `combined_report.tsv` | Primary output. Every genome with all 28 columns merged from each step. |
| `filtered_report.tsv` | Subset of `combined_report.tsv` passing the quality filter (default: medium_quality). |
| `species_clusters.tsv` | Three columns: `mag_id`, `cluster_id`, `is_representative`. |
| `dereplicated_report.tsv` | Full report rows for representative genomes only. |

The `individual/` directory contains per-genome intermediate outputs. These are useful for debugging but are not needed for downstream analysis.
