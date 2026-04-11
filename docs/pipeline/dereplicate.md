# Dereplication

## Purpose

Cluster genomes at species-level ANI and select the best representative from each cluster. This removes redundant genomes from the dataset while retaining the highest-quality representative per species.

## Tool

**skani** v0.2+

> Shaw J, Yu YW (2023) Fast and robust metagenomic sequence comparison through sparse chaining with skani. *Nature Methods*, 20:1633--1634.

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `dereplicate.ani_threshold` | 95.0 | Species boundary ANI (%) |
| `dereplicate.min_af` | 10.0 | Minimum alignment fraction (%) for a valid comparison |
| `dereplicate.score_weights` | see below | Weights for the composite quality score |

### Composite Score Weights

```yaml
score_weights:
  w_qscore: 1.0         # quality_score = completeness - 5 * contamination
  w_completeness: 1.0    # raw completeness
  w_n50: 0.5             # log10(N50) normalized
  w_contam: 0.5          # contamination penalty
  w_gunc: 0.5            # bonus for passing GUNC
```

## How It Works

1. **ANI calculation**: `skani triangle` computes all-vs-all ANI for the genome set. Only pairs exceeding `min_af` are retained.
2. **Bi-directional filtering**: ANI values are made symmetric. Both the forward and reverse alignment fractions must meet `min_af`.
3. **Greedy clustering**: Genomes are sorted by composite quality score (descending). The highest-scoring unclustered genome becomes a cluster representative. All genomes within `ani_threshold` are assigned to that cluster.
4. **Representative selection**: The cluster representative is the genome with the highest composite score.

## Output Files

| File | Description |
|------|-------------|
| `species_clusters.tsv` | All genomes with `mag_id`, `cluster_id`, `is_representative` |
| `dereplicated_report.tsv` | Full combined report rows for representative genomes only |

## When Dereplication Is Skipped

If the `dereplicate` step is not included in `--steps`, cluster files are not produced. The combined and filtered reports are still generated from the other steps.
