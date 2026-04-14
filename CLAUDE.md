# CLAUDE.md — meta-pipeline-MAGDrep

## Project

Snakemake pipeline for quality assessment, taxonomic classification, and species-level dereplication of metagenome-assembled genomes (MAGs) at scale.

- **Repo**: https://github.com/SDmetagenomics/meta-pipeline-MAGDrep
- **Package**: `meta_pipeline_magdrep` (installed via `make install`)
- **CLI**: `meta-pipeline-MAGDrep`
- **Local dir**: Note the local directory is still named `meta-pipeline-MAGQC` (pre-rename), but the repo/package/CLI are all `MAGDrep`.

## Current State (2026-04-11) — v1.3.0

### What's built and working

- **Full pipeline runs end-to-end** on 50 test genomes: 45 min wall time (genome_stats 3s, checkm2 21m, gtdbtk 24m, skani+dereplicate <1s each)
- **58/58 unit tests passing**
- **Five available steps**: `genome_stats` -> `checkm1` (optional) -> `checkm2` -> `gtdbtk` -> `dereplicate`
  - GUNC was removed from the pipeline
  - CheckM1 added as optional step for strain heterogeneity data
- **Databases installed**: CheckM2 (~3 GB), GTDB-Tk R226 (~132 GB), CheckM1 (~1.4 GB, optional)
- **Tool versions pinned** in `environment.yml` + `conda-lock.txt` for reproducibility
- **Input**: directory of MAG FASTAs OR text file with one MAG directory per line
- **`--rename` flag**: resolves duplicate genome IDs (appends _A,_B,...) and rewrites contig headers
- **`make install`**: creates both `magdrep` and `magdrep-checkm1` conda environments
- **Persistent db config**: `MAGDREP_DB_DIR` env var + `db update --db-dir` saves to conda env

### Quality tiers

Three tiers (MIMAG-style, no chimerism dimension):

| Tier | Completeness | Contamination | Quality Score |
|------|-------------|---------------|---------------|
| `high_quality` | >= 90% | < 5% | >= 50 |
| `medium_quality` | >= 60% | < 10% | >= 50 |
| `low_quality` | below medium | -- | -- |

### Dereplication

- skani triangle all-vs-all ANI with bi-directional `--min-af 10`
- Connected components at 90% ANI partition the graph so each component's distance matrix stays small (scalability)
- **Average linkage (UPGMA)** clustering within each component
- Cut at 95% ANI (distance = 5.0) defines species-level clusters
- **60% completeness gate**: only genomes above `min_completeness` are eligible as representatives
- Composite score formula: `A*Completeness - B*Contamination + C*(Contamination*strain_het/100) + D*log10(N50) + E*log10(genome_size)`
- Default weights: A=1, B=5, C=1, D=0.5, E=0
- The C term uses CheckM1 strain heterogeneity; when only CheckM2 is run, it zeroes out

### Output layout

```
results/
├── summary_report.tsv        # compact per-genome summary
├── combined_report.tsv       # all columns from every tool
├── filtered_report.tsv       # genomes passing quality filter
├── genome_stats/             # per-tool directory
├── checkm2/                  # per-tool directory
├── gtdbtk/                   # per-tool directory
└── dereplicate/              # species_clusters.tsv + dereplicated_report.tsv
```

### GTDB-Tk resource autotuning

- `pplacer_cpus: auto` in config scales with available memory (~60 GB per pplacer cpu for r226)
- `threads` uses all detected CPUs
- `resources.py` detects CPU count + total memory; `compute_gtdbtk_pplacer_cpus()` picks a safe value
- Startup prints: `Detected: N CPUs, M GB RAM. GTDB-Tk will use --cpus=N --pplacer_cpus=X.`

### Per-rule benchmarks

- Every rule has a `benchmark:` directive writing to `results/benchmarks/<step>/<batch>.tsv`
- Summarize with: `meta-pipeline-MAGDrep benchmark results/`

### Database management (`db update` / `db status`)

- Lab-wide shared conda env + `db update` once after install
- `db update --db-dir /path` saves the path persistently to the conda env
- `MAGDREP_DB_DIR` env var overrides default; `--db-dir` flag overrides everything
- Resolution order: `--db-dir` > `$MAGDREP_DB_DIR` > persistent config > `./databases/`
- Sentinel files (`*.ok`) track completion; re-runs skip completed downloads

## Commands

```bash
# Install (creates magdrep + magdrep-checkm1 envs)
make install && conda activate magdrep

# Unit tests
make test

# Download databases (one-time)
meta-pipeline-MAGDrep db update
meta-pipeline-MAGDrep db status

# Run full pipeline on test genomes
meta-pipeline-MAGDrep run -i tests/data/genomes/ -o results/

# Run with optional CheckM1
meta-pipeline-MAGDrep run -i mags/ -o results/ --steps genome_stats,checkm1,checkm2,gtdbtk,dereplicate

# Skip a step
meta-pipeline-MAGDrep run -i mags/ -o results/ --skip gtdbtk

# Rename duplicate genome IDs
meta-pipeline-MAGDrep run -i mags/ -o results/ --rename

# Input as text file listing MAG directories
meta-pipeline-MAGDrep run -i mag_dirs.txt -o results/

# View timing
meta-pipeline-MAGDrep benchmark results/
```

## Bugs fixed during end-to-end testing

1. **CheckM2 multiprocessing + Python 3.12**: CheckM2 1.1.0 fails under Python 3.12's `spawn` start method (name-mangled private methods can't be pickled). Wrapper in `run_checkm2.py` calls checkm2 via `python -c "multiprocessing.set_start_method('fork'); ..."` to force fork mode.
2. **GTDB-Tk reference ID collisions**: Test genomes share accessions with GTDB refs, so `rules/gtdbtk.smk` prefixes symlinks with `MAG_` and `run_gtdbtk.py` strips the prefix when parsing output.
3. **dereplicate shell quoting**: Python dict passed through shell broke `ast.literal_eval`. Fixed: use `run:` block with `subprocess` + `json.dumps`/`json.loads`.
4. **Score weights type coercion**: Snakemake's config pipeline can stringify numeric values. `compute_composite_scores` now coerces weight values to float; rule also coerces defensively.
5. **SeqKit `fx2tab` column order**: length comes before gc (fixed in genome_stats.py).
6. **Quality config type coercion**: YAML values arrive as strings, need float() cast (fixed in merge_reports.py).

## Architecture

- Mirrors `meta-pipeline-ORFanno` (sibling project at `../meta-pipeline-ORFanno/`)
- Batch processing: CheckM2 / GTDB-Tk process genomes in batches of 1000 (configurable)
- Quality tiers: MIMAG-style (high / medium / low)
- Dereplication: skani all-vs-all -> 90%-ANI connected components -> average linkage per component -> cut at 95%
