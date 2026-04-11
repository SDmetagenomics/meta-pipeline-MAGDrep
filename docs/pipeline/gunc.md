# GUNC Chimerism Detection

## Purpose

Detect chimeric genomes -- MAGs assembled from fragments of multiple organisms. GUNC identifies chimerism that CheckM2 cannot, because contamination from closely related taxa looks like legitimate genome content to marker-gene and ML approaches.

## Tool

**GUNC** v1.1.0

> Orakov A, Fullam A, Coelho LP, et al. (2021) GUNC: detection of chimerism and contamination in prokaryotic genomes. *Genome Biology*, 22:178.

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `batch_size` | 1000 | Genomes per GUNC invocation |
| `threads_per_job` | 4 | Threads per batch |
| `quality_filter.gunc_css_threshold` | 0.45 | Clade separation score threshold |
| `db_versions.gunc` | `gtdb_214` | GUNC database version |

## Database

GUNC uses a taxonomic reference database (~14 GB). Download with:

```bash
meta-pipeline-MAGQC db update
# or manually:
gunc download_db databases/gunc --db gtdb_214
```

## Columns Produced

| Column | Type | Description |
|--------|------|-------------|
| `css` | float | Clade separation score (0--1). Higher = more chimeric. |
| `rrs` | float | Reference representation score |
| `contamination_portion` | float | Estimated fraction of contaminant contigs |
| `pass_gunc` | bool | `True` if CSS < threshold, `False` otherwise |

## Complementary to CheckM2

CheckM2 measures contamination based on duplicated marker genes or ML features. GUNC measures taxonomic inconsistency across contigs. A genome can pass CheckM2 (low contamination) but fail GUNC (chimeric), which is why both are run.

Genomes that fail GUNC are assigned to `medium_chimeric` or `low_chimeric` quality tiers regardless of their CheckM2 scores.
