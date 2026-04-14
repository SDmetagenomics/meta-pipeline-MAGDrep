# Inputs and Outputs

## Input Format

The pipeline accepts either a directory of MAG FASTA files or a text file listing one MAG directory per line (`#` comments allowed):

### Option A: Directory of FASTA files

```
mags/
├── GCA_000001405_MAG001.fna
├── GCA_000001405_MAG002.fna.gz
└── SRR12345_bin_003.fasta
```

### Option B: Text file with MAG directories

```
# mags.txt
/data/project1/mags
/data/project2/mags
# /data/project3/mags  (commented out, skipped)
```

```bash
meta-pipeline-MAGDrep run -i mags.txt -o results/
```

### Accepted Extensions

`.fna`, `.fa`, `.fasta` -- optionally gzip-compressed (`.fna.gz`, `.fa.gz`, `.fasta.gz`).

The file stem (without extension) becomes the `mag_id` used throughout the pipeline. Files that do not match a recognized extension are silently skipped.

### The --rename Flag

If duplicate genome IDs are detected across input directories, the pipeline raises an error by default. Pass `--rename` to resolve duplicates automatically (appending `_A`, `_B`, etc.) and rewrite every contig header to `{genome}_scaffold_{N}`.

```bash
meta-pipeline-MAGDrep run -i mags/ -o results/ --rename
```

### Requirements

- Files must contain valid nucleotide sequences in FASTA format.
- One file per genome. Multi-genome files are not supported.
- Empty files are skipped with a warning.

## Output Structure

```
results/
├── summary_report.tsv              # Compact per-genome summary (stats + quality + taxonomy)
├── combined_report.tsv             # All genomes, all columns from every tool
├── filtered_report.tsv             # Genomes passing the configured quality filter
├── genome_stats/
│   └── {mag_id}/
│       └── genome_stats.tsv
├── checkm2/
│   └── checkm2_quality.tsv
├── gtdbtk/
│   └── gtdbtk_taxonomy.tsv
└── dereplicate/
    ├── skani_edges.tsv
    ├── species_clusters.tsv
    └── dereplicated_report.tsv
```

If the optional CheckM1 step is enabled, a `checkm1/checkm1_quality.tsv` directory also appears.

### Key Output Files

| File | Description |
|------|-------------|
| `summary_report.tsv` | Compact overview: assembly stats, quality tier, and taxonomy per genome. |
| `combined_report.tsv` | Full output. Every genome with all columns merged from each step. |
| `filtered_report.tsv` | Subset of `combined_report.tsv` passing the quality filter (default: medium_quality). |
| `dereplicate/species_clusters.tsv` | Three columns: `mag_id`, `cluster_id`, `is_representative`. |
| `dereplicate/dereplicated_report.tsv` | Full report rows for representative genomes only. |

Per-tool directories (`genome_stats/`, `checkm2/`, `gtdbtk/`, `dereplicate/`) contain intermediate outputs useful for debugging but not needed for downstream analysis.
