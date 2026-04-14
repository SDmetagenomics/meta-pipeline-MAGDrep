# Rename to MAGDrep + Test Genome Set Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename meta-pipeline-MAGQC to meta-pipeline-MAGDrep throughout the codebase and GitHub, then curate and distribute 50 real NCBI test genomes via a GitHub Release.

**Architecture:** The rename is a mechanical find-and-replace across all files plus a `git mv` for the package directory and bash shim. The test genome set is a manifest TSV + download script + conftest fixture, distributed as a tarball attached to a GitHub Release.

**Tech Stack:** Python 3.11+, NCBI datasets CLI / curl, gh CLI, pytest

---

## File Structure

**Renamed files:**
- `meta-pipeline-MAGQC` → `meta-pipeline-MAGDrep` (bash shim)
- `src/meta_pipeline_magqc/` → `src/meta_pipeline_magdrep/` (entire directory)

**Modified files (content replacement):**
- `pyproject.toml`
- `src/meta_pipeline_magdrep/__init__.py` (no change needed, just `__version__`)
- `src/meta_pipeline_magdrep/cli.py` (imports + docstring)
- `src/meta_pipeline_magdrep/runner.py` (no references to MAGQC)
- `src/meta_pipeline_magdrep/config.py` (no references to MAGQC)
- `src/meta_pipeline_magdrep/resources.py` (no references to MAGQC)
- `meta-pipeline-MAGDrep` (bash shim content)
- `config/config.yaml`
- `config/profiles/slurm/config.yaml`
- `container/Dockerfile`
- `container/environment.yml`
- `mkdocs.yml`
- `README.md`
- `docs/index.md`, `docs/quickstart.md`, `docs/installation.md`
- `docs/usage/configuration.md`
- `docs/pipeline/overview.md`, `docs/pipeline/checkm2.md`, `docs/pipeline/gunc.md`, `docs/pipeline/gtdbtk.md`
- `tests/test_cli.py`, `tests/test_config.py`, `tests/test_runner.py`, `tests/test_integration.py`

**New files:**
- `tests/data/test_genomes_manifest.tsv`
- `tests/data/download_test_genomes.py`
- `tests/test_download_genomes.py`

---

### Task 1: Rename Package Directory and Bash Shim

**Files:**
- Rename: `src/meta_pipeline_magqc/` → `src/meta_pipeline_magdrep/`
- Rename: `meta-pipeline-MAGQC` → `meta-pipeline-MAGDrep`

- [ ] **Step 1: Rename the Python package directory**

```bash
cd /Users/sdiamond/Dropbox/Informatics/Dev/Claude_Projects/meta-pipeline-MAGQC
git mv src/meta_pipeline_magqc src/meta_pipeline_magdrep
```

- [ ] **Step 2: Rename the bash shim**

```bash
git mv meta-pipeline-MAGQC meta-pipeline-MAGDrep
```

- [ ] **Step 3: Update bash shim content**

Edit `meta-pipeline-MAGDrep` to change the module reference:

```bash
#!/usr/bin/env bash
# meta-pipeline-MAGDrep launcher
# Thin shim that delegates to the Python CLI entry point.
set -euo pipefail

exec python -m meta_pipeline_magdrep.cli "$@"
```

- [ ] **Step 4: Commit the renames**

```bash
git add -A
git commit -m "refactor: rename package directory and bash shim from MAGQC to MAGDrep"
```

---

### Task 2: Update Python Package References

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/meta_pipeline_magdrep/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_config.py`
- Modify: `tests/test_runner.py`
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Update pyproject.toml**

Replace all occurrences:
- `"meta-pipeline-MAGQC"` → `"meta-pipeline-MAGDrep"`
- `"meta_pipeline_magqc.cli:main"` → `"meta_pipeline_magdrep.cli:main"`

The entry point line becomes:
```toml
meta-pipeline-MAGDrep = "meta_pipeline_magdrep.cli:main"
```

- [ ] **Step 2: Update cli.py imports and docstring**

In `src/meta_pipeline_magdrep/cli.py`, replace all occurrences:
- `from meta_pipeline_magqc` → `from meta_pipeline_magdrep`
- `meta-pipeline-MAGQC` → `meta-pipeline-MAGDrep` (in the docstring)

Lines to change:
```python
from meta_pipeline_magdrep import __version__
from meta_pipeline_magdrep.config import load_and_merge_config, VALID_STEPS, ConfigError
from meta_pipeline_magdrep.resources import detect_resources
```
```python
    """meta-pipeline-MAGDrep: quality assessment and taxonomy of MAGs at scale."""
