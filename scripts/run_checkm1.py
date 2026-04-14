"""Batch runner for CheckM1 (ecogenomics/CheckM) lineage_wf.

CheckM1 lives in a sibling conda environment (`magdrep-checkm1`) because
its Python version requirements are incompatible with CheckM2's.
This script shells out to that env via `conda run`.

Parses CheckM1's tab-delimited summary into the same schema used by
run_checkm2.py so downstream merge_reports.py can treat both as
interchangeable sources for completeness/contamination. Additionally
emits `strain_heterogeneity` which CheckM2 does not provide — used by
the dereplication composite score.
"""
from __future__ import annotations
import os
import shutil
import subprocess
from pathlib import Path


CHECKM1_ENV = "magdrep-checkm1"


def _resolve_checkm1_db(db_path: str) -> str:
    """Return a directory path suitable for CHECKM_DATA_PATH.

    CheckM1's reference data lives in a flat directory — whatever the
    user points us at. Accept either that directory directly or a
    parent that contains a `checkm1/` subdir."""
    p = Path(db_path)
    if (p / "selected_marker_sets.tsv").exists():
        return str(p)
    sub = p / "checkm1"
    if sub.is_dir():
        return str(sub)
    return str(p)


def parse_checkm1_output(report_path: Path) -> list[dict]:
    """Parse CheckM1's --tab_table summary into our canonical schema.

    Expected columns: Bin Id, Marker lineage, # genomes, # markers,
    # marker sets, 0, 1, 2, 3, 4, 5+, Completeness, Contamination,
    Strain heterogeneity.
    """
    rows = []
    with open(report_path) as f:
        header = f.readline().rstrip("\n").split("\t")

        def col(name: str) -> int | None:
            try:
                return header.index(name)
            except ValueError:
                return None

        i_binid = col("Bin Id")
        i_lineage = col("Marker lineage")
        i_comp = col("Completeness")
        i_contam = col("Contamination")
        i_strain = col("Strain heterogeneity")

        for line in f:
            values = line.rstrip("\n").split("\t")
            if not values or not values[0]:
                continue
            rows.append({
                "mag_id": values[i_binid] if i_binid is not None else values[0],
                "checkm1_marker_lineage": values[i_lineage] if i_lineage is not None else "",
                "completeness": float(values[i_comp]) if i_comp is not None else 0.0,
                "contamination": float(values[i_contam]) if i_contam is not None else 0.0,
                "strain_heterogeneity": float(values[i_strain]) if i_strain is not None else 0.0,
            })
    return rows


def write_output_tsv(rows: list[dict], output_path: Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        # Still emit a header so merge_reports can left-join safely.
        with open(output_path, "w") as f:
            f.write("mag_id\tcheckm1_marker_lineage\tcompleteness\tcontamination\tstrain_heterogeneity\n")
        return
    keys = list(rows[0].keys())
    with open(output_path, "w") as f:
        f.write("\t".join(keys) + "\n")
        for row in rows:
            f.write("\t".join(str(row[k]) for k in keys) + "\n")


def _conda_available() -> bool:
    return shutil.which("conda") is not None or "CONDA_EXE" in os.environ


def run_checkm1(
    input_dir: str, output_dir: str, output_tsv: str,
    threads: int = 16, db_path: str | None = None,
    extension: str | None = None,
) -> None:
    """Run CheckM1 lineage_wf on a directory of genomes.

    Auto-detects the FASTA file extension from the input dir unless one
    is passed in explicitly. Writes a clean TSV to *output_tsv*.
    """
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    summary = Path(output_dir) / "checkm1_summary.tsv"

    input_path = Path(input_dir)
    if extension is None:
        for ext in (".fna", ".fasta", ".fa"):
            if list(input_path.glob(f"*{ext}")):
                extension = ext.lstrip(".")
                break
        if extension is None:
            raise FileNotFoundError(
                f"No FASTA files with extension .fna/.fasta/.fa found in {input_dir}"
            )

    base_cmd = [
        "checkm", "lineage_wf",
        "--tab_table",
        "-f", str(summary),
        "--threads", str(threads),
        "--extension", extension,
        input_dir,
        output_dir,
    ]

    # CheckM1 reads its data path from the CHECKM_DATA_PATH env var or
    # a global `checkm data setRoot` config. We prefer the env var so
    # multiple parallel invocations don't race on the config file.
    env = {**os.environ}
    if db_path:
        env["CHECKM_DATA_PATH"] = _resolve_checkm1_db(db_path)

    if _conda_available():
        cmd = ["conda", "run", "-n", CHECKM1_ENV, "--no-capture-output"] + base_cmd
    else:
        cmd = base_cmd  # assume caller already activated the right env

    subprocess.run(cmd, check=True, env=env)

    if not summary.exists():
        raise FileNotFoundError(f"CheckM1 output not found: {summary}")

    rows = parse_checkm1_output(summary)
    write_output_tsv(rows, Path(output_tsv))


if __name__ == "__main__":
    import sys
    run_checkm1(
        input_dir=sys.argv[1],
        output_dir=sys.argv[2],
        output_tsv=sys.argv[3],
        threads=int(sys.argv[4]),
        db_path=sys.argv[5] if len(sys.argv) > 5 else None,
    )
