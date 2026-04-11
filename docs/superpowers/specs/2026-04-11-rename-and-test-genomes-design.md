# Rename to MAGDrep + Test Genome Set — Design Spec

## Summary

Rename the project from `meta-pipeline-MAGQC` to `meta-pipeline-MAGDrep` throughout the codebase, GitHub repo, and all references. Curate a set of 50 real NCBI RefSeq genomes for end-to-end pipeline testing, distributed as a GitHub Release asset.

---

## Part 1: Rename MAGQC → MAGDrep

### Scope

Every occurrence of the old name must be updated:

| Old | New |
|-----|-----|
| `meta-pipeline-MAGQC` | `meta-pipeline-MAGDrep` |
| `meta_pipeline_magqc` | `meta_pipeline_magdrep` |
| `MAGQC` (in comments/docs) | `MAGDrep` |
| `magqc` (conda env name) | `magdrep` |

### Files affected

**Renames:**
- `meta-pipeline-MAGQC` (bash shim) → `meta-pipeline-MAGDrep`
- `src/meta_pipeline_magqc/` → `src/meta_pipeline_magdrep/`

**Content updates (all occurrences):**
- `pyproject.toml` — package name, entry point
- `Snakefile` — no direct references (uses relative paths)
- `src/meta_pipeline_magdrep/*.py` — module imports in cli.py
- `tests/test_cli.py`, `test_config.py`, `test_runner.py`, `test_integration.py` — import paths
- `config/config.yaml` — comments only
- `config/profiles/slurm/config.yaml` — comments
- `container/Dockerfile` — paths, labels, symlink
- `container/environment.yml` — env name
- `mkdocs.yml` — site_name, repo_url, repo_name
- `README.md` — all references
- `docs/*.md` — all references
- `meta-pipeline-MAGQC_build_instructions.md` — rename or remove (it's the original build spec, no longer needed in the repo)

### GitHub repo rename

Use `gh repo rename meta-pipeline-MAGDrep` to rename the repo on GitHub. Git remotes update automatically.

---

## Part 2: Test Genome Set (50 genomes)

### Selection criteria

- All genomes are **complete** (assembly_level = "Complete Genome") from NCBI RefSeq
- Prefer small genomes (< 5 MB) where possible to minimize download size
- One genome per phylum/class for the diverse set
- Multiple strains per species for the dereplication cluster set

### Genome list

#### Same-species strain clusters (~15 genomes)

These test dereplication at 95% ANI. Each group should cluster together.

**Escherichia coli (5 strains, Gammaproteobacteria):**

| Accession | Strain | Size (Mb) |
|-----------|--------|-----------|
| GCF_000005845.2 | K-12 MG1655 | 4.6 |
| GCF_000008865.2 | O157:H7 EDL933 | 5.5 |
| GCF_000007445.1 | CFT073 | 5.2 |
| GCF_000026245.1 | 55989 | 5.2 |
| GCF_000026325.1 | UMN026 | 5.2 |

**Staphylococcus aureus (4 strains, Bacilli):**

| Accession | Strain | Size (Mb) |
|-----------|--------|-----------|
| GCF_000013425.1 | NCTC 8325 | 2.8 |
| GCF_000009585.1 | USA300 FPR3757 | 2.9 |
| GCF_000011505.1 | COL | 2.8 |
| GCF_000012045.1 | MRSA252 | 2.9 |

**Bacillus subtilis (3 strains, Bacilli):**

| Accession | Strain | Size (Mb) |
|-----------|--------|-----------|
| GCF_000009045.1 | 168 | 4.2 |
| GCF_000227465.1 | BSn5 | 4.1 |
| GCF_000496555.1 | QB928 | 4.1 |

**Pseudomonas aeruginosa (3 strains, Gammaproteobacteria):**

| Accession | Strain | Size (Mb) |
|-----------|--------|-----------|
| GCF_000006765.1 | PAO1 | 6.3 |
| GCF_000014625.1 | PA14 | 6.5 |
| GCF_000006945.2 | LESB58 | 6.6 |

#### Taxonomically diverse set (~35 genomes, one per class/phylum)

**Bacteria:**

| # | Accession | Organism | Class/Phylum | Size (Mb) |
|---|-----------|----------|--------------|-----------|
| 1 | GCF_000195955.2 | Mycobacterium tuberculosis H37Rv | Actinomycetia | 4.4 |
| 2 | GCF_000196035.1 | Deinococcus radiodurans R1 | Deinococci | 3.3 |
| 3 | GCF_000009065.1 | Thermus thermophilus HB8 | Deinococci/Thermia | 2.1 |
| 4 | GCF_000011465.1 | Caulobacter vibrioides CB15 | Alphaproteobacteria | 4.0 |
| 5 | GCF_000007145.1 | Ralstonia solanacearum GMI1000 | Betaproteobacteria | 5.8 |
| 6 | GCF_000020225.1 | Helicobacter pylori 26695 | Epsilonproteobacteria | 1.7 |
| 7 | GCF_000195515.1 | Clostridium difficile 630 | Clostridia | 4.3 |
| 8 | GCF_000009045.1 | *(already in B. subtilis cluster)* | — | — |
| 9 | GCF_000011065.1 | Bacteroides thetaiotaomicron VPI-5482 | Bacteroidia | 6.3 |
| 10 | GCF_000006745.1 | Vibrio cholerae O1 N16961 | Gammaproteobacteria (extra) | 4.0 |
| 11 | GCF_000009725.1 | Synechocystis sp. PCC 6803 | Cyanobacteriia | 3.6 |
| 12 | GCF_000008525.1 | Treponema pallidum Nichols | Spirochaetia | 1.1 |
| 13 | GCF_000027305.1 | Borrelia burgdorferi B31 | Spirochaetia (Lyme) | 1.5 |
| 14 | GCF_000027325.1 | Chlamydia trachomatis D/UW-3/CX | Chlamydiia | 1.0 |
| 15 | GCF_000008745.1 | Mycoplasma genitalium G37 | Mollicutes | 0.6 |
| 16 | GCF_000016525.1 | Rhodopirellula baltica SH 1 | Planctomycetia | 7.1 |
| 17 | GCF_000024845.1 | Akkermansia muciniphila ATCC BAA-835 | Verrucomicrobiae | 2.7 |
| 18 | GCF_000018865.1 | Dehalococcoides mccartyi 195 | Dehalococcoidia (Chloroflexi) | 1.5 |
| 19 | GCF_000007325.1 | Fusobacterium nucleatum ATCC 25586 | Fusobacteriia | 2.2 |
| 20 | GCF_000014005.1 | Acidobacterium capsulatum ATCC 51196 | Acidobacteriia | 4.1 |
| 21 | GCF_000018285.1 | Thermotoga maritima MSB8 | Thermotogae | 1.9 |
| 22 | GCF_000025525.1 | Aquifex aeolicus VF5 | Aquificae | 1.6 |
| 23 | GCF_000020965.1 | Chlorobaculum tepidum TLS | Chlorobia | 2.2 |
| 24 | GCF_000017945.1 | Geobacter sulfurreducens PCA | Deltaproteobacteria | 3.8 |
| 25 | GCF_000015005.1 | Lactobacillus plantarum WCFS1 | Lactobacillia | 3.3 |
| 26 | GCF_000009985.1 | Streptomyces coelicolor A3(2) | Actinomycetia (2nd) | 8.7 |
| 27 | GCF_000195735.1 | Corynebacterium glutamicum ATCC 13032 | Actinomycetia (3rd) | 3.3 |
| 28 | GCF_000014165.1 | Campylobacter jejuni NCTC 11168 | Campylobacteria | 1.6 |
| 29 | GCF_000021665.1 | Leptospira interrogans serovar Lai | Leptospirae | 4.6 |
| 30 | GCF_000013925.1 | Rickettsia prowazekii Madrid E | Alphaproteobacteria (2nd) | 1.1 |

**Archaea:**

| # | Accession | Organism | Class/Phylum | Size (Mb) |
|---|-----------|----------|--------------|-----------|
| 31 | GCF_000195915.1 | Methanobacterium thermoautotrophicum ΔH | Methanobacteria | 1.8 |
| 32 | GCF_000006805.1 | Halobacterium salinarum NRC-1 | Halobacteria | 2.6 |
| 33 | GCF_000007005.1 | Sulfolobus solfataricus P2 | Thermoprotei | 3.0 |
| 34 | GCF_000018465.1 | Nitrosopumilus maritimus SCM1 | Nitrososphaeria | 1.6 |
| 35 | GCF_000007205.1 | Thermococcus kodakarensis KOD1 | Thermococci | 2.1 |

**Total: 50 genomes, estimated ~170 MB compressed.**

> Note: The exact accessions above are best-effort from my training data. The download script will verify each accession exists and is a complete genome. Any that fail will be replaced with an alternate genome from the same class during implementation.

### Manifest file

`tests/data/test_genomes_manifest.tsv` with columns:

```
accession	organism	strain	domain	phylum	class	genome_size_mb	cluster_group	description
```

- `cluster_group`: `ecoli`, `saureus`, `bsubtilis`, `paeruginosa`, or `unique`
- `description`: one-line note (e.g., "K-12 reference strain", "diverse: Thermotogae representative")

### Download script

`tests/data/download_test_genomes.py`:

1. Reads manifest TSV
2. Downloads each genome from NCBI using `datasets download genome accession` (NCBI datasets CLI) or falls back to direct FTP (`rsync`/`curl` from `ftp.ncbi.nlm.nih.gov`)
3. Extracts genomic FASTA, renames to `{accession}.fna`
4. Stores in `tests/data/genomes/`
5. Verifies MD5 checksums (recorded in manifest after first successful download)
6. Skips already-present genomes (idempotent)

### GitHub Release

- **Tag**: `v0.1.0-testdata`
- **Asset**: `test_genomes_v1.tar.gz` containing all 50 `.fna` files
- **Release description**: genome count, taxonomic coverage summary, intended use, how to download

### Pipeline integration

- `conftest.py` gains a `test_genomes_dir` fixture:
  - Checks `tests/data/genomes/` for local genomes
  - If missing, downloads from GitHub Release via `gh release download` or curl
  - Returns the directory path
- `db update` command documentation updated to list official download commands for CheckM2, GUNC, GTDB-Tk
- Integration test (`test_integration.py`) updated to use 50-genome set when available

---

## Part 3: Database Documentation

The pipeline points users to official database downloads. The `db update` command and docs will provide:

| Database | Version | Download Command | Size |
|----------|---------|-----------------|------|
| CheckM2 | 1.0.2 | `checkm2 database --download --path databases/checkm2` | ~1.4 GB |
| GUNC | gtdb_214 | `gunc download_db databases/gunc -db gtdb_214` | ~13 GB |
| GTDB-Tk | R226 | `download-db.sh databases/gtdbtk` | ~85 GB |

---

## Out of scope

- Zenodo deposits (deferred — can add later if needed for publication)
- Automated database downloads in the pipeline (users run commands manually)
- CI/CD pipeline (future work)
