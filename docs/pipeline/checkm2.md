# CheckM2 Quality Assessment

## Purpose

Estimate genome completeness and contamination using a gradient-boosted machine learning model trained on genome simulations. CheckM2 replaces the original CheckM's lineage-specific marker gene approach with a faster, more accurate ML predictor.

## Tool

**CheckM2** v1.1.0

> Chklovski A, Parks DH, Woodcroft BJ, Tyson GW (2023) CheckM2: a rapid, scalable and accurate tool for assessing microbial genome quality using machine learning. *Nature Methods*, 20:1203--1212.

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `batch_size` | 1000 | Genomes per CheckM2 invocation |
| `checkm2_threads` | auto | Threads per batch (auto = split cores with concurrent tools) |
| `checkm2_batch_size` | null | Override batch size (null = use global `batch_size`) |

## Database

CheckM2 requires a pre-trained model (~3 GB). Download with:

```bash
meta-pipeline-MAGDrep db update
# or manually:
checkm2 database --download --path databases/checkm2
```

The database path is resolved from `$MAGDREP_DB_DIR`, persistent config, or `./databases/`.

## Columns Produced

| Column | Type | Description |
|--------|------|-------------|
| `completeness` | float | Estimated completeness (0--100%) |
| `contamination` | float | Estimated contamination (0--100%) |
| `completeness_model_used` | str | Model variant used (`gradient_boost` or `neural_network`) |

## How It Works

1. Input genomes are batched into groups of `batch_size`.
2. Each batch is run through `checkm2 predict`.
3. Per-batch results are merged into `checkm2/checkm2_quality.tsv`.
4. Completeness and contamination feed into quality tier assignment and the composite dereplication score.

## CheckM1 (Optional Alternative)

For strain heterogeneity data (used by the dereplication composite score), you can also enable CheckM1 by adding `checkm1` to `--steps`. CheckM1 runs in a sibling conda environment (`magdrep-checkm1`) because its Python requirements are incompatible with CheckM2. Both tools can run in the same pipeline -- their results are merged in the combined report.

See [Configuration](../usage/configuration.md) for CheckM1-specific settings.
