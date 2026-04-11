rule skani_triangle:
    """Compute all-vs-all ANI for filtered genomes using skani triangle."""
    input:
        filtered_report=str(OUTDIR / "filtered_report.tsv")
    output:
        edge_list=str(OUTDIR / "dereplicate" / "skani_edges.tsv"),
        genome_list=str(OUTDIR / "dereplicate" / "genome_list.txt"),
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
        clusters=str(OUTDIR / "species_clusters.tsv"),
        derep_report=str(OUTDIR / "dereplicated_report.tsv"),
    threads: 1
    params:
        derep_cfg=config.get("dereplicate", {}),
        quality_cfg=config.get("quality_filter", {}),
    shell:
        "python scripts/dereplicate.py cluster "
        "--edge-list {input.edge_list} "
        "--filtered-report {input.filtered_report} "
        "--output-clusters {output.clusters} "
        "--output-derep-report {output.derep_report} "
        "--ani-threshold {params.derep_cfg[ani_threshold]} "
        "--min-af {params.derep_cfg[min_af]} "
        "--score-weights '{params.derep_cfg[score_weights]}'"
