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
| `steps` | all five | Pipeline steps to run, in order |
| `batch_size` | `1000` | Number of genomes per batch (controls memory) |
| `threads_per_job` | `4` | CPU threads allocated to each tool invocation |
| `max_parallel_jobs` | `8` | Maximum concurrent Snakemake jobs |
| `fasta_extensions` | `.fna`, `.fa`, `.fasta` (+ `.gz`) | Recognized input extensions |
| `db_dir` | `databases` | Root directory for reference databases |

### Quality Filter

```yaml
quality_filter:
  high_completeness: 90.0
  high_contamination: 5.0
  medium_completeness: 60.0
  medium_contamination: 10.0
  min_quality_score: 50.0
  gunc_css_threshold: 0.45
  default_filter: medium_quality
```

The `default_filter` controls which tier is the minimum for inclusion in `filtered_report.tsv`. Options: `high_quality`, `medium_quality`.

### Dereplication

```yaml
dereplicate:
  ani_threshold: 95.0       # Species boundary (%)
  min_af: 10.0              # Minimum alignment fraction (%)
  score_weights:
    w_qscore: 1.0           # quality_score weight
    w_completeness: 1.0     # completeness weight
    w_n50: 0.5              # N50 weight
    w_contam: 0.5           # contamination penalty weight
    w_gunc: 0.5             # GUNC pass bonus weight
```

The composite score ranks genomes within each species cluster to select the best representative.

## Example Custom Config

```yaml
# my_config.yaml
batch_size: 500
quality_filter:
  default_filter: high_quality
  gunc_css_threshold: 0.50
dereplicate:
  ani_threshold: 96.0
```

```bash
meta-pipeline-MAGQC qc -i mags/ -o results/ --config my_config.yaml
```
