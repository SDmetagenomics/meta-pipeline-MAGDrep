# Combined Report Reference

## Overview

`combined_report.tsv` is the primary output of the pipeline. It contains one row per input genome with columns from every pipeline step merged on `mag_id`.

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

### GUNC Chimerism

| Column | Type | Description |
|--------|------|-------------|
| `css` | float | Clade separation score (0--1) |
| `rrs` | float | Reference representation score |
| `contamination_portion` | float | Estimated contaminant fraction |
| `pass_gunc` | bool | True if CSS below threshold |

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

## Quality Tiers

Quality tiers follow MIMAG standards with an additional chimerism dimension from GUNC:

| Tier | Completeness | Contamination | Quality Score | GUNC |
|------|-------------|---------------|---------------|------|
| `high_quality` | >= 90% | < 5% | >= 50 | pass |
| `medium_quality` | >= 60% | < 10% | >= 50 | pass |
| `medium_chimeric` | >= 60% | < 10% | >= 50 | fail |
| `low_quality` | below medium thresholds | -- | -- | pass |
| `low_chimeric` | any | any | any | fail |

## Quality Score Formula

```
quality_score = completeness - 5 * contamination
```

This formula follows the convention established by Parks et al. (2018) for ranking MAG quality.

## Filtered Report

`filtered_report.tsv` contains only rows where `quality_tier` meets the configured minimum (default: `medium_quality`). Chimeric genomes are excluded. The column schema is identical to the combined report.
