# Output Report Reference

## Overview

The pipeline produces three top-level reports, all keyed on `mag_id`:

| File | Description |
|------|-------------|
| `summary_report.tsv` | Compact per-genome summary: assembly stats, quality tier, and taxonomy. |
| `combined_report.tsv` | Every column from every tool merged on `mag_id`. |
| `filtered_report.tsv` | Subset of `combined_report.tsv` passing the quality filter. |

## Column Schema

### Genome Statistics (from SeqKit / BioPython)

| Column | Type | Description |
|--------|------|-------------|
| `mag_id` | str | Genome identifier (FASTA file stem) |
| `total_length_bp` | int | Total assembly length in base pairs |
| `gc_percent` | float | GC content (0--100%) |
| `contig_count` | int | Number of contigs |
| `n50_bp` | int | N50 contig length in base pairs |
| `largest_contig_bp` | int | Longest contig in base pairs |

### CheckM2 Quality

| Column | Type | Description |
|--------|------|-------------|
| `completeness` | float | Estimated completeness (0--100%) |
| `contamination` | float | Estimated contamination (0--100%) |
| `completeness_model_used` | str | CheckM2 model variant |

### CheckM1 Quality (optional, when checkm1 step is enabled)

| Column | Type | Description |
|--------|------|-------------|
| `strain_heterogeneity` | float | Strain heterogeneity estimate (0--100%) |

CheckM1 also provides its own completeness and contamination estimates. When both CheckM1 and CheckM2 are active, CheckM2 values take precedence for quality tiering. CheckM1's strain heterogeneity feeds into the dereplication composite score.

### GTDB-Tk Taxonomy

| Column | Type | Description |
|--------|------|-------------|
| `domain` | str | Domain classification |
| `phylum` | str | Phylum classification |
| `class` | str | Class classification |
| `order` | str | Order classification |
| `family` | str | Family classification |
| `genus` | str | Genus classification |
| `species` | str | Species classification |
| `classification` | str | Full semicolon-delimited lineage |
| `fastani_ani` | float | ANI to closest GTDB reference |

### Quality Tier Assignment

| Column | Type | Description |
|--------|------|-------------|
| `quality_score` | float | completeness - 5 * contamination |
| `quality_tier` | str | MIMAG-style quality label |

### Dereplication (if enabled)

| Column | Type | Description |
|--------|------|-------------|
| `cluster_id` | int | Species cluster identifier |
| `is_representative` | bool | True if this genome represents its cluster |
| `composite_score` | float | Weighted composite quality score used for representative selection |

## Quality Tiers

Quality tiers follow MIMAG standards:

| Tier | Completeness | Contamination | Quality Score |
|------|-------------|---------------|---------------|
| `high_quality` | >= 90% | < 5% | >= 50 |
| `medium_quality` | >= 60% | < 10% | >= 50 |
| `low_quality` | below medium thresholds | -- | -- |

## Quality Score Formula

```
quality_score = completeness - 5 * contamination
```

This formula follows the convention established by Parks et al. (2018) for ranking MAG quality.

## Composite Score Formula (Dereplication)

The composite score is used to select representative genomes during dereplication:

```
score = A * Completeness
      - B * Contamination
      + C * (Contamination * strain_heterogeneity / 100)
      + D * log10(N50)
      + E * log10(genome_size)
```

Default weights: A=1, B=5, C=1, D=0.5, E=0. See [Configuration](../usage/configuration.md) for details.

## Filtered Report

`filtered_report.tsv` contains only rows where `quality_tier` meets the configured minimum (default: `medium_quality`). The column schema is identical to the combined report.

## Summary Report

`summary_report.tsv` is a compact view with the most commonly needed columns: assembly stats, quality tier, and taxonomy. Useful for quick inspection without all the per-tool detail columns.
