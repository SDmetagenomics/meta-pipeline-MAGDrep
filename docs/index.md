# meta-pipeline-MAGQC

**Quality assessment, taxonomic classification, and species-level dereplication of metagenome-assembled genomes (MAGs) at scale.**

## What It Does

meta-pipeline-MAGQC takes a directory of MAG FASTA files and runs a standardized quality-control pipeline:

1. **Assembly statistics** -- contig count, N50, GC%, total length via SeqKit
2. **Completeness and contamination** -- gradient-boosted ML estimates via CheckM2
3. **Chimerism detection** -- taxonomic consistency scoring via GUNC
4. **Taxonomic classification** -- placement on the GTDB R10-RS226 tree via GTDB-Tk
5. **Quality tiering** -- MIMAG-style labels (high, medium, low, chimeric)
6. **Species-level dereplication** -- all-vs-all ANI via skani with composite quality scoring

The pipeline is designed for datasets of 10,000+ genomes. Batch processing keeps memory bounded. It runs on a laptop, a SLURM cluster, or in a Docker container.

## Quick Start

```bash
git clone https://github.com/diamondlab-ucb/meta-pipeline-MAGQC.git
cd meta-pipeline-MAGQC
pip install -e . --no-deps
meta-pipeline-MAGQC db update
meta-pipeline-MAGQC qc -i mags/ -o results/
```

See the [Quick Start](quickstart.md) guide for full details.

## Output

The pipeline produces a single `combined_report.tsv` with 28 columns covering every genome, plus filtered and dereplicated views. See [Output Reference](outputs/combined-report.md).

## Requirements

- Python 3.11+
- Snakemake 9.x
- External tools: SeqKit, CheckM2, GUNC, GTDB-Tk, skani

All tool versions are pinned in `container/environment.yml`.
