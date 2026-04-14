# Installation

## Prerequisites

- Python 3.11 or later
- Snakemake 9.x
- Conda or Mamba

## Option 1: make install (Recommended)

```bash
git clone https://github.com/SDmetagenomics/meta-pipeline-MAGDrep.git
cd meta-pipeline-MAGDrep
make install
conda activate magdrep
```

`make install` creates two conda environments:

- **magdrep** -- main environment with CheckM2, GTDB-Tk, skani, SeqKit, and the pipeline itself
- **magdrep-checkm1** -- sibling environment for the optional CheckM1 step (incompatible Python version with CheckM2)

The pipeline invokes CheckM1 automatically via `conda run` when `checkm1` is included in `--steps`.

## Option 2: pip (Development)

```bash
git clone https://github.com/SDmetagenomics/meta-pipeline-MAGDrep.git
cd meta-pipeline-MAGDrep
pip install -e . --no-deps
```

You must install the external tools separately. The easiest method is conda/mamba:

```bash
mamba install -c conda-forge -c bioconda \
  seqkit checkm2 gtdbtk skani
```

## Option 3: Docker

```bash
docker build -t meta-pipeline-magdrep .
docker run -v /path/to/dbs:/databases -v /path/to/mags:/input \
  meta-pipeline-magdrep run -i /input -o /output
```

## Database Downloads

CheckM2 and GTDB-Tk require reference databases. Use the built-in downloader:

```bash
meta-pipeline-MAGDrep db update --db-dir /data/magdrep_dbs
```

The `--db-dir` path is saved persistently so future commands find it automatically. Alternatively, set the `MAGDREP_DB_DIR` environment variable:

```bash
export MAGDREP_DB_DIR=/data/magdrep_dbs
meta-pipeline-MAGDrep db update
```

Or download manually:

| Database | Command | Size |
|----------|---------|------|
| CheckM2 | `checkm2 database --download --path /data/magdrep_dbs/checkm2` | ~3 GB |
| CheckM1 (optional) | `checkm data setRoot /data/magdrep_dbs/checkm1` | ~1.4 GB |
| GTDB-Tk | `download-db.sh /data/magdrep_dbs/gtdbtk` | ~85 GB |

## Verify Installation

```bash
meta-pipeline-MAGDrep --version
meta-pipeline-MAGDrep db status
```