```
```python
    from meta_pipeline_magdrep.runner import run_snakemake
```

- [ ] **Step 3: Update test imports**

In `tests/test_cli.py`:
```python
from meta_pipeline_magdrep.cli import main
```

In `tests/test_config.py`:
```python
from meta_pipeline_magdrep.config import (
    load_config, validate_config, merge_config,
    load_and_merge_config, ConfigError, VALID_STEPS,
)
```

In `tests/test_runner.py`:
```python
from meta_pipeline_magdrep.runner import build_snakemake_config
```

In `tests/test_integration.py`:
```python
    from meta_pipeline_magdrep.config import load_and_merge_config
    from meta_pipeline_magdrep.runner import run_snakemake
```

- [ ] **Step 4: Reinstall the package in editable mode**

```bash
pip install -e . --no-deps
```

- [ ] **Step 5: Run all tests to verify the rename works**

```bash
python -m pytest tests/ -v --ignore=tests/test_integration.py
```

Expected: 50 passed.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: update all Python imports and entry points from MAGQC to MAGDrep"
```

---

### Task 3: Update Config, Container, and Infrastructure Files

**Files:**
- Modify: `config/config.yaml`
- Modify: `config/profiles/slurm/config.yaml`
- Modify: `container/Dockerfile`
- Modify: `container/environment.yml`
- Modify: `mkdocs.yml`

- [ ] **Step 1: Update config/config.yaml**

Line 1: `# meta-pipeline-MAGQC default configuration` → `# meta-pipeline-MAGDrep default configuration`

- [ ] **Step 2: Update config/profiles/slurm/config.yaml**

Line 1: `# SLURM profile for meta-pipeline-MAGQC` → `# SLURM profile for meta-pipeline-MAGDrep`
Line 6: `#   meta-pipeline-MAGQC qc` → `#   meta-pipeline-MAGDrep qc`

- [ ] **Step 3: Update container/Dockerfile**

Replace all occurrences of `meta-pipeline-MAGQC` → `meta-pipeline-MAGDrep` and `MAGQC` → `MAGDrep`:

```dockerfile
FROM mambaorg/micromamba:1.5.8

LABEL org.opencontainers.image.title="meta-pipeline-MAGDrep"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.description="Quality assessment and taxonomy of MAGs at scale"

COPY container/environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml && \
    micromamba clean --all --yes

COPY . /opt/meta-pipeline-MAGDrep
WORKDIR /opt/meta-pipeline-MAGDrep

RUN micromamba run -n base pip install -e . --no-deps

RUN chmod +x /opt/meta-pipeline-MAGDrep/meta-pipeline-MAGDrep && \
    ln -s /opt/meta-pipeline-MAGDrep/meta-pipeline-MAGDrep /usr/local/bin/meta-pipeline-MAGDrep

# Databases are mounted at runtime
VOLUME ["/databases"]
ENV MAGDREP_DB_DIR=/databases

ENTRYPOINT ["micromamba", "run", "-n", "base", "meta-pipeline-MAGDrep"]
CMD ["--help"]
```

- [ ] **Step 4: Update container/environment.yml**

Line 1: `name: magqc` → `name: magdrep`

- [ ] **Step 5: Update mkdocs.yml**

```yaml
site_name: meta-pipeline-MAGDrep
...
repo_url: https://github.com/SDmetagenomics/meta-pipeline-MAGDrep
repo_name: SDmetagenomics/meta-pipeline-MAGDrep
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "refactor: update config, container, and mkdocs references to MAGDrep"
```

