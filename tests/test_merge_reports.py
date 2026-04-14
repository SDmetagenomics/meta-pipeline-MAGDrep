import pytest
from scripts.merge_reports import assign_quality_tier, merge_all_reports

DEFAULT_QUALITY_CFG = {
    "high_completeness": 90.0,
    "high_contamination": 5.0,
    "medium_completeness": 60.0,
    "medium_contamination": 10.0,
    "min_quality_score": 50.0,
    "default_filter": "medium_quality",
}


def test_assign_high_quality():
    row = {"completeness": 95.0, "contamination": 1.0}
    assert assign_quality_tier(row, DEFAULT_QUALITY_CFG) == "high_quality"


def test_assign_medium_quality():
    row = {"completeness": 75.0, "contamination": 3.0}
    assert assign_quality_tier(row, DEFAULT_QUALITY_CFG) == "medium_quality"


def test_assign_low_quality():
    row = {"completeness": 40.0, "contamination": 2.0}
    assert assign_quality_tier(row, DEFAULT_QUALITY_CFG) == "low_quality"


def test_assign_high_contamination_is_low():
    row = {"completeness": 95.0, "contamination": 12.0}
    assert assign_quality_tier(row, DEFAULT_QUALITY_CFG) == "low_quality"


def test_assign_quality_score_below_threshold():
    """Completeness 65, contamination 5 -> qscore=40 < 50 -> low_quality."""
    row = {"completeness": 65.0, "contamination": 5.0}
    assert assign_quality_tier(row, DEFAULT_QUALITY_CFG) == "low_quality"


def test_merge_adds_strain_heterogeneity_from_checkm1(tmp_path):
    """CheckM1 strain_heterogeneity always lands in the combined report."""
    indiv = tmp_path / "individual"
    (indiv / "mag_001").mkdir(parents=True)
    (indiv / "mag_001" / "genome_stats.tsv").write_text(
        "mag_id\ttotal_length_bp\tgc_percent\tcontig_count\tn50_bp\tlargest_contig_bp\n"
        "mag_001\t1000000\t45.0\t10\t200000\t300000\n"
    )
    (tmp_path / "checkm1_quality.tsv").write_text(
        "mag_id\tcheckm1_marker_lineage\tcompleteness\tcontamination\tstrain_heterogeneity\n"
        "mag_001\tp__Bacteria\t80.0\t3.0\t50.0\n"
    )
    (tmp_path / "checkm2_quality.tsv").write_text(
        "mag_id\tcompleteness\tcontamination\tcompleteness_model_used\n"
        "mag_001\t85.0\t1.5\tNeural Network\n"
    )

    combined = tmp_path / "combined.tsv"
    filtered = tmp_path / "filtered.tsv"

    merge_all_reports(
        stats_dir=str(indiv),
        checkm1_path=str(tmp_path / "checkm1_quality.tsv"),
        checkm2_path=str(tmp_path / "checkm2_quality.tsv"),
        gtdbtk_path=None,
        output_combined=str(combined),
        output_filtered=str(filtered),
        quality_cfg=DEFAULT_QUALITY_CFG,
    )

    header, row = combined.read_text().strip().split("\n")
    cols = header.split("\t")
    vals = dict(zip(cols, row.split("\t")))
    # CheckM2 wins on canonical completeness/contamination
    assert vals["completeness"] == "85.0"
    assert vals["contamination"] == "1.5"
    # CheckM1 values preserved side-by-side
    assert vals["checkm1_completeness"] == "80.0"
    assert vals["checkm1_contamination"] == "3.0"
    # Strain het present
    assert vals["strain_heterogeneity"] == "50.0"


def test_merge_checkm1_only_promotes_completeness(tmp_path):
    """If only CheckM1 ran, its values become the canonical completeness/contamination."""
    indiv = tmp_path / "individual"
    (indiv / "mag_001").mkdir(parents=True)
    (indiv / "mag_001" / "genome_stats.tsv").write_text(
        "mag_id\ttotal_length_bp\tgc_percent\tcontig_count\tn50_bp\tlargest_contig_bp\n"
        "mag_001\t1000000\t45.0\t10\t200000\t300000\n"
    )
    (tmp_path / "checkm1_quality.tsv").write_text(
        "mag_id\tcheckm1_marker_lineage\tcompleteness\tcontamination\tstrain_heterogeneity\n"
        "mag_001\tp__Bacteria\t80.0\t3.0\t50.0\n"
    )

    combined = tmp_path / "combined.tsv"
    filtered = tmp_path / "filtered.tsv"

    merge_all_reports(
        stats_dir=str(indiv),
        checkm1_path=str(tmp_path / "checkm1_quality.tsv"),
        checkm2_path=None,
        gtdbtk_path=None,
        output_combined=str(combined),
        output_filtered=str(filtered),
        quality_cfg=DEFAULT_QUALITY_CFG,
    )

    header, row = combined.read_text().strip().split("\n")
    cols = header.split("\t")
    vals = dict(zip(cols, row.split("\t")))
    assert vals["completeness"] == "80.0"
    assert vals["contamination"] == "3.0"
    assert vals["strain_heterogeneity"] == "50.0"


def test_merge_all_reports(tmp_path):
    """Test full merge pipeline with mock data."""
    indiv = tmp_path / "individual"
    for mag_id in ["mag_001", "mag_002"]:
        mag_dir = indiv / mag_id
        mag_dir.mkdir(parents=True)
        (mag_dir / "genome_stats.tsv").write_text(
            "mag_id\ttotal_length_bp\tgc_percent\tcontig_count\tn50_bp\tlargest_contig_bp\n"
            f"{mag_id}\t1000000\t45.0\t10\t200000\t300000\n"
        )

    (tmp_path / "checkm2_quality.tsv").write_text(
        "mag_id\tcompleteness\tcontamination\tcompleteness_model_used\ttranslation_table_used\n"
        "mag_001\t95.5\t1.2\tNeural Network\t11\n"
        "mag_002\t55.0\t8.0\tNeural Network\t11\n"
    )

    combined = tmp_path / "combined_report.tsv"
    filtered = tmp_path / "filtered_report.tsv"

    merge_all_reports(
        stats_dir=str(indiv),
        checkm2_path=str(tmp_path / "checkm2_quality.tsv"),
        gtdbtk_path=None,
        output_combined=str(combined),
        output_filtered=str(filtered),
        quality_cfg=DEFAULT_QUALITY_CFG,
    )

    lines = combined.read_text().strip().split("\n")
    assert len(lines) == 3  # header + 2 rows
    assert "quality_tier" in lines[0]

    filt_lines = filtered.read_text().strip().split("\n")
    assert len(filt_lines) == 2  # header + 1 row (only mag_001)
    assert "mag_001" in filt_lines[1]
