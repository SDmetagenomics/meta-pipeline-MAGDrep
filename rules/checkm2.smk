rule checkm2_setup_batch:
    """Create a directory of symlinks for one batch of genomes."""
    input:
        fastas=lambda wc: [mag_fasta(INPUT_DIR, mid) for mid in BATCHES[wc.batch_id]]
    output:
        batch_dir=directory(str(OUTDIR / "batches" / "checkm2" / "{batch_id}" / "input"))
    threads: 1
    run:
        create_batch_dir(wildcards.batch_id, BATCHES[wildcards.batch_id],
                         INPUT_DIR, output.batch_dir)


rule checkm2_batch:
    """Run CheckM2 predict on one batch."""
    input:
        batch_dir=str(OUTDIR / "batches" / "checkm2" / "{batch_id}" / "input")
    output:
        results=str(OUTDIR / "batches" / "checkm2" / "{batch_id}" / "quality_report.tsv")
    benchmark:
        str(OUTDIR / "benchmarks" / "checkm2" / "{batch_id}.tsv")
    threads: 16
    params:
        outdir=str(OUTDIR / "batches" / "checkm2" / "{batch_id}" / "output"),
        db_path=config.get("checkm2_db_path", ""),
    shell:
        "python scripts/run_checkm2.py {input.batch_dir} {params.outdir} {output.results} {threads} {params.db_path}"


rule checkm2_merge:
    """Concatenate all batch quality reports into one file."""
    input:
        expand(str(OUTDIR / "batches" / "checkm2" / "{batch_id}" / "quality_report.tsv"),
               batch_id=BATCH_IDS)
    output:
        str(OUTDIR / "checkm2_quality.tsv")
    threads: 1
    run:
        header = None
        with open(output[0], "w") as out:
            for tsv in input:
                with open(tsv) as f:
                    h = f.readline()
                    if header is None:
                        header = h
                        out.write(header)
                    for line in f:
                        if line.strip():
                            out.write(line)