---

### Task 4: Update Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/index.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/installation.md`
- Modify: `docs/usage/configuration.md`
- Modify: `docs/pipeline/overview.md`
- Modify: `docs/pipeline/checkm2.md`
- Modify: `docs/pipeline/gunc.md`
- Modify: `docs/pipeline/gtdbtk.md`

- [ ] **Step 1: Global find-and-replace in all docs and README**

In every file listed above, replace:
- `meta-pipeline-MAGQC` → `meta-pipeline-MAGDrep`
- `meta-pipeline-magqc` → `meta-pipeline-magdrep` (lowercase Docker tag)
- `diamondlab-ucb/meta-pipeline-MAGQC` → `SDmetagenomics/meta-pipeline-MAGDrep`
- `magqc` → `magdrep` (conda env name, db paths in examples)
- `MAGQC` → `MAGDrep` (standalone references)

Be careful NOT to change:
- `GUNC` (different tool name)
- Anything inside the `superpowers/` directory

- [ ] **Step 2: Run tests to confirm nothing broke**

```bash
python -m pytest tests/ -v --ignore=tests/test_integration.py
```

Expected: 50 passed.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "docs: update all documentation references from MAGQC to MAGDrep"
```

---

### Task 5: Rename GitHub Repo and Update Remote

- [ ] **Step 1: Rename the GitHub repo**

```bash
gh repo rename meta-pipeline-MAGDrep --repo SDmetagenomics/meta-pipeline-MAGQC -y
```

- [ ] **Step 2: Update the git remote URL**

```bash
git remote set-url origin https://github.com/SDmetagenomics/meta-pipeline-MAGDrep.git
```

- [ ] **Step 3: Push all rename commits**

```bash
git push origin main
```

- [ ] **Step 4: Verify the rename**

```bash
gh repo view SDmetagenomics/meta-pipeline-MAGDrep --json name,url
```

---

### Task 6: Create Test Genomes Manifest

**Files:**
- Create: `tests/data/test_genomes_manifest.tsv`

- [ ] **Step 1: Create the manifest file**

`tests/data/test_genomes_manifest.tsv`:

```tsv
accession	organism	strain	domain	phylum	class	genome_size_mb	cluster_group	description
GCF_000005845.2	Escherichia coli	K-12 MG1655	Bacteria	Pseudomonadota	Gammaproteobacteria	4.6	ecoli	K-12 reference strain
GCF_000008865.2	Escherichia coli	O157:H7 EDL933	Bacteria	Pseudomonadota	Gammaproteobacteria	5.5	ecoli	Enterohemorrhagic O157:H7
GCF_000007445.1	Escherichia coli	CFT073	Bacteria	Pseudomonadota	Gammaproteobacteria	5.2	ecoli	Uropathogenic strain
GCF_000026245.1	Escherichia coli	55989	Bacteria	Pseudomonadota	Gammaproteobacteria	5.2	ecoli	Enteroaggregative strain
GCF_000026325.1	Escherichia coli	UMN026	Bacteria	Pseudomonadota	Gammaproteobacteria	5.4	ecoli	Extraintestinal pathogenic
GCF_000013425.1	Staphylococcus aureus	NCTC 8325	Bacteria	Bacillota	Bacilli	2.8	saureus	Reference strain
GCF_000009585.1	Staphylococcus aureus	USA300 FPR3757	Bacteria	Bacillota	Bacilli	2.9	saureus	Community-acquired MRSA
GCF_000011505.1	Staphylococcus aureus	COL	Bacteria	Bacillota	Bacilli	2.8	saureus	Early MRSA isolate
GCF_000012045.1	Staphylococcus aureus	MRSA252	Bacteria	Bacillota	Bacilli	2.9	saureus	Hospital-acquired MRSA
GCF_000009045.1	Bacillus subtilis	168	Bacteria	Bacillota	Bacilli	4.2	bsubtilis	Reference strain
GCF_000227465.1	Bacillus subtilis	BSn5	Bacteria	Bacillota	Bacilli	4.1	bsubtilis	Plant-associated strain
GCF_000496555.1	Bacillus subtilis	QB928	Bacteria	Bacillota	Bacilli	4.1	bsubtilis	Industrial strain
GCF_000006765.1	Pseudomonas aeruginosa	PAO1	Bacteria	Pseudomonadota	Gammaproteobacteria	6.3	paeruginosa	Reference strain
GCF_000014625.1	Pseudomonas aeruginosa	UCBPP-PA14	Bacteria	Pseudomonadota	Gammaproteobacteria	6.5	paeruginosa	Virulent clinical isolate
GCF_000006945.2	Pseudomonas aeruginosa	LESB58	Bacteria	Pseudomonadota	Gammaproteobacteria	6.6	paeruginosa	Liverpool epidemic strain
GCF_000195955.2	Mycobacterium tuberculosis	H37Rv	Bacteria	Actinomycetota	Actinomycetia	4.4	unique	Actinomycetia representative
GCF_000196035.1	Deinococcus radiodurans	R1	Bacteria	Deinococcota	Deinococci	3.3	unique	Radiation-resistant extremophile
GCF_000009065.1	Thermus thermophilus	HB8	Bacteria	Deinococcota	Deinococci	2.1	unique	Thermophile model organism
GCF_000011465.1	Caulobacter vibrioides	CB15	Bacteria	Pseudomonadota	Alphaproteobacteria	4.0	unique	Cell cycle model organism
GCF_000007145.1	Ralstonia solanacearum	GMI1000	Bacteria	Pseudomonadota	Betaproteobacteria	5.8	unique	Plant pathogen
GCF_000020225.1	Helicobacter pylori	26695	Bacteria	Campylobacterota	Epsilonproteobacteria	1.7	unique	Gastric pathogen
GCF_000195515.1	Clostridioides difficile	630	Bacteria	Bacillota	Clostridia	4.3	unique	Nosocomial pathogen
GCF_000011065.1	Bacteroides thetaiotaomicron	VPI-5482	Bacteria	Bacteroidota	Bacteroidia	6.3	unique	Gut commensal model
GCF_000006745.1	Vibrio cholerae	O1 N16961	Bacteria	Pseudomonadota	Gammaproteobacteria	4.0	unique	Cholera pandemic strain
GCF_000009725.1	Synechocystis sp.	PCC 6803	Bacteria	Cyanobacteriota	Cyanobacteriia	3.6	unique	Photosynthesis model
GCF_000008525.1	Treponema pallidum	Nichols	Bacteria	Spirochaetota	Spirochaetia	1.1	unique	Syphilis agent
GCF_000027305.1	Borreliella burgdorferi	B31	Bacteria	Spirochaetota	Spirochaetia	1.5	unique	Lyme disease agent
GCF_000027325.1	Chlamydia trachomatis	D/UW-3/CX	Bacteria	Chlamydiota	Chlamydiia	1.0	unique	Obligate intracellular pathogen
GCF_000008745.1	Mycoplasma genitalium	G37	Bacteria	Mycoplasmatota	Mollicutes	0.6	unique	Minimal genome organism
GCF_000016525.1	Rhodopirellula baltica	SH 1	Bacteria	Planctomycetota	Planctomycetia	7.1	unique	Marine planctomycete
GCF_000024845.1	Akkermansia muciniphila	ATCC BAA-835	Bacteria	Verrucomicrobiota	Verrucomicrobiae	2.7	unique	Gut mucin degrader
GCF_000018865.1	Dehalococcoides mccartyi	195	Bacteria	Chloroflexota	Dehalococcoidia	1.5	unique	Organohalide respirer
GCF_000007325.1	Fusobacterium nucleatum	ATCC 25586	Bacteria	Fusobacteriota	Fusobacteriia	2.2	unique	Oral/colorectal pathogen
GCF_000014005.1	Acidobacterium capsulatum	ATCC 51196	Bacteria	Acidobacteriota	Acidobacteriia	4.1	unique	Soil acidobacterium
GCF_000018285.1	Thermotoga maritima	MSB8	Bacteria	Thermotogota	Thermotogae	1.9	unique	Hyperthermophile
GCF_000025525.1	Aquifex aeolicus	VF5	Bacteria	Aquificota	Aquificae	1.6	unique	Deep-branching thermophile
GCF_000020965.1	Chlorobaculum tepidum	TLS	Bacteria	Chlorobiota	Chlorobia	2.2	unique	Green sulfur bacterium
GCF_000017945.1	Geobacter sulfurreducens	PCA	Bacteria	Desulfobacterota	Desulfuromonadia	3.8	unique	Metal-reducing bacterium
GCF_000015005.1	Lactiplantibacillus plantarum	WCFS1	Bacteria	Bacillota	Lactobacillia	3.3	unique	Probiotic lactic acid bacterium
GCF_000009985.1	Streptomyces coelicolor	A3(2)	Bacteria	Actinomycetota	Actinomycetia	8.7	unique	Antibiotic producer model
GCF_000195735.1	Corynebacterium glutamicum	ATCC 13032	Bacteria	Actinomycetota	Actinomycetia	3.3	unique	Industrial amino acid producer
GCF_000014165.1	Campylobacter jejuni	NCTC 11168	Bacteria	Campylobacterota	Campylobacteria	1.6	unique	Foodborne pathogen
GCF_000021665.1	Leptospira interrogans	serovar Lai	Bacteria	Spirochaetota	Leptospirae	4.6	unique	Zoonotic spirochete
GCF_000013925.1	Rickettsia prowazekii	Madrid E	Bacteria	Pseudomonadota	Alphaproteobacteria	1.1	unique	Obligate intracellular pathogen
GCF_000195915.1	Methanothermobacter thermautotrophicus	Delta H	Archaea	Euryarchaeota	Methanobacteria	1.8	unique	Methanogenic archaeon
GCF_000006805.1	Halobacterium salinarum	NRC-1	Archaea	Euryarchaeota	Halobacteria	2.6	unique	Extreme halophile
GCF_000007005.1	Sulfolobus solfataricus	P2	Archaea	Thermoproteota	Thermoprotei	3.0	unique	Thermoacidophilic archaeon
GCF_000018465.1	Nitrosopumilus maritimus	SCM1	Archaea	Nitrososphaerota	Nitrososphaeria	1.6	unique	Ammonia-oxidizing archaeon
GCF_000007205.1	Thermococcus kodakarensis	KOD1	Archaea	Euryarchaeota	Thermococci	2.1	unique	Hyperthermophilic archaeon
```

- [ ] **Step 2: Commit**

```bash
git add tests/data/test_genomes_manifest.tsv
git commit -m "feat: curated 50-genome test set manifest with taxonomic diversity and strain clusters"
```

---

### Task 7: Create Download Script

**Files:**
- Create: `tests/data/download_test_genomes.py`

- [ ] **Step 1: Create the download script**

`tests/data/download_test_genomes.py`:

```python
#!/usr/bin/env python3
"""Download test genomes from NCBI or a GitHub Release asset.

Usage:
    # Download from NCBI (primary):
    python tests/data/download_test_genomes.py --source ncbi

    # Download from GitHub Release (faster, pre-packaged):
    python tests/data/download_test_genomes.py --source github

    # Specify output directory:
    python tests/data/download_test_genomes.py --output-dir tests/data/genomes
"""
from __future__ import annotations
import argparse
import hashlib
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DEFAULT_MANIFEST = SCRIPT_DIR / "test_genomes_manifest.tsv"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "genomes"
GITHUB_REPO = "SDmetagenomics/meta-pipeline-MAGDrep"
RELEASE_TAG = "v0.1.0-testdata"
RELEASE_ASSET = "test_genomes_v1.tar.gz"


