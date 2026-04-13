rule gtdbtk_setup_batch:
    """Create a directory of symlinks for one batch of genomes.

    Symlinks are prefixed with 'MAG_' to avoid collisions with GTDB-Tk
    reference genome IDs. The prefix is stripped when parsing output.
    """
    input:
        fastas=lambda wc: [mag_fasta(INPUT_DIR, mid) for mid in BATCHES[wc.batch_id]]
    output:
        batch_dir=directory(str(OUTDIR / "batches" / "gtdbtk" / "{batch_id}" / "input"))
    threads: 1
    run:
        import os
        batch_path = Path(output.batch_dir)
        batch_path.mkdir(parents=True, exist_ok=True)
        for mid in BATCHES[wildcards.batch_id]:
            src = Path(mag_fasta(INPUT_DIR, mid))
            dst = batch_path / f"MAG_{src.name}"
            if not dst.exists():
                os.symlink(src.resolve(), dst)


rule gtdbtk_batch:
    """Run GTDB-Tk classify_wf on one batch."""
    input:
        batch_dir=str(OUTDIR / "batches" / "gtdbtk" / "{batch_id}" / "input")
    output:
        results=str(OUTDIR / "batches" / "gtdbtk" / "{batch_id}" / "gtdbtk_output.tsv")
    benchmark:
        str(OUTDIR / "benchmarks" / "gtdbtk" / "{batch_id}.tsv")
    threads: config.get("gtdbtk", {}).get("threads", 16)
    resources:
        mem_mb=120000
    params:
        outdir=str(OUTDIR / "batches" / "gtdbtk" / "{batch_id}" / "output"),
        pplacer_cpus=config.get("gtdbtk", {}).get("pplacer_cpus", 1),
        skip_ani=config.get("gtdbtk", {}).get("skip_ani_screen", False),
        db_path=config.get("gtdbtk_db_path", ""),
    shell:
        "python scripts/run_gtdbtk.py {input.batch_dir} {params.outdir} {output.results} "
        "{threads} {params.pplacer_cpus} {params.skip_ani} {params.db_path}"


rule gtdbtk_merge:
    """Concatenate all batch GTDB-Tk reports into one file."""
    input:
        expand(str(OUTDIR / "batches" / "gtdbtk" / "{batch_id}" / "gtdbtk_output.tsv"),
               batch_id=BATCH_IDS)
    output:
        str(OUTDIR / "gtdbtk_taxonomy.tsv")
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
