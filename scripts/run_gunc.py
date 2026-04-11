"""Batch runner for GUNC chimerism detection."""
from __future__ import annotations
import subprocess
from pathlib import Path


def parse_gunc_output(report_path: Path, css_threshold: float = 0.45) -> list[dict]:
    """
    Parse GUNC's GUNC.maxCSS_level.tsv output.
    The pass_gunc field is recomputed from css_threshold for configurability.
    """
    rows = []
    with open(report_path) as f:
        header = f.readline().strip().split("\t")
        for line in f:
            values = line.strip().split("\t")
            if not values or not values[0]:
                continue
            row = dict(zip(header, values))
            css = float(row.get("clade_separation_score", 0))
            rows.append({
                "mag_id": row["genome"],
                "css": css,
                "rrs": float(row.get("reference_representation_score", 0)),
                "contamination_portion": float(row.get("contamination_portion", 0)),
                "taxonomic_level": row.get("taxonomic_level", ""),
                "pass_gunc": css < css_threshold,
            })
    return rows


def write_output_tsv(rows: list[dict], output_path: Path) -> None:
    """Write parsed GUNC results to a TSV."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    keys = list(rows[0].keys())
    with open(output_path, "w") as f:
        f.write("\t".join(keys) + "\n")
        for row in rows:
            f.write("\t".join(str(row[k]) for k in keys) + "\n")


def run_gunc(
    input_dir: str, output_dir: str, output_tsv: str,
    threads: int = 16, db_type: str = "gtdb_214"
) -> None:
    """Run GUNC on a directory of genomes."""
    cmd = [
        "gunc", "run",
        "--input_dir", input_dir,
        "--out_dir", output_dir,
        "--threads", str(threads),
        "--db_file", db_type,
    ]
    subprocess.run(cmd, check=True)

    report = Path(output_dir) / "GUNC.maxCSS_level.tsv"
    if not report.exists():
        raise FileNotFoundError(f"GUNC output not found: {report}")

    rows = parse_gunc_output(report)
    write_output_tsv(rows, Path(output_tsv))


if __name__ == "__main__":
    import sys
    run_gunc(
        input_dir=sys.argv[1],
        output_dir=sys.argv[2],
        output_tsv=sys.argv[3],
        threads=int(sys.argv[4]),
        db_type=sys.argv[5] if len(sys.argv) > 5 else "gtdb_214",
    )