def read_manifest(manifest_path: Path) -> list[dict]:
    """Read the test genomes manifest TSV."""
    rows = []
    with open(manifest_path) as f:
        header = f.readline().strip().split("\t")
        for line in f:
            values = line.strip().split("\t")
            if values and values[0]:
                rows.append(dict(zip(header, values)))
    return rows


def download_from_ncbi(manifest: list[dict], output_dir: Path) -> None:
    """Download genomes from NCBI using the datasets CLI or curl fallback."""
    output_dir.mkdir(parents=True, exist_ok=True)

    use_datasets = shutil.which("datasets") is not None

    for entry in manifest:
        accession = entry["accession"]
        output_fasta = output_dir / f"{accession}.fna"

        if output_fasta.exists():
            print(f"  [skip] {accession} — already exists")
            continue

        print(f"  [download] {accession} ({entry['organism']} {entry['strain']})")

        if use_datasets:
            _download_via_datasets(accession, output_fasta)
        else:
            _download_via_curl(accession, output_fasta)

        if not output_fasta.exists():
            print(f"  [WARN] Failed to download {accession}", file=sys.stderr)


def _download_via_datasets(accession: str, output_fasta: Path) -> None:
    """Download using NCBI datasets CLI."""
    import tempfile
    import zipfile

    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "genome.zip"
        subprocess.run(
            ["datasets", "download", "genome", "accession", accession,
             "--include", "genome", "--filename", str(zip_path)],
            check=True, capture_output=True,
        )
        with zipfile.ZipFile(zip_path) as zf:
            # Find the genomic FASTA inside the zip
            fasta_files = [n for n in zf.namelist() if n.endswith("_genomic.fna")]
            if not fasta_files:
                raise FileNotFoundError(f"No genomic FASTA in download for {accession}")
            with zf.open(fasta_files[0]) as src, open(output_fasta, "wb") as dst:
                dst.write(src.read())


