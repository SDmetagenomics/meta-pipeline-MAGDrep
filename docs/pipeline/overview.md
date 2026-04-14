# Pipeline Architecture

## Data Flow

```mermaid
graph TD
    A[Input MAG FASTAs] --> B[MAG Discovery & Batching]
    B --> C[Genome Statistics<br/>SeqKit / BioPython]
    B --> D[CheckM2<br/>Completeness & Contamination]
    B --> D2[CheckM1 optional<br/>Strain Heterogeneity]
    B --> F[GTDB-Tk<br/>Taxonomy]
    C --> G[Merge Reports]
    D --> G
    D2 --> G
    F --> G
    G --> H[combined_report.tsv<br/>summary_report.tsv<br/>Quality Tier Assignment]
    H --> I[filtered_report.tsv]
    H --> J[Dereplication<br/>skani ANI]
    J --> K[species_clusters.tsv]
    J --> L[dereplicated_report.tsv]
```

## Pipeline Steps

| Step | Tool | Description | Default |
|------|------|-------------|---------|
| `genome_stats` | SeqKit / BioPython | Assembly statistics (N50, GC%, contig count, total length) | enabled |
| `checkm1` | CheckM v1.2.5 | Lineage-specific marker gene completeness/contamination + strain heterogeneity | optional |
| `checkm2` | CheckM2 v1.1.0 | ML-based completeness and contamination estimates | enabled |
| `gtdbtk` | GTDB-Tk v2.5 | Taxonomic classification via GTDB R10-RS226 | enabled |
| `dereplicate` | skani | All-vs-all ANI clustering and representative selection | enabled |

## Execution Model

The pipeline is orchestrated by Snakemake. Each step is defined as a set of rules in `rules/`. Steps run in parallel where data dependencies allow:

- **Genome statistics**, **CheckM2**, **CheckM1** (optional), and **GTDB-Tk** run independently in parallel.
- **Merge reports** waits for all enabled steps to complete.
- **Dereplication** runs after the merge, using the filtered report and composite quality scores to select representatives.

## Batching

Large input sets are split into batches of configurable size (default: 1,000 genomes). Each batch is processed as an independent Snakemake job. This bounds peak memory and allows partial results to appear early.

## Execution Profiles

| Profile | Description |
|---------|-------------|
| `local` | Runs on the current machine using Snakemake's Python API. |
| `slurm` | Submits jobs to a SLURM cluster using `snakemake-executor-plugin-slurm`. |
| `gcp` | Runs each rule as a Google Cloud Batch job. |

Profiles are stored in `config/profiles/` and set resource defaults (threads, memory, time limits) per rule.

## Step Selection

Steps can be included or excluded at the command line:

```bash
# Run only genome stats and CheckM2
meta-pipeline-MAGDrep run -i mags/ -o results/ --steps genome_stats,checkm2

# Run everything except GTDB-Tk
meta-pipeline-MAGDrep run -i mags/ -o results/ --skip gtdbtk

# Include optional CheckM1 step
meta-pipeline-MAGDrep run -i mags/ -o results/ --steps genome_stats,checkm1,checkm2,gtdbtk,dereplicate
```

When a step is skipped, its columns are absent from the combined report and quality tiers that depend on those columns are marked as `NA`.
