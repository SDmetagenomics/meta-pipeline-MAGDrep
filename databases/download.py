"""
Download and cache reference databases for MAGDrep.
Called by `meta-pipeline-MAGDrep db update`.

Each tool's CLI handles its own download logic; we orchestrate and
track completion with sentinel files so re-runs are fast.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# Database metadata: tool CLI commands and expected artifacts
DATABASES = {
    "checkm1": {
        "display_name": "CheckM1 (2015-01-16)",
        "size_hint": "~1.4 GB",
        "sentinel": "checkm1.ok",
    },
    "checkm2": {
        "display_name": "CheckM2",
        "size_hint": "~3 GB",
        "sentinel": "checkm2.ok",
    },
    "gtdbtk": {
        "display_name": "GTDB-Tk (r226)",
        "size_hint": "~85 GB",
        "sentinel": "gtdbtk.ok",
    },
}


CHECKM1_DB_URL = "https://data.ace.uq.edu.au/public/CheckM_databases/checkm_data_2015_01_16.tar.gz"
CHECKM1_ENV = "magdrep-checkm1"


def download_checkm1(db_dir: Path, force: bool = False) -> Path:
    """Download and unpack CheckM1 reference data."""
    checkm1_dir = db_dir / "checkm1"
    sentinel = checkm1_dir / DATABASES["checkm1"]["sentinel"]

    if sentinel.exists() and not force:
        print(f"  CheckM1 database already present (sentinel: {sentinel})")
        return checkm1_dir

    checkm1_dir.mkdir(parents=True, exist_ok=True)
    tarball = checkm1_dir / "checkm_data_2015_01_16.tar.gz"

    print("  Downloading CheckM1 database (~1.4 GB)...")
    subprocess.run(["curl", "-L", "-o", str(tarball), CHECKM1_DB_URL], check=True)

    print("  Extracting CheckM1 archive...")
    subprocess.run(["tar", "xzf", str(tarball), "-C", str(checkm1_dir)], check=True)
    tarball.unlink()

    # Verify a canonical marker-set file is present
    marker_file = checkm1_dir / "selected_marker_sets.tsv"
    if not marker_file.exists():
        # Some tarballs nest the files one level deep — detect and flatten.
        nested = list(checkm1_dir.glob("*/selected_marker_sets.tsv"))
        if nested:
            from shutil import move
            inner = nested[0].parent
            for item in inner.iterdir():
                move(str(item), str(checkm1_dir / item.name))
            inner.rmdir()

    if not (checkm1_dir / "selected_marker_sets.tsv").exists():
        raise RuntimeError(
            f"CheckM1 download completed but selected_marker_sets.tsv missing in {checkm1_dir}"
        )

    sentinel.touch()
    print(f"  CheckM1 ready at {checkm1_dir}")
    return checkm1_dir


def download_checkm2(db_dir: Path, force: bool = False) -> Path:
    """Download CheckM2 diamond database."""
    checkm2_dir = db_dir / "checkm2"
    sentinel = checkm2_dir / DATABASES["checkm2"]["sentinel"]

    if sentinel.exists() and not force:
        print(f"  CheckM2 database already present (sentinel: {sentinel})")
        return checkm2_dir

    checkm2_dir.mkdir(parents=True, exist_ok=True)
    print("  Downloading CheckM2 database (~3 GB)...")
    subprocess.run(
        ["checkm2", "database", "--download", "--path", str(checkm2_dir)],
        check=True,
    )

    # Verify the download produced the expected file
    dmnd_files = list(checkm2_dir.rglob("*.dmnd"))
    if not dmnd_files:
        raise RuntimeError(f"CheckM2 download completed but no .dmnd file found in {checkm2_dir}")

    sentinel.touch()
    print(f"  CheckM2 ready at {checkm2_dir}")
    return checkm2_dir


GTDBTK_DB_URL = (
    "https://data.gtdb.aau.ecogenomic.org/releases/release226/226.0/"
    "auxillary_files/gtdbtk_package/full_package/gtdbtk_r226_data.tar.gz"
)


def download_gtdbtk(db_dir: Path, force: bool = False) -> Path:
    """Download GTDB-Tk r226 reference package."""
    gtdbtk_dir = db_dir / "gtdbtk"
    sentinel = gtdbtk_dir / DATABASES["gtdbtk"]["sentinel"]

    if sentinel.exists() and not force:
        print(f"  GTDB-Tk database already present (sentinel: {sentinel})")
        return gtdbtk_dir

    gtdbtk_dir.mkdir(parents=True, exist_ok=True)
    print("  Downloading GTDB-Tk r226 database (~85 GB)...")
    print("  This will take a while — go get a coffee.")

    tarball = gtdbtk_dir / "gtdbtk_r226_data.tar.gz"

    # Try download-db.sh first (bundled with gtdbtk conda package),
    # fall back to curl if wget is not available.
    try:
        subprocess.run(
            ["download-db.sh", str(gtdbtk_dir)],
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("  download-db.sh failed, falling back to curl...")
        subprocess.run(
            ["curl", "-L", "-o", str(tarball), GTDBTK_DB_URL],
            check=True,
        )
        print("  Extracting archive...")
        subprocess.run(
            ["tar", "xzf", str(tarball), "-C", str(gtdbtk_dir), "--strip-components", "1"],
            check=True,
        )
        tarball.unlink()

    # Verify key files exist
    taxonomy_dir = gtdbtk_dir / "taxonomy"
    if not taxonomy_dir.exists():
        raise RuntimeError(
            f"GTDB-Tk download completed but expected directory not found: {taxonomy_dir}"
        )

    sentinel.touch()
    print(f"  GTDB-Tk ready at {gtdbtk_dir}")
    return gtdbtk_dir


_DOWNLOADERS = {
    "checkm1": download_checkm1,
    "checkm2": download_checkm2,
    "gtdbtk": download_gtdbtk,
}


def download_all_databases(db_dir: Path, force: bool = False) -> dict[str, Path]:
    """Download all required databases. Returns {name: path} dict."""
    db_dir = Path(db_dir)
    db_dir.mkdir(parents=True, exist_ok=True)

    paths = {}
    for name, downloader in _DOWNLOADERS.items():
        meta = DATABASES[name]
        print(f"\n[{meta['display_name']}] ({meta['size_hint']})")
        try:
            paths[name] = downloader(db_dir, force=force)
        except Exception as exc:
            print(f"  ERROR: {exc}", file=sys.stderr)
            raise
    return paths


def database_status(db_dir: Path) -> dict[str, dict]:
    """Check which databases are installed. Returns status dict."""
    db_dir = Path(db_dir)
    status = {}
    for name, meta in DATABASES.items():
        tool_dir = db_dir / name
        sentinel = tool_dir / meta["sentinel"]
        status[name] = {
            "display_name": meta["display_name"],
            "size_hint": meta["size_hint"],
            "path": str(tool_dir),
            "present": sentinel.exists(),
            "directory_exists": tool_dir.exists(),
        }
    return status


if __name__ == "__main__":
    db_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("databases")
    download_all_databases(db_dir)
