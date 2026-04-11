"""Batch runner for CheckM2 predict."""
from __future__ import annotations
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


def run_checkm2(input_dir: str, output_dir: str, output_tsv: str, threads: int = 16) -> None:
    """Run CheckM2 predict on a directory of genomes."""
    cmd = [
        "checkm2", "predict",
        "--input", input_dir,
        "--output-directory", output_dir,
        "--threads", str(threads),
        "--force",
    ]
    subprocess.run(cmd, check=True)

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
    )