def _download_via_curl(accession: str, output_fasta: Path) -> None:
    """Download via NCBI FTP using curl."""
    # Convert accession to FTP path
    # GCF_000005845.2 -> GCF/000/005/845/GCF_000005845.2
    parts = accession.split("_")
    prefix = parts[0]
    number = parts[1].split(".")[0]  # "000005845"
    chunks = [number[i:i+3] for i in range(0, 9, 3)]
    ftp_dir = f"https://ftp.ncbi.nlm.nih.gov/genomes/all/{prefix}/{'/'.join(chunks)}/{accession}"

    # Try to get the assembly directory listing and find the FASTA
    result = subprocess.run(
        ["curl", "-sL", f"{ftp_dir}/"],
        capture_output=True, text=True,
    )

    # Find the assembly directory name from the listing
    lines = result.stdout.strip().split("\n")
    asm_dir = None
    for line in lines:
        if accession in line and "genomic" not in line:
            # Extract directory name from HTML listing
            import re
            match = re.search(rf'href="({accession}[^"]*)"', line)
            if match:
                asm_dir = match.group(1).rstrip("/")
                break

    if asm_dir:
        fasta_url = f"{ftp_dir}/{asm_dir}/{asm_dir}_genomic.fna.gz"
    else:
        # Direct attempt with accession
        fasta_url = f"{ftp_dir}/{accession}_genomic.fna.gz"

    import gzip
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".fna.gz", delete=False) as tmp:
        tmp_path = tmp.name

    subprocess.run(
        ["curl", "-sL", "-o", tmp_path, fasta_url],
        check=True,
    )

    # Decompress
    with gzip.open(tmp_path, "rb") as f_in, open(output_fasta, "wb") as f_out:
        f_out.write(f_in.read())

    Path(tmp_path).unlink()


