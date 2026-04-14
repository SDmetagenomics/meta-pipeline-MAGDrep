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
| `dereplicate.min_completeness` | 60.0 | Completeness gate -- only genomes above this threshold are eligible as representatives |
| `dereplicate.score_weights` | see below | Weights for the composite quality score |

### Composite Score Formula

```
score = A * Completeness
      - B * Contamination
      + C * (Contamination * strain_heterogeneity / 100)
      + D * log10(N50)
      + E * log10(genome_size)
```

### Default Score Weights

```yaml
score_weights:
  A: 1.0    # completeness weight
  B: 5.0    # contamination weight
  C: 1.0    # strain-heterogeneity x contamination weight
  D: 0.5    # log10(N50) weight
  E: 0.0    # log10(genome_size) weight
```

The `C` term uses strain heterogeneity from CheckM1. When only CheckM2 is run (the default), strain heterogeneity is 0 and the `C` term drops out. Enable CheckM1 via `--steps genome_stats,checkm1,checkm2,gtdbtk,dereplicate` to populate it.

## How It Works

1. **ANI calculation**: `skani triangle` computes all-vs-all ANI for genomes in the filtered report. Only pairs exceeding `min_af` are retained.
2. **Connected components**: Genomes are partitioned into connected components at 90% ANI so each component's distance matrix stays small (scalability).
3. **Average linkage clustering**: UPGMA clustering within each component, cut at the `ani_threshold` (default 95%) to define species-level clusters.
4. **60% completeness gate**: Only genomes with completeness >= `min_completeness` are eligible as cluster representatives.
5. **Representative selection**: The cluster representative is the genome with the highest composite score among eligible genomes.

## Output Files

| File | Description |
|------|-------------|
| `dereplicate/species_clusters.tsv` | All genomes with `mag_id`, `cluster_id`, `is_representative` |
| `dereplicate/dereplicated_report.tsv` | Full combined report rows for representative genomes only |

## When Dereplication Is Skipped

If the `dereplicate` step is not included in `--steps`, cluster files are not produced. The combined, filtered, and summary reports are still generated from the other steps.
