# CLAUDE.md — meta-pipeline-MAGDrep

## Project

Snakemake pipeline for quality assessment, taxonomic classification, and species-level dereplication of metagenome-assembled genomes (MAGs) at scale.

- **Repo**: https://github.com/SDmetagenomics/meta-pipeline-MAGDrep
- **Package**: `meta_pipeline_magdrep` (installed via `make install`)
- **CLI**: `meta-pipeline-MAGDrep`
- **Local dir**: Note the local directory is still named `meta-pipeline-MAGQC` (pre-rename), but the repo/package/CLI are all `MAGDrep`.

## Current State (2026-04-11)

### What's built and working

- **Full pipeline codebase**: 50/50 unit tests passing
  - Python package: `src/meta_pipeline_magdrep/` (cli, config, runner, resources)
  - Snakemake rules: genome_stats, checkm2, gunc, gtdbtk, aggregate, dereplicate
  - Scripts: genome_stats.py, run_checkm2.py, run_gunc.py, run_gtdbtk.py, merge_reports.py, dereplicate.py
- **Conda environment** (`magdrep`): all tools installed via `make install`
- **50 real NCBI test genomes** downloaded locally in `tests/data/genomes/`
  - GitHub Release: https://github.com/SDmetagenomics/meta-pipeline-MAGDrep/releases/tag/v0.1.0-testdata
  - 15 same-species strains (E. coli, S. aureus, B. subtilis, P. aeruginosa) + 35 diverse
- **genome_stats step tested**: ran successfully on all 50 genomes, combined_report.tsv produced
- **Docs**: MkDocs site, README, full documentation

### What's NOT yet tested end-to-end

The remaining pipeline steps need databases downloaded:

| Step | Database | Size | Command |
|------|----------|------|---------|
| `checkm2` | CheckM2 DB | ~1.4 GB | `checkm2 database --download --path databases/checkm2` |
| `gunc` | GUNC gtdb_214 | ~13 GB | `gunc download_db databases/gunc -db gtdb_214` |
| `gtdbtk` | GTDB-Tk R226 | ~85 GB | See GTDB-Tk docs |
| `dereplicate` | (no database) | — | Needs filtered_report.tsv from checkm2 step |

Recommended testing order: checkm2 → gunc → gtdbtk → dereplicate (full pipeline)

### Bugs found and fixed during testing

1. SeqKit `fx2tab` column order: length comes before gc (fixed in genome_stats.py)
2. Aggregate rule shell quoting: Python dict passed as shell arg broke argparse (fixed: use `run:` block with subprocess)
3. Quality config type coercion: YAML values arrive as strings, need float() cast (fixed in merge_reports.py)

## Commands

```bash
# Install
make install && conda activate magdrep

# Run unit tests
make test

# Run pipeline on test genomes (genome_stats only — works now)
meta-pipeline-MAGDrep qc -i tests/data/genomes/ -o results/ --steps genome_stats

# Run full pipeline (requires databases)
meta-pipeline-MAGDrep qc -i tests/data/genomes/ -o results/

# Download test genomes (if not present)
make test-genomes
```

## Architecture

- Mirrors `meta-pipeline-ORFanno` (sibling project at `../meta-pipeline-ORFanno/`)
- Batch processing: CheckM2/GUNC/GTDB-Tk process genomes in batches of 1000 (configurable)
- Quality tiers: MIMAG-style (high/medium/low + chimeric variants)
- Dereplication: skani all-vs-all ANI → greedy clustering with composite quality scoring
