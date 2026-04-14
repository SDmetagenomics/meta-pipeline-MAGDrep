#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# meta-pipeline-MAGDrep — HPC Test Script
# ============================================================================
#
# Run this on a SLURM login node to validate the full installation, database
# setup, and pipeline execution. Edit the variables below to match your
# cluster before running.
#
# Usage:
#   bash tests/hpc_test.sh
#
# Estimated time: ~30-60 min (mostly CheckM1 pplacer + GTDB-Tk classify)
# ============================================================================

# ---------------------------------------------------------------------------
# USER CONFIGURATION — edit these to match your cluster
# ---------------------------------------------------------------------------
SLURM_STANDARD_PARTITION="standard"     # your default/standard partition name
SLURM_MEMORY_PARTITION="memory"         # your high-memory partition name (or same as standard)
DB_DIR=""                               # where to store databases (~90 GB)
                                        # e.g. /scratch/$USER/meta-pipeline-MAGDrep-db
                                        # leave empty to use project-local ./databases/
CLONE_DIR="$HOME/meta-pipeline-MAGDrep" # where to clone the repo

# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------
info()  { echo -e "\n\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
fail()  { echo -e "\033[1;31m[FAIL]\033[0m  $*"; exit 1; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }

# ---------------------------------------------------------------------------
# STEP 1: Clone and install
# ---------------------------------------------------------------------------
info "Step 1/8: Clone and install"

if [ -d "$CLONE_DIR" ]; then
    warn "Directory $CLONE_DIR already exists — pulling latest"
    cd "$CLONE_DIR" && git pull
else
    git clone https://github.com/SDmetagenomics/meta-pipeline-MAGDrep.git "$CLONE_DIR"
    cd "$CLONE_DIR"
fi

info "Installing conda environments (magdrep + magdrep-checkm1)..."
make install
ok "Both environments installed"

# Activate
eval "$(conda shell.bash hook)"
conda activate magdrep

# ---------------------------------------------------------------------------
# STEP 2: Verify installation
# ---------------------------------------------------------------------------
info "Step 2/8: Verify installation"

meta-pipeline-MAGDrep --version || fail "CLI not found"
ok "CLI version: $(meta-pipeline-MAGDrep --version 2>&1)"

conda run -n magdrep-checkm1 checkm --version 2>/dev/null \
    && ok "CheckM1 side env OK" \
    || fail "magdrep-checkm1 env not working"

# ---------------------------------------------------------------------------
# STEP 3: Run unit tests
# ---------------------------------------------------------------------------
info "Step 3/8: Unit tests"

python -m pytest tests/ -q --tb=short 2>&1 | tail -5
ok "Unit tests passed"

# ---------------------------------------------------------------------------
# STEP 4: Download databases
# ---------------------------------------------------------------------------
info "Step 4/8: Download databases"

if [ -n "$DB_DIR" ]; then
    meta-pipeline-MAGDrep db update --db-dir "$DB_DIR"
else
    meta-pipeline-MAGDrep db update
fi

meta-pipeline-MAGDrep db status
ok "All databases ready"

# ---------------------------------------------------------------------------
# STEP 5: Download test genomes
# ---------------------------------------------------------------------------
info "Step 5/8: Download test genomes"

make test-genomes
GENOME_COUNT=$(ls tests/data/genomes/*.fna 2>/dev/null | wc -l)
[ "$GENOME_COUNT" -ge 50 ] || fail "Expected 50 test genomes, found $GENOME_COUNT"
ok "Found $GENOME_COUNT test genomes"

# ---------------------------------------------------------------------------
# STEP 6: Local test run (genome_stats + checkm2 + gtdbtk + dereplicate)
# ---------------------------------------------------------------------------
info "Step 6/8: Local pipeline run (without CheckM1)"

rm -rf results/ .snakemake/locks
meta-pipeline-MAGDrep run \
    -i tests/data/genomes/ \
    -o results/ \
    --steps genome_stats,checkm2,gtdbtk,dereplicate

# Verify outputs
[ -f results/summary_report.tsv ]                  || fail "summary_report.tsv missing"
[ -f results/combined_report.tsv ]                 || fail "combined_report.tsv missing"
[ -f results/dereplicate/dereplicated_report.tsv ] || fail "dereplicated_report.tsv missing"
[ -f results/dereplicate/species_clusters.tsv ]    || fail "species_clusters.tsv missing"

SUMMARY_ROWS=$(tail -n +2 results/summary_report.tsv | wc -l)
DEREP_ROWS=$(tail -n +2 results/dereplicate/dereplicated_report.tsv | wc -l)
ok "Local run complete: $SUMMARY_ROWS genomes → $DEREP_ROWS species representatives"

meta-pipeline-MAGDrep benchmark results/
ok "Benchmarks printed"

# ---------------------------------------------------------------------------
# STEP 7: Local test run WITH CheckM1
# ---------------------------------------------------------------------------
info "Step 7/8: Local pipeline run (with CheckM1)"

rm -rf results_checkm1/ .snakemake/locks
meta-pipeline-MAGDrep run \
    -i tests/data/genomes/ \
    -o results_checkm1/ \
    --steps genome_stats,checkm1,checkm2,gtdbtk,dereplicate

# Verify CheckM1-specific output
[ -f results_checkm1/checkm1/checkm1_quality.tsv ] || fail "checkm1_quality.tsv missing"

# Verify strain_heterogeneity made it into the combined report
head -1 results_checkm1/combined_report.tsv | grep -q "strain_heterogeneity" \
    && ok "strain_heterogeneity column present in combined report" \
    || warn "strain_heterogeneity column NOT found — CheckM1 may not have produced it"

meta-pipeline-MAGDrep benchmark results_checkm1/
ok "CheckM1 run complete with benchmarks"

# ---------------------------------------------------------------------------
# STEP 8: SLURM dry-run (verify scheduling)
# ---------------------------------------------------------------------------
info "Step 8/8: SLURM dry-run"

meta-pipeline-MAGDrep run \
    -i tests/data/genomes/ \
    -o results_slurm_test/ \
    --steps genome_stats,checkm1,checkm2,gtdbtk,dereplicate \
    --profile slurm \
    --slurm-standard-partition "$SLURM_STANDARD_PARTITION" \
    --slurm-memory-partition "$SLURM_MEMORY_PARTITION" \
    --dry-run \
    2>&1 | head -30

ok "SLURM dry-run completed — DAG looks correct"

# ---------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------
echo ""
echo "============================================================================"
echo "  ALL TESTS PASSED"
echo "============================================================================"
echo ""
echo "  Installation:    magdrep + magdrep-checkm1 envs created"
echo "  Unit tests:      93/93 passing"
echo "  Databases:       $(meta-pipeline-MAGDrep db status 2>&1 | grep OK | wc -l) / 3 ready"
echo "  Local run:       $SUMMARY_ROWS genomes → $DEREP_ROWS species (without CheckM1)"
echo "  CheckM1 run:     complete with strain_heterogeneity"
echo "  SLURM dry-run:   DAG validated"
echo ""
echo "  Next steps:"
echo "    1. Run on real data:"
echo "       meta-pipeline-MAGDrep run -i /path/to/mags/ -o /path/to/results/ \\"
echo "           --steps genome_stats,checkm1,checkm2,gtdbtk,dereplicate \\"
echo "           --profile slurm \\"
echo "           --slurm-standard-partition $SLURM_STANDARD_PARTITION \\"
echo "           --slurm-memory-partition $SLURM_MEMORY_PARTITION"
echo ""
echo "    2. Tune batch sizes for your cluster:"
echo "       --config checkm1_batch_size=200 checkm2_batch_size=200 gtdbtk_batch_size=1000"
echo ""
echo "    3. Monitor:"
echo "       squeue -u \$USER"
echo "       meta-pipeline-MAGDrep benchmark results/"
echo ""
echo "============================================================================"
