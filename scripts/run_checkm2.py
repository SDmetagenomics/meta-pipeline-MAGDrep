"""Batch runner for CheckM2 predict."""
from __future__ import annotations
import os
import subprocess
from pathlib import Path


def parse_checkm2_output(report_path: Path) -> list[dict]:
    """
    Parse CheckM2 quality_report.tsv into a list of dicts.
    Renames 'Name' -> 'mag_id' and normalizes column names.
    """
    rows = []
    with open(report_path) as f:
        header = f.readline().strip().split("\t")
        for line in f:
            values = line.strip().split("\t")
            row = dict(zip(header, values))
            rows.append({
                "mag_id": row["Name"],
                "completeness": float(row["Completeness"]),
                "contamination": float(row["Contamination"]),
                "completeness_model_used": row.get("Completeness_Model_Used", ""),
                "translation_table_used": row.get("Translation_Table_Used", ""),
            })
    return rows


def write_output_tsv(rows: list[dict], output_path: Path) -> None:
    """Write parsed CheckM2 results to a TSV."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(output_path, "w") as f:
        f.write("\t".join(keys) + "\n")
        for row in rows:
            f.write("\t".join(str(row[k]) for k in keys) + "\n")


def _resolve_checkm2_db(db_path: str) -> str:
    """Resolve a CheckM2 database path to the actual .dmnd file.

    CheckM2's --database_path requires a file, not a directory.
    If given a directory, find the .dmnd file inside it.
    """
    p = Path(db_path)
    if p.is_file():
        return str(p)
    if p.is_dir():
        dmnd_files = sorted(p.rglob("*.dmnd"))
        if dmnd_files:
            return str(dmnd_files[0])
    return str(p)


def run_checkm2(
    input_dir: str, output_dir: str, output_tsv: str,
    threads: int = 16, db_path: str | None = None,
) -> None:
    """Run CheckM2 predict on a directory of genomes."""
    cmd = [
        "checkm2", "predict",
        "--input", input_dir,
        "--output-directory", output_dir,
        "--threads", str(threads),
        "--force",
    ]
    if db_path:
        cmd.extend(["--database_path", _resolve_checkm2_db(db_path)])

    # CheckM2 1.1.0 multiprocessing fails with Python 3.12's "spawn" start
    # method on macOS — private methods can't be pickled. Force "fork" by
    # calling checkm2 through a wrapper that sets the start method first.
    wrapper = (
        "import multiprocessing; multiprocessing.set_start_method('fork', force=True); "
        "import sys; sys.argv = {argv!r}; "
        "from checkm2.main import main; main()"
    ).format(argv=cmd)
    subprocess.run(["python", "-c", wrapper], check=True)

    report = Path(output_dir) / "quality_report.tsv"
    if not report.exists():
        raise FileNotFoundError(f"CheckM2 output not found: {report}")

    rows = parse_checkm2_output(report)
    write_output_tsv(rows, Path(output_tsv))


if __name__ == "__main__":
    import sys
    run_checkm2(
        input_dir=sys.argv[1],
        output_dir=sys.argv[2],
        output_tsv=sys.argv[3],
        threads=int(sys.argv[4]),
        db_path=sys.argv[5] if len(sys.argv) > 5 else None,
    )
