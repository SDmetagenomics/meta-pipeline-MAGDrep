"""Batch runner for GTDB-Tk classify_wf."""
from __future__ import annotations
import subprocess
from pathlib import Path

_RANKS = ["domain", "phylum", "class", "order", "family", "genus", "species"]
_RANK_PREFIXES = ["d__", "p__", "c__", "o__", "f__", "g__", "s__"]


def _parse_classification(classification_string: str) -> dict:
    """Parse GTDB classification string into individual rank columns."""
    result = {r: "" for r in _RANKS}
    if not classification_string or classification_string == "N/A":
        return result
    parts = classification_string.split(";")
    for part in parts:
        for rank, prefix in zip(_RANKS, _RANK_PREFIXES):
            if part.startswith(prefix):
                result[rank] = part[len(prefix):]
                break
    return result


def _parse_summary_tsv(path: Path) -> list[dict]:
    """Parse a single GTDB-Tk summary TSV (bac120 or ar53)."""
    rows = []
    if not path.exists():
        return rows
    with open(path) as f:
        header = f.readline().strip().split("\t")
        for line in f:
            values = line.strip().split("\t")
            if not values or not values[0]:
                continue
            raw = dict(zip(header, values))
            ranks = _parse_classification(raw.get("classification", ""))

            def safe_float(val):
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None

            # Strip MAG_ prefix added to avoid GTDB-Tk reference ID collisions
            genome_id = raw["user_genome"]
            if genome_id.startswith("MAG_"):
                genome_id = genome_id[4:]

            rows.append({
                "mag_id": genome_id,
                **ranks,
                "classification": raw.get("classification", ""),
                "fastani_reference": raw.get("fastani_reference", ""),
                "fastani_ani": safe_float(raw.get("fastani_ani")),
                "fastani_af": safe_float(raw.get("fastani_af")),
                "classification_method": raw.get("classification_method", ""),
                "note": raw.get("note", ""),
                "warnings": raw.get("warnings", ""),
            })
    return rows


def parse_gtdbtk_output(
    bac120_path: Path | None = None,
    ar53_path: Path | None = None,
) -> list[dict]:
    """Parse both bac120 and ar53 summary files, merge into one list."""
    rows = []
    if bac120_path:
        rows.extend(_parse_summary_tsv(Path(bac120_path)))
    if ar53_path:
        rows.extend(_parse_summary_tsv(Path(ar53_path)))
    return rows


def write_output_tsv(rows: list[dict], output_path: Path) -> None:
    """Write parsed GTDB-Tk results to a TSV."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        keys = ["mag_id"] + _RANKS + [
            "classification", "fastani_reference", "fastani_ani",
            "fastani_af", "classification_method", "note", "warnings",
        ]
        with open(output_path, "w") as f:
            f.write("\t".join(keys) + "\n")
        return
    keys = list(rows[0].keys())
    with open(output_path, "w") as f:
        f.write("\t".join(keys) + "\n")
        for row in rows:
            f.write("\t".join(str(row.get(k, "")) for k in keys) + "\n")


def run_gtdbtk(
    input_dir: str, output_dir: str, output_tsv: str,
    threads: int = 64, pplacer_cpus: int = 1,
    skip_ani_screen: bool = False,
    db_path: str | None = None,
) -> None:
    """Run GTDB-Tk classify_wf on a directory of genomes."""
    cmd = [
        "gtdbtk", "classify_wf",
        "--genome_dir", input_dir,
        "--out_dir", output_dir,
        "--cpus", str(threads),
        "--pplacer_cpus", str(pplacer_cpus),
    ]
    if skip_ani_screen:
        cmd.append("--skip_ani_screen")

    input_path = Path(input_dir)
    for ext in (".fna", ".fasta", ".fa", ".fna.gz", ".fasta.gz", ".fa.gz"):
        if list(input_path.glob(f"*{ext}")):
            cmd.extend(["--extension", ext.lstrip(".")])
            break

    # Use node-local scratch if TMPDIR points to fast local storage
    # (e.g. SLURM's /tmp/$JOB_ID). Falls back to GTDB-Tk default otherwise.
    import os
    tmpdir = os.environ.get("TMPDIR")
    if tmpdir and Path(tmpdir).exists():
        cmd.extend(["--scratch_dir", tmpdir])

    env = None
    if db_path:
        env = {**os.environ, "GTDBTK_DATA_PATH": db_path}

    subprocess.run(cmd, check=True, env=env)

    out_path = Path(output_dir)
    bac = out_path / "classify" / "gtdbtk.bac120.summary.tsv"
    ar = out_path / "classify" / "gtdbtk.ar53.summary.tsv"
    rows = parse_gtdbtk_output(
        bac120_path=bac if bac.exists() else None,
        ar53_path=ar if ar.exists() else None,
    )
    write_output_tsv(rows, Path(output_tsv))


if __name__ == "__main__":
    import sys
    run_gtdbtk(
        input_dir=sys.argv[1],
        output_dir=sys.argv[2],
        output_tsv=sys.argv[3],
        threads=int(sys.argv[4]),
        pplacer_cpus=int(sys.argv[5]) if len(sys.argv) > 5 else 1,
        skip_ani_screen=sys.argv[6].lower() == "true" if len(sys.argv) > 6 else False,
        db_path=sys.argv[7] if len(sys.argv) > 7 else None,
    )
