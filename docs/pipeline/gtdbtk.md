# GTDB-Tk Taxonomy

## Purpose

Assign taxonomic classifications to MAGs using the Genome Taxonomy Database (GTDB). Classifications are based on placement in the GTDB reference tree using 120 bacterial or 53 archaeal marker genes.

## Tool

**GTDB-Tk** v2.5+ with **GTDB R10-RS226**

> Chaumeil P-A, Mussig AJ, Hugenholtz P, Parks DH (2022) GTDB-Tk v2: memory friendly classification with the genome taxonomy database. *Bioinformatics*, 38:5315--5316.

> Parks DH, et al. (2026) GTDB: an ongoing census of bacterial and archaeal diversity through a phylogenetically consistent, rank normalized and complete genome-based taxonomy. *Nucleic Acids Research*, 54:D743--D754.

## Key Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `batch_size` | 1000 | Genomes per GTDB-Tk invocation |
| `gtdbtk.threads` | auto | Threads per batch (auto = detect available CPUs) |
| `gtdbtk.pplacer_cpus` | auto | pplacer threads (auto = scale with available memory, ~60 GB per pplacer cpu for R226) |
| `gtdbtk.skip_ani_screen` | false | Skip ANI pre-screen against reference genomes |
| `gtdbtk_batch_size` | null | Override batch size (null = use global `batch_size`) |

!!! warning "Memory requirement"
    GTDB-Tk's pplacer step requires approximately **85 GB of RAM** for the full GTDB R10-RS226 database. Ensure your system or SLURM job has sufficient memory. The pipeline auto-tunes `pplacer_cpus` based on available memory when set to `auto`.

## Database

The GTDB-Tk database is large (~85 GB). Download with:

```bash
meta-pipeline-MAGDrep db update
# or manually:
download-db.sh databases/gtdbtk
```

The database path is resolved from `$MAGDREP_DB_DIR`, persistent config, or `./databases/`.

## Columns Produced

| Column | Type | Description |
|--------|------|-------------|
| `domain` | str | d\_\_Bacteria or d\_\_Archaea |
| `phylum` | str | GTDB phylum assignment |
| `class` | str | GTDB class assignment |
| `order` | str | GTDB order assignment |
| `family` | str | GTDB family assignment |
| `genus` | str | GTDB genus assignment |
| `species` | str | GTDB species assignment |
| `classification` | str | Full semicolon-delimited lineage |
| `fastani_ani` | float | ANI to closest reference genome (if available) |

## How It Works

1. Genomes are batched and classified with `gtdbtk classify_wf`.
2. GTDB-Tk runs marker gene identification (Prodigal), alignment (hmmer), and tree placement (pplacer).
3. Bacterial (bac120) and archaeal (ar53) summary files are parsed and merged.
4. Results are written to `gtdbtk/gtdbtk_taxonomy.tsv`.
