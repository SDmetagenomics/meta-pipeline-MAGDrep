from pathlib import Path

include: "rules/common.smk"

# --- Configuration ---
INPUT_DIR = Path(config.get("input_dir", "mags"))
OUTDIR = Path(config.get("outdir", "results"))
BATCH_SIZE = cfg_int("batch_size", 1000)
CHECKM2_BATCH_SIZE = cfg_int("checkm2_batch_size", BATCH_SIZE)
GTDBTK_BATCH_SIZE = cfg_int("gtdbtk_batch_size", BATCH_SIZE)
STEPS = set(config.get("steps", []))

# Discover MAG IDs from input directory
MAG_IDS = discover_mag_ids(INPUT_DIR)
if not MAG_IDS:
    raise ValueError(f"No FASTA files found in input directory: {INPUT_DIR}")

# Per-tool batch assignments. CheckM2 benefits from smaller batches (more
# parallelism on cluster/cloud); GTDB-Tk benefits from larger batches
# (amortizes DB load time).
CHECKM2_BATCHES = make_batches(MAG_IDS, CHECKM2_BATCH_SIZE)
CHECKM2_BATCH_IDS = list(CHECKM2_BATCHES.keys())
GTDBTK_BATCHES = make_batches(MAG_IDS, GTDBTK_BATCH_SIZE)
GTDBTK_BATCH_IDS = list(GTDBTK_BATCHES.keys())

# Always include genome_stats and aggregate
include: "rules/genome_stats.smk"
include: "rules/aggregate.smk"

if "checkm2" in STEPS:
    include: "rules/checkm2.smk"

if "gtdbtk" in STEPS:
    include: "rules/gtdbtk.smk"

if "dereplicate" in STEPS:
    include: "rules/dereplicate.smk"


def all_outputs():
    """Build the list of expected final outputs based on selected steps."""
    outputs = [
        str(OUTDIR / "combined_report.tsv"),
        str(OUTDIR / "filtered_report.tsv"),
        str(OUTDIR / "summary_report.tsv"),
    ]
    if "dereplicate" in STEPS:
        outputs.append(str(OUTDIR / "dereplicate" / "dereplicated_report.tsv"))
        outputs.append(str(OUTDIR / "dereplicate" / "species_clusters.tsv"))
    return outputs


rule all:
    input:
        all_outputs()
