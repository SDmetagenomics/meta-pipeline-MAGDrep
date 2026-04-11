rule merge_reports:
    """Left-join genome_stats + checkm2 + gunc + gtdbtk on mag_id, assign quality tiers."""
    input:
        stats=expand(str(OUTDIR / "individual" / "{mag_id}" / "genome_stats.tsv"), mag_id=MAG_IDS),
        checkm2=str(OUTDIR / "checkm2_quality.tsv") if "checkm2" in STEPS else [],
        gunc=str(OUTDIR / "gunc_chimerism.tsv") if "gunc" in STEPS else [],
        gtdbtk=str(OUTDIR / "gtdbtk_taxonomy.tsv") if "gtdbtk" in STEPS else [],
    output:
        combined=str(OUTDIR / "combined_report.tsv"),
        filtered=str(OUTDIR / "filtered_report.tsv"),
    threads: 1
    params:
        stats_dir=str(OUTDIR / "individual"),
        checkm2=str(OUTDIR / "checkm2_quality.tsv") if "checkm2" in STEPS else "",
        gunc=str(OUTDIR / "gunc_chimerism.tsv") if "gunc" in STEPS else "",
        gtdbtk=str(OUTDIR / "gtdbtk_taxonomy.tsv") if "gtdbtk" in STEPS else "",
        quality_cfg=config.get("quality_filter", {}),
    shell:
        "python scripts/merge_reports.py "
        "--stats-dir {params.stats_dir} "
        "--checkm2 {params.checkm2} "
        "--gunc {params.gunc} "
        "--gtdbtk {params.gtdbtk} "
        "--output-combined {output.combined} "
        "--output-filtered {output.filtered} "
        "--quality-config '{params.quality_cfg}'"
