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
import gzip
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
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
            print(f"  [skip] {accession} -- already exists")
            continue

        print(f"  [download] {accession} ({entry['organism']} {entry['strain']})")

        try:
            if use_datasets:
                _download_via_datasets(accession, output_fasta)
            else:
                _download_via_curl(accession, output_fasta)
        except Exception as e:
            print(f"  [WARN] Failed to download {accession}: {e}", file=sys.stderr)


def _download_via_datasets(accession: str, output_fasta: Path) -> None:
    """Download using NCBI datasets CLI."""
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = Path(tmpdir) / "genome.zip"
        subprocess.run(
            ["datasets", "download", "genome", "accession", accession,
             "--include", "genome", "--filename", str(zip_path)],
            check=True, capture_output=True,
        )
        with zipfile.ZipFile(zip_path) as zf:
            fasta_files = [n for n in zf.namelist() if n.endswith("_genomic.fna")]
            if not fasta_files:
                raise FileNotFoundError(f"No genomic FASTA in download for {accession}")
            with zf.open(fasta_files[0]) as src, open(output_fasta, "wb") as dst:
                dst.write(src.read())


def _download_via_curl(accession: str, output_fasta: Path) -> None:
    """Download via NCBI FTP using curl."""
    parts = accession.split("_")
    prefix = parts[0]
    number = parts[1].split(".")[0]
    chunks = [number[i:i+3] for i in range(0, 9, 3)]
    ftp_dir = f"https://ftp.ncbi.nlm.nih.gov/genomes/all/{prefix}/{'/'.join(chunks)}"

    # List the directory to find the assembly folder name
    result = subprocess.run(
        ["curl", "-sL", f"{ftp_dir}/"],
        capture_output=True, text=True,
    )

    asm_dir = None
    for match in re.finditer(rf'href="({re.escape(accession)}[^"]*)"', result.stdout):
        candidate = match.group(1).rstrip("/")
        if "_genomic" not in candidate:
            asm_dir = candidate
            break

    if not asm_dir:
        asm_dir = accession

    fasta_url = f"{ftp_dir}/{asm_dir}/{asm_dir}_genomic.fna.gz"

    with tempfile.NamedTemporaryFile(suffix=".fna.gz", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        subprocess.run(["curl", "-sL", "-o", str(tmp_path), fasta_url], check=True)
        with gzip.open(tmp_path, "rb") as f_in, open(output_fasta, "wb") as f_out:
            f_out.write(f_in.read())
    finally:
        tmp_path.unlink(missing_ok=True)


def download_from_github(output_dir: Path) -> None:
    """Download pre-packaged genomes from GitHub Release."""
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tarball = Path(tmpdir) / RELEASE_ASSET

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
            subprocess.run(["curl", "-sL", "-o", str(tarball), url], check=True)

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

    fasta_count = len(list(args.output_dir.glob("*.fna")))
    print(f"Done. {fasta_count} genomes in {args.output_dir}")


if __name__ == "__main__":
    main()
