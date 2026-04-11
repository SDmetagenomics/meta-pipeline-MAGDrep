# Installation

## Prerequisites

- Python 3.11 or later
- Snakemake 9.x
- External bioinformatics tools (see below)

## Option 1: pip (Recommended for Development)

```bash
git clone https://github.com/diamondlab-ucb/meta-pipeline-MAGQC.git
cd meta-pipeline-MAGQC
pip install -e . --no-deps
```

You must install the external tools separately. The easiest method is conda/mamba:

```bash
mamba install -c conda-forge -c bioconda \
  seqkit=2.8 checkm2=1.0.2 diamond=2.1 prodigal=2.6 \
  gtdbtk=2.5 skani=0.2
pip install "gunc>=1.1.0"
```

## Option 2: Conda Environment

```bash
mamba env create -f container/environment.yml
mamba activate magqc
pip install -e . --no-deps
```

## Option 3: Docker

```bash
docker build -t meta-pipeline-magqc .
docker run -v /path/to/dbs:/databases -v /path/to/mags:/input \
  meta-pipeline-magqc qc -i /input -o /output
```

## Database Downloads

Each tool requires a reference database. Use the built-in downloader:

```bash
meta-pipeline-MAGQC db update --db-dir /data/magqc_dbs
```

Or download manually:

| Database | Command | Size |
|----------|---------|------|
| CheckM2 | `checkm2 database --download --path /data/magqc_dbs/checkm2` | ~3 GB |
| GUNC | `gunc download_db /data/magqc_dbs/gunc --db gtdb_214` | ~14 GB |
| GTDB-Tk | `download-db.sh /data/magqc_dbs/gtdbtk` | ~85 GB |

## Verify Installation

```bash
meta-pipeline-MAGQC --version
meta-pipeline-MAGQC db status
```
