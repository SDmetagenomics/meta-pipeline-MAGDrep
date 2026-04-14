# meta-pipeline-MAGDrep

**Quality assessment, taxonomic classification, and species-level dereplication of metagenome-assembled genomes (MAGs) at scale.**

## What It Does

meta-pipeline-MAGDrep takes a directory of MAG FASTA files (or a text file listing MAG directories) and runs a standardized quality-control pipeline:

1. **Assembly statistics** -- contig count, N50, GC%, total length via SeqKit
2. **Completeness and contamination** -- gradient-boosted ML estimates via CheckM2 (with optional CheckM1 for strain heterogeneity)
3. **Taxonomic classification** -- placement on the GTDB R10-RS226 tree via GTDB-Tk
4. **Quality tiering** -- MIMAG-style labels (high, medium, low)
5. **Species-level dereplication** -- all-vs-all ANI via skani with composite quality scoring (60% completeness gate)

The pipeline is designed for datasets of 10,000+ genomes. Batch processing keeps memory bounded. It runs on a laptop, a SLURM cluster, or in a Docker container.

## Quick Start

```bash
git clone https://github.com/SDmetagenomics/meta-pipeline-MAGDrep.git
cd meta-pipeline-MAGDrep
make install          # creates magdrep + magdrep-checkm1 envs
conda activate magdrep
meta-pipeline-MAGDrep db update
meta-pipeline-MAGDrep run -i mags/ -o results/
```

See the [Quick Start](quickstart.md) guide for full details.

## Output

The pipeline produces a `summary_report.tsv` (compact per-genome overview), a `combined_report.tsv` (all columns from every tool), and `filtered_report.tsv` (genomes passing the quality filter), plus per-tool output directories and dereplication results. See [Output Reference](outputs/combined-report.md).

## Requirements

- Python 3.11+
- Snakemake 9.x
- External tools: SeqKit, CheckM2, GTDB-Tk, skani (CheckM1 optional)

All tool versions are pinned in `environment.yml`.
