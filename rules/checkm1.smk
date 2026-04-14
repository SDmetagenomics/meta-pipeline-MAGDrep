rule checkm1_setup_batch:
    """Create a directory of symlinks for one batch of genomes."""
    input:
        fastas=lambda wc: [mag_fasta(INPUT_DIR, mid) for mid in CHECKM1_BATCHES[wc.batch_id]]
    output:
        batch_dir=directory(str(OUTDIR / "checkm1" / "batches" / "{batch_id}" / "input"))
    threads: 1
    run:
        create_batch_dir(wildcards.batch_id, CHECKM1_BATCHES[wildcards.batch_id],
                         INPUT_DIR, output.batch_dir)


rule checkm1_batch:
    """Run CheckM1 lineage_wf on one batch.

    CheckM1 lives in a sibling conda env; run_checkm1.py uses `conda run`
    to invoke it. Raw output (bin stats, marker gene tables, trees) lands
    at results/checkm1/batches/{batch_id}/raw/ for downstream inspection.
    """
    input:
        batch_dir=str(OUTDIR / "checkm1" / "batches" / "{batch_id}" / "input")
    output:
        results=str(OUTDIR / "checkm1" / "batches" / "{batch_id}" / "checkm1_output.tsv")
    benchmark:
        str(OUTDIR / "benchmarks" / "checkm1" / "{batch_id}.tsv")
    threads: cfg_int("checkm1_threads", 8)
    resources:
        mem_mb=64000
    params:
        outdir=str(OUTDIR / "checkm1" / "batches" / "{batch_id}" / "raw"),
        db_path=config.get("checkm1_db_path", ""),
        pplacer_threads=cfg_int("checkm1_pplacer_threads", 4),
    shell:
        "python scripts/run_checkm1.py {input.batch_dir} {params.outdir} {output.results} {threads} {params.db_path} {params.pplacer_threads}"


rule checkm1_merge:
    """Concatenate all batch CheckM1 reports into one file."""
    input:
        expand(str(OUTDIR / "checkm1" / "batches" / "{batch_id}" / "checkm1_output.tsv"),
               batch_id=CHECKM1_BATCH_IDS)
    output:
        str(OUTDIR / "checkm1" / "checkm1_quality.tsv")
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
