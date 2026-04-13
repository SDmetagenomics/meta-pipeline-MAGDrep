rule merge_reports:
    """Left-join genome_stats + checkm2 + gtdbtk on mag_id, assign quality tiers."""
    input:
        stats=expand(str(OUTDIR / "individual" / "{mag_id}" / "genome_stats.tsv"), mag_id=MAG_IDS),
        checkm2=str(OUTDIR / "checkm2_quality.tsv") if "checkm2" in STEPS else [],
        gtdbtk=str(OUTDIR / "gtdbtk_taxonomy.tsv") if "gtdbtk" in STEPS else [],
    output:
        combined=str(OUTDIR / "combined_report.tsv"),
        filtered=str(OUTDIR / "filtered_report.tsv"),
    threads: 1
    params:
        stats_dir=str(OUTDIR / "individual"),
    run:
        import json, subprocess
        cmd = [
            "python", "scripts/merge_reports.py",
            "--stats-dir", params.stats_dir,
            "--output-combined", output.combined,
            "--output-filtered", output.filtered,
        ]
        if "checkm2" in STEPS:
            cmd += ["--checkm2", str(OUTDIR / "checkm2_quality.tsv")]
        if "gtdbtk" in STEPS:
            cmd += ["--gtdbtk", str(OUTDIR / "gtdbtk_taxonomy.tsv")]
        quality_cfg = config.get("quality_filter", {})
        if quality_cfg:
            cmd += ["--quality-config", json.dumps(quality_cfg)]
        subprocess.run(cmd, check=True)
