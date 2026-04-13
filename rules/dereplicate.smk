rule skani_triangle:
    """Compute all-vs-all ANI for filtered genomes using skani triangle."""
    input:
        filtered_report=str(OUTDIR / "filtered_report.tsv")
    output:
        edge_list=str(OUTDIR / "dereplicate" / "skani_edges.tsv"),
        genome_list=str(OUTDIR / "dereplicate" / "genome_list.txt"),
    benchmark:
        str(OUTDIR / "benchmarks" / "skani_triangle.tsv")
    threads: 64
    resources:
        mem_mb=64000
    params:
        input_dir=str(INPUT_DIR)
    shell:
        "python scripts/dereplicate.py triangle "
        "--filtered-report {input.filtered_report} "
        "--input-dir {params.input_dir} "
        "--output-edges {output.edge_list} "
        "--output-genome-list {output.genome_list} "
        "--threads {threads}"


rule dereplicate_cluster:
    """Cluster genomes at species level and select representatives."""
    input:
        edge_list=str(OUTDIR / "dereplicate" / "skani_edges.tsv"),
        filtered_report=str(OUTDIR / "filtered_report.tsv"),
    output:
        clusters=str(OUTDIR / "dereplicate" / "species_clusters.tsv"),
        derep_report=str(OUTDIR / "dereplicate" / "dereplicated_report.tsv"),
    benchmark:
        str(OUTDIR / "benchmarks" / "dereplicate_cluster.tsv")
    threads: 1
    params:
        derep_cfg=config.get("dereplicate", {}),
    run:
        import json, subprocess
        cfg = params.derep_cfg
        # Coerce values to float — Snakemake's config passing can stringify them.
        weights = {k: float(v) for k, v in cfg.get("score_weights", {}).items()}
        cmd = [
            "python", "scripts/dereplicate.py", "cluster",
            "--edge-list", input.edge_list,
            "--filtered-report", input.filtered_report,
            "--output-clusters", output.clusters,
            "--output-derep-report", output.derep_report,
            "--ani-threshold", str(float(cfg.get("ani_threshold", 95.0))),
            "--min-af", str(float(cfg.get("min_af", 10.0))),
            "--score-weights", json.dumps(weights),
        ]
        subprocess.run(cmd, check=True)
