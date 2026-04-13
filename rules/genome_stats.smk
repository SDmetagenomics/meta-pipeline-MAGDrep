rule genome_stats:
    input:
        fasta=lambda wc: mag_fasta(INPUT_DIR, wc.mag_id)
    output:
        stats=str(OUTDIR / "individual" / "{mag_id}" / "genome_stats.tsv")
    benchmark:
        str(OUTDIR / "benchmarks" / "genome_stats" / "{mag_id}.tsv")
    threads: 1
    group: "fast_{mag_id}"
    shell:
        "python scripts/genome_stats.py {input.fasta} {output.stats}"
