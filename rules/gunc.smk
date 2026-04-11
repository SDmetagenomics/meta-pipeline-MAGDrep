rule gunc_setup_batch:
    """Create a directory of symlinks for one batch of genomes."""
    input:
        fastas=lambda wc: [mag_fasta(INPUT_DIR, mid) for mid in BATCHES[wc.batch_id]]
    output:
        batch_dir=directory(str(OUTDIR / "batches" / "gunc" / "{batch_id}" / "input"))
    threads: 1
    run:
        create_batch_dir(wildcards.batch_id, BATCHES[wildcards.batch_id],
                         INPUT_DIR, output.batch_dir)


rule gunc_batch:
    """Run GUNC on one batch."""
    input:
        batch_dir=str(OUTDIR / "batches" / "gunc" / "{batch_id}" / "input")
    output:
        results=str(OUTDIR / "batches" / "gunc" / "{batch_id}" / "gunc_output.tsv")
    threads: 16
    params:
        outdir=str(OUTDIR / "batches" / "gunc" / "{batch_id}" / "output"),
        db_path=config.get("gunc_db_path") or "",
        db_type=config.get("gunc", {}).get("db_type", "gtdb_214"),
    shell:
        "python scripts/run_gunc.py {input.batch_dir} {params.outdir} {output.results} {threads} {params.db_type}"


rule gunc_merge:
    """Concatenate all batch GUNC reports into one file."""
    input:
        expand(str(OUTDIR / "batches" / "gunc" / "{batch_id}" / "gunc_output.tsv"),
               batch_id=BATCH_IDS)
    output:
        str(OUTDIR / "gunc_chimerism.tsv")
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