def download_from_github(output_dir: Path) -> None:
    """Download pre-packaged genomes from GitHub Release."""
    output_dir.mkdir(parents=True, exist_ok=True)

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tarball = Path(tmpdir) / RELEASE_ASSET

        # Try gh CLI first, fall back to curl
        if shutil.which("gh"):
            subprocess.run(
                ["gh", "release", "download", RELEASE_TAG,
                 "--repo", GITHUB_REPO,
                 "--pattern", RELEASE_ASSET,
                 "--dir", tmpdir],
                check=True,
            )
        else:
            url = f"https://github.com/{GITHUB_REPO}/releases/download/{RELEASE_TAG}/{RELEASE_ASSET}"
            subprocess.run(
                ["curl", "-sL", "-o", str(tarball), url],
                check=True,
            )

        # Extract
        with tarfile.open(tarball, "r:gz") as tar:
            tar.extractall(path=output_dir)

    print(f"Extracted genomes to {output_dir}")


def main():
    parser = argparse.ArgumentParser(description="Download test genomes")
    parser.add_argument("--source", choices=["ncbi", "github"], default="github",
                        help="Download source (default: github)")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST,
                        help="Path to manifest TSV")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                        help="Output directory for genomes")
    args = parser.parse_args()

    if args.source == "github":
        print(f"Downloading test genomes from GitHub Release ({RELEASE_TAG})...")
        download_from_github(args.output_dir)
    else:
        print("Downloading test genomes from NCBI...")
        manifest = read_manifest(args.manifest)
        print(f"  {len(manifest)} genomes in manifest")
        download_from_ncbi(manifest, args.output_dir)

    # Count results
    fasta_count = len(list(args.output_dir.glob("*.fna")))
    print(f"Done. {fasta_count} genomes in {args.output_dir}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make it executable**

```bash
chmod +x tests/data/download_test_genomes.py
```

- [ ] **Step 3: Add genomes/ to .gitignore**

Create or append to `.gitignore`:
```
tests/data/genomes/
```

- [ ] **Step 4: Commit**

```bash
git add tests/data/download_test_genomes.py .gitignore
git commit -m "feat: download script for 50 test genomes from NCBI or GitHub Release"
```

---

### Task 8: Update conftest.py with Test Genome Fixtures

**Files:**
- Modify: `tests/conftest.py`

- [ ] **Step 1: Add test genome fixtures to conftest.py**

Add after the existing fixtures:

```python
TEST_GENOMES_DIR = TEST_DATA_DIR / "genomes"
TEST_GENOMES_MANIFEST = TEST_DATA_DIR / "test_genomes_manifest.tsv"


@pytest.fixture(scope="session")
def test_genomes_dir():
    """
    Return path to the 50 real test genomes.
    Downloads from GitHub Release on first access if not present locally.
    """
    if TEST_GENOMES_DIR.exists() and len(list(TEST_GENOMES_DIR.glob("*.fna"))) >= 50:
        return TEST_GENOMES_DIR

    # Auto-download from GitHub Release
    import subprocess
    download_script = TEST_DATA_DIR / "download_test_genomes.py"
    subprocess.run(
        [sys.executable, str(download_script),
         "--source", "github",
         "--output-dir", str(TEST_GENOMES_DIR)],
        check=True,
    )
    return TEST_GENOMES_DIR
```

Also add `import sys` at the top of conftest.py.

- [ ] **Step 2: Run existing tests to confirm nothing broke**

```bash
python -m pytest tests/ -v --ignore=tests/test_integration.py
```

Expected: 50 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "feat: conftest fixture for auto-downloading test genomes"
```

---

### Task 9: Download Genomes from NCBI and Create GitHub Release

- [ ] **Step 1: Download all 50 genomes from NCBI**

```bash
python tests/data/download_test_genomes.py --source ncbi --output-dir tests/data/genomes
```

This may take 5-10 minutes. Verify all 50 downloaded:
```bash
ls tests/data/genomes/*.fna | wc -l
```
Expected: 50

- [ ] **Step 2: Verify accessions match manifest**

```bash
python -c "
from pathlib import Path
manifest_ids = set()
with open('tests/data/test_genomes_manifest.tsv') as f:
    next(f)  # skip header
    for line in f:
        manifest_ids.add(line.split('\t')[0])
downloaded = {p.stem for p in Path('tests/data/genomes').glob('*.fna')}
missing = manifest_ids - downloaded
extra = downloaded - manifest_ids
print(f'Manifest: {len(manifest_ids)}, Downloaded: {len(downloaded)}')
if missing: print(f'MISSING: {missing}')
if extra: print(f'EXTRA: {extra}')
if not missing and not extra: print('All accessions match.')
"
```

- [ ] **Step 3: Create the tarball**

```bash
cd tests/data
tar czf test_genomes_v1.tar.gz -C genomes .
ls -lh test_genomes_v1.tar.gz
cd /Users/sdiamond/Dropbox/Informatics/Dev/Claude_Projects/meta-pipeline-MAGQC
```

- [ ] **Step 4: Create the GitHub Release with the tarball**

```bash
gh release create v0.1.0-testdata \
  tests/data/test_genomes_v1.tar.gz \
  --repo SDmetagenomics/meta-pipeline-MAGDrep \
  --title "Test Genomes v1 (50 NCBI RefSeq genomes)" \
  --notes "$(cat <<'EOF'
## Test Genome Set v1

50 complete prokaryotic genomes from NCBI RefSeq for end-to-end pipeline testing.

### Contents

- **15 same-species strains** (4 species) for dereplication testing at 95% ANI
  - 5 Escherichia coli strains
  - 4 Staphylococcus aureus strains
  - 3 Bacillus subtilis strains
  - 3 Pseudomonas aeruginosa strains
- **35 taxonomically diverse genomes** spanning major bacterial and archaeal phyla/classes
  - 30 Bacteria across Pseudomonadota, Bacillota, Actinomycetota, Bacteroidota, Cyanobacteriota, Spirochaetota, Deinococcota, Campylobacterota, Chlamydiota, Mycoplasmatota, Planctomycetota, Verrucomicrobiota, Chloroflexota, Fusobacteriota, Acidobacteriota, Thermotogota, Aquificota, Chlorobiota, Desulfobacterota
  - 5 Archaea across Euryarchaeota, Thermoproteota, Nitrososphaerota

### Usage

```bash
# Automatic (via pipeline test fixtures):
pytest tests/ -m slow

# Manual download:
python tests/data/download_test_genomes.py --source github
```

### File format

50 uncompressed FASTA files named by RefSeq accession (e.g., `GCF_000005845.2.fna`).

See `tests/data/test_genomes_manifest.tsv` for full metadata.
EOF
)"
```

- [ ] **Step 5: Clean up the local tarball**

```bash
rm tests/data/test_genomes_v1.tar.gz
```

- [ ] **Step 6: Push all commits**

```bash
git push origin main
```

---

### Task 10: Final Verification

- [ ] **Step 1: Run all unit tests**

```bash
python -m pytest tests/ -v --ignore=tests/test_integration.py
```

Expected: 50 passed.

- [ ] **Step 2: Verify CLI works with new name**

```bash
meta-pipeline-MAGDrep --version
meta-pipeline-MAGDrep --help
meta-pipeline-MAGDrep qc --help
meta-pipeline-MAGDrep db status
```

- [ ] **Step 3: Verify GitHub Release download works**

```bash
rm -rf tests/data/genomes
python tests/data/download_test_genomes.py --source github
ls tests/data/genomes/*.fna | wc -l
```

Expected: 50

- [ ] **Step 4: Verify repo URL**

```bash
gh repo view SDmetagenomics/meta-pipeline-MAGDrep --json name,url
```

---

## Notes

- **Accession verification**: Some accessions in the manifest are from training data. The download script will report failures; replace any invalid accessions with alternates from the same class.
- **NCBI datasets CLI**: The preferred download method. Install via `conda install -c conda-forge ncbi-datasets-cli` if not available. The curl fallback handles cases where datasets is not installed.
- **GitHub Release size**: The tarball should be ~150 MB. GitHub Releases support up to 2 GB per asset.
- **Local directory ignored**: `tests/data/genomes/` is in `.gitignore` — genomes are never committed to git.
