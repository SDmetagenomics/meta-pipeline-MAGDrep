# CLAUDE.md — meta-pipeline-MAGDrep

## Project

Snakemake pipeline for quality assessment, taxonomic classification, and species-level dereplication of metagenome-assembled genomes (MAGs) at scale.

- **Repo**: https://github.com/SDmetagenomics/meta-pipeline-MAGDrep
- **Package**: `meta_pipeline_magdrep` (installed via `make install`)
- **CLI**: `meta-pipeline-MAGDrep`
- **Local dir**: Note the local directory is still named `meta-pipeline-MAGQC` (pre-rename), but the repo/package/CLI are all `MAGDrep`.

## Current State (2026-04-12) — v1.0.0

### What's built and working

- **Full pipeline runs end-to-end** on 50 test genomes: 45 min wall time (genome_stats 3s, checkm2 21m, gtdbtk 24m, skani+dereplicate <1s each)
- **58/58 unit tests passing**
- **Four active steps**: `genome_stats` → `checkm2` → `gtdbtk` → `dereplicate`
  - GUNC was removed from the pipeline in this session
- **Databases installed**: CheckM2 (~3 GB), GTDB-Tk R226 (~132 GB) — GUNC removed
- **Tool versions pinned** in `environment.yml` + `conda-lock.txt` for reproducibility

### Dereplication

- skani triangle all-vs-all ANI with bi-directional `--min-af 10`
- Connected components at 90% ANI partition the graph so each component's distance matrix stays small (scalability)
- **Average linkage (UPGMA)** clustering within each component
- Cut at 95% ANI (distance = 5.0) defines species-level clusters
- Representative per cluster = highest composite quality score (weighted qscore, completeness, log10(N50), 100-contam)

### GTDB-Tk resource autotuning

- `pplacer_cpus: auto` in config scales with available memory (~60 GB per pplacer cpu for r226)
- `threads` uses all detected CPUs
- `resources.py` detects CPU count + total memory; `compute_gtdbtk_pplacer_cpus()` picks a safe value
- Startup prints: `Detected: N CPUs, M GB RAM. GTDB-Tk will use --cpus=N --pplacer_cpus=X.`

### Per-rule benchmarks

- Every rule has a `benchmark:` directive writing to `results/benchmarks/<step>/<batch>.tsv`
- Summarize with: `meta-pipeline-MAGDrep benchmark results/`

### Database management (`db update` / `db status`)

- Lab-wide shared conda env + `db update` once after install (see memory `project_lab_env.md`)
- Sentinel files (`*.ok`) track completion; re-runs skip completed downloads
- Paths flow from config → rules → scripts: `db_dir` + `checkm2_db_path`/`gtdbtk_db_path` (null = `db_dir/<tool>`)

## Commands

```bash
# Install (one-command from env.yml + conda-lock)
make install && conda activate magdrep

# Unit tests
make test

# Download databases (one-time)
meta-pipeline-MAGDrep db update
meta-pipeline-MAGDrep db status

# Run full pipeline on test genomes
meta-pipeline-MAGDrep run -i tests/data/genomes/ -o results/

# Skip a step
meta-pipeline-MAGDrep run -i mags/ -o results/ --skip gtdbtk

# View timing
meta-pipeline-MAGDrep benchmark results/
```

## Bugs fixed during end-to-end testing (this session)

1. **CheckM2 multiprocessing + Python 3.12**: CheckM2 1.1.0 fails under Python 3.12's `spawn` start method (name-mangled private methods can't be pickled). Wrapper in `run_checkm2.py` calls checkm2 via `python -c "multiprocessing.set_start_method('fork'); ..."` to force fork mode.
2. **GTDB-Tk reference ID collisions**: Test genomes share accessions with GTDB refs, so `rules/gtdbtk.smk` prefixes symlinks with `MAG_` and `run_gtdbtk.py` strips the prefix when parsing output.
3. **Diamond version conflict**: CheckM2 1.1.0 pins `diamond=2.1.11`; earlier GUNC wanted `>=2.1.24`. When GUNC was still present we used `GUNC_SKIP_DIAMOND_VERSION_CHECK=1` — moot now that GUNC is removed.
4. **GUNC file suffix**: GUNC defaulted to `.fa`; test genomes are `.fna`. Auto-detected from input dir (moot now).
5. **dereplicate shell quoting**: Python dict passed through shell broke `ast.literal_eval`. Fixed: use `run:` block with `subprocess` + `json.dumps`/`json.loads`.
6. **Score weights type coercion**: Snakemake's config pipeline can stringify numeric values. `compute_composite_scores` now coerces weight values to float; rule also coerces defensively.

## Architecture

- Mirrors `meta-pipeline-ORFanno` (sibling project at `../meta-pipeline-ORFanno/`)
- Batch processing: CheckM2 / GTDB-Tk process genomes in batches of 1000 (configurable)
- Quality tiers: MIMAG-style (high / medium / low)
- Dereplication: skani all-vs-all → 90%-ANI connected components → average linkage per component → cut at 95%
