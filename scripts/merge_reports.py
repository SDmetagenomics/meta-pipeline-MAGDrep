"""Merge genome_stats + CheckM2 + GUNC + GTDB-Tk reports and assign quality tiers."""
from __future__ import annotations
import ast
from pathlib import Path


def _read_tsv(path: str | Path) -> list[dict]:
    """Read a TSV file into a list of dicts."""
    rows = []
    path = Path(path)
    if not path.exists() or path.stat().st_size == 0:
        return rows
    with open(path) as f:
        header = f.readline().strip().split("\t")
        for line in f:
            values = line.strip().split("\t")
            if values and values[0]:
                rows.append(dict(zip(header, values)))
    return rows


def _to_float(val, default=None):
    """Safely convert a value to float."""
    if val is None or val == "" or val == "None" or val == "N/A":
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _to_bool(val, default=True):
    """Safely convert a value to bool."""
    if val is None or val == "":
        return default
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("true", "1", "yes")


def assign_quality_tier(row: dict, cfg: dict) -> str:
    """
    Assign a quality tier to a genome based on CheckM2 and GUNC results.

    Tiers (in order of precedence):
      high_quality     : comp >= 90, contam < 5,  qscore >= 50, GUNC pass
      medium_quality   : comp >= 60, contam < 10, qscore >= 50, GUNC pass
      medium_chimeric  : meets medium_quality thresholds but GUNC flagged chimeric
      low_quality      : comp < 60 OR contam >= 10 OR qscore < 50
      low_chimeric     : meets low_quality AND GUNC flagged chimeric
    """
    comp = _to_float(row.get("completeness"), 0)
    contam = _to_float(row.get("contamination"), 100)
    qscore = comp - 5 * contam
    gunc_pass = _to_bool(row.get("pass_gunc"), True)

    is_high = (
        comp >= cfg["high_completeness"]
        and contam < cfg["high_contamination"]
        and qscore >= cfg["min_quality_score"]
    )
    is_medium = (
        comp >= cfg["medium_completeness"]
        and contam < cfg["medium_contamination"]
        and qscore >= cfg["min_quality_score"]
    )

    if is_high and gunc_pass:
        return "high_quality"
    elif is_medium and gunc_pass:
        return "medium_quality"
    elif is_medium and not gunc_pass:
        return "medium_chimeric"
    elif not gunc_pass:
        return "low_chimeric"
    else:
        return "low_quality"


_FILTER_TIERS = {
    "high_quality": {"high_quality"},
    "medium_quality": {"high_quality", "medium_quality"},
}


def merge_all_reports(
    stats_dir: str,
    checkm2_path: str | None,
    gunc_path: str | None,
    gtdbtk_path: str | None,
    output_combined: str,
    output_filtered: str,
    quality_cfg: dict,
) -> None:
    """
    Left-join all reports on mag_id, compute quality tiers,
    write combined and filtered reports.
    """
    # 1. Read all per-MAG genome_stats.tsv files
    stats_rows = []
    stats_path = Path(stats_dir)
    for mag_dir in sorted(stats_path.iterdir()):
        if mag_dir.is_dir():
            tsv = mag_dir / "genome_stats.tsv"
            if tsv.exists():
                stats_rows.extend(_read_tsv(tsv))

    data = {row["mag_id"]: dict(row) for row in stats_rows}

    # 2. Left-join CheckM2
    if checkm2_path:
        for row in _read_tsv(checkm2_path):
            mid = row.get("mag_id", "")
            if mid in data:
                data[mid].update(row)

    # 3. Left-join GUNC
    if gunc_path:
        for row in _read_tsv(gunc_path):
            mid = row.get("mag_id", "")
            if mid in data:
                data[mid].update(row)

    # 4. Left-join GTDB-Tk
    if gtdbtk_path:
        for row in _read_tsv(gtdbtk_path):
            mid = row.get("mag_id", "")
            if mid in data:
                data[mid].update(row)

    # 5. Compute derived columns and assign quality tiers
    for mid, row in data.items():
        comp = _to_float(row.get("completeness"), 0)
        contam = _to_float(row.get("contamination"), 0)
        row["quality_score"] = round(comp - 5 * contam, 2)
        row["quality_tier"] = assign_quality_tier(row, quality_cfg)

    # 6. Remap GUNC column name
    for row in data.values():
        if "taxonomic_level" in row and "gunc_taxonomic_level" not in row:
            row["gunc_taxonomic_level"] = row.pop("taxonomic_level")

    # 7. Define output column order
    columns = [
        "mag_id", "total_length_bp", "gc_percent", "contig_count", "n50_bp",
        "largest_contig_bp", "completeness", "contamination",
        "completeness_model_used", "quality_score", "css", "rrs",
        "contamination_portion", "gunc_taxonomic_level", "pass_gunc",
        "domain", "phylum", "class", "order", "family", "genus", "species",
        "classification", "fastani_reference", "fastani_ani", "fastani_af",
        "classification_method", "quality_tier",
    ]
    available_cols = set()
    for row in data.values():
        available_cols.update(row.keys())
    output_cols = [c for c in columns if c in available_cols or c in ("quality_score", "quality_tier")]

    # 8. Write combined report
    rows_sorted = sorted(data.values(), key=lambda r: r.get("mag_id", ""))
    _write_tsv(rows_sorted, output_cols, output_combined)

    # 9. Write filtered report
    filter_level = quality_cfg.get("default_filter", "medium_quality")
    passing_tiers = _FILTER_TIERS.get(filter_level, {"high_quality", "medium_quality"})
    filtered_rows = [r for r in rows_sorted if r.get("quality_tier") in passing_tiers]
    _write_tsv(filtered_rows, output_cols, output_filtered)


def _write_tsv(rows: list[dict], columns: list[str], output_path: str) -> None:
    """Write rows to a TSV with specified column order."""
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        f.write("\t".join(columns) + "\n")
        for row in rows:
            f.write("\t".join(str(row.get(c, "")) for c in columns) + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Merge QC reports and assign quality tiers")
    parser.add_argument("--stats-dir", required=True)
    parser.add_argument("--checkm2", default=None)
    parser.add_argument("--gunc", default=None)
    parser.add_argument("--gtdbtk", default=None)
    parser.add_argument("--output-combined", required=True)
    parser.add_argument("--output-filtered", required=True)
    parser.add_argument("--quality-config", default="{}")
    args = parser.parse_args()

    quality_cfg = ast.literal_eval(args.quality_config) if args.quality_config else {}

    merge_all_reports(
        stats_dir=args.stats_dir,
        checkm2_path=args.checkm2 if args.checkm2 else None,
        gunc_path=args.gunc if args.gunc else None,
        gtdbtk_path=args.gtdbtk if args.gtdbtk else None,
        output_combined=args.output_combined,
        output_filtered=args.output_filtered,
        quality_cfg=quality_cfg,
    )
