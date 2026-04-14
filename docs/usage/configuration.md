# Configuration

## Config Hierarchy

Settings are resolved in order of increasing priority:

1. **Built-in defaults** (`config/config.yaml`)
2. **User YAML file** (passed via `--config`)
3. **CLI overrides** (e.g., `--steps`, `--jobs`)

Nested dictionaries are deep-merged: user values replace defaults at the leaf level without discarding sibling keys.

## Key Settings

### General

| Setting | Default | Description |
|---------|---------|-------------|
| `outdir` | `results` | Output directory |
| `steps` | `genome_stats, checkm2, gtdbtk, dereplicate` | Pipeline steps to run, in order |
| `batch_size` | `1000` | Number of genomes per batch (controls memory) |
| `threads_per_job` | `auto` | CPU threads allocated to each tool invocation (auto = detect) |
| `max_parallel_jobs` | `auto` | Maximum concurrent Snakemake jobs (auto = detect) |
| `fasta_extensions` | `.fna`, `.fa`, `.fasta` (+ `.gz`) | Recognized input extensions |
| `db_dir` | `databases` | Root directory for reference databases |

Valid steps: `genome_stats`, `checkm1` (optional), `checkm2`, `gtdbtk`, `dereplicate`.

### Database Configuration

The pipeline resolves `db_dir` in this order:

1. `--db-dir` flag (per-command)
2. `$MAGDREP_DB_DIR` environment variable
3. Persistent config saved by `db update --db-dir`
4. Default `./databases/`

Running `meta-pipeline-MAGDrep db update --db-dir /path` saves the path persistently to the conda environment so future invocations find databases automatically.

### Quality Filter

```yaml
quality_filter:
  high_completeness: 90.0
  high_contamination: 5.0
  medium_completeness: 60.0
  medium_contamination: 10.0
  min_quality_score: 50.0
  default_filter: medium_quality
```

The `default_filter` controls which tier is the minimum for inclusion in `filtered_report.tsv`. Options: `high_quality`, `medium_quality`.

### Dereplication

```yaml
dereplicate:
  ani_threshold: 95.0       # Species boundary (%)
  min_af: 10.0              # Minimum alignment fraction (%)
  min_completeness: 60.0    # Completeness gate for representative selection
  score_weights:
    A: 1.0    # completeness weight
    B: 5.0    # contamination weight
    C: 1.0    # strain-heterogeneity x contamination weight
    D: 0.5    # log10(N50) weight
    E: 0.0    # log10(genome_size) weight
```

The composite score ranks genomes within each species cluster to select the best representative. Only genomes with at least `min_completeness` (default 60%) are eligible as representatives.

### Composite Score Formula

```
score = A * Completeness
      - B * Contamination
      + C * (Contamination * strain_heterogeneity / 100)
      + D * log10(N50)
      + E * log10(genome_size)
```

The `C` term uses strain heterogeneity from CheckM1; when only CheckM2 is run, strain heterogeneity is 0 and the term drops out.

### CheckM1 (Optional)

```yaml
steps:
  - genome_stats
  - checkm1         # add this line to enable
  - checkm2
  - gtdbtk
  - dereplicate

checkm1_threads: auto
checkm1_pplacer_threads: 4
checkm1_batch_size: null    # null = use batch_size; small batches recommended
```

CheckM1 runs in the sibling `magdrep-checkm1` conda environment. It provides `strain_heterogeneity`, which feeds into the dereplication composite score (the `C` term).

## Example Custom Config

```yaml
# my_config.yaml
batch_size: 500
quality_filter:
  default_filter: high_quality
dereplicate:
  ani_threshold: 96.0
  min_completeness: 70.0
```

```bash
meta-pipeline-MAGDrep run -i mags/ -o results/ --config my_config.yaml
```
