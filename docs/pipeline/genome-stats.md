# Genome Statistics

## Purpose

Compute basic assembly statistics for each MAG: total length, GC content, contig count, N50, and largest contig size. These metrics are used downstream in quality scoring and dereplication ranking.

## Tool

**SeqKit** v2.8 (primary), **BioPython** (fallback)

SeqKit is preferred for speed. If SeqKit is not installed, the pipeline falls back to a pure-Python implementation using BioPython's `SeqIO`.

> Shen W, Le S, Li Y, Hu F (2016) SeqKit: A Cross-Platform and Ultrafast Toolkit for FASTA/Q File Manipulation. *PLOS ONE*, 11:e0163962.

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `threads_per_job` | 4 | Threads passed to SeqKit |

No external database is required.

## Columns Produced

| Column | Type | Description |
|--------|------|-------------|
| `mag_id` | str | Genome identifier (file stem) |
| `total_length_bp` | int | Sum of all contig lengths |
| `gc_percent` | float | GC content as a percentage (0--100) |
| `contig_count` | int | Number of contigs in the FASTA |
| `n50_bp` | int | N50 contig length |
| `largest_contig_bp` | int | Length of the longest contig |

## Output File

`individual/{mag_id}/genome_stats.tsv` -- one row per genome with the columns above.

All per-genome stats files are merged into `combined_report.tsv` during the report merge step.
