# Running MAGDrep on an HPC cluster (SLURM)

The `slurm` profile at `config/profiles/slurm/config.yaml` submits each
Snakemake rule as a separate SLURM job via `snakemake-executor-plugin-slurm`.

## Prerequisites

- SLURM cluster with submission from the login node
- The `magdrep` conda env available on every compute node (either in a
  shared filesystem or via module system)
- Databases on a shared filesystem accessible to all nodes

## Usage

```bash
# Activate env on the login node
conda activate magdrep

# Run, tuning batch sizes to your cluster's sweet spot
meta-pipeline-MAGDrep qc \
    -i mags/ \
    -o results/ \
    --profile slurm \
    --config checkm2_batch_size=200 gtdbtk_batch_size=1000
```

## Profile highlights

- **CheckM2 batches of 200**: creates many fast jobs, maximizes cluster parallelism
- **GTDB-Tk batches of 1000**: amortizes the 85 GB database load per job
- **`cpus_per_task`** per rule matches the tool's `threads` request
- **`tmpdir: /tmp/$SLURM_JOB_ID`**: node-local scratch for GTDB-Tk intermediate files
  (falls back to GTDB-Tk's default if not set). `run_gtdbtk.py` auto-detects
  `$TMPDIR` and passes it as `--scratch_dir`.
- **Up to 500 concurrent jobs** (`jobs: 500`) — raise to your partition's cap.

## Tuning for your cluster

Edit `config/profiles/slurm/config.yaml` to match your node sizing. Key
numbers:

| Node size | Recommended `gtdbtk_batch` resources | pplacer_cpus |
|---|---|---|
| 128 GB, 16 CPU | mem=100000, cpus=16 | 1 |
| 256 GB, 32 CPU | mem=240000, cpus=32 | 3 |
| 512 GB, 64 CPU | mem=480000, cpus=64 | 6 |
| 1 TB, 96 CPU | mem=960000, cpus=96 | 12 |

The auto-resolution in the CLI picks `pplacer_cpus` from *login node*
memory, which may be wrong on HPC. Override explicitly:

```bash
meta-pipeline-MAGDrep qc ... --config gtdbtk.pplacer_cpus=6
```

## Database placement

GTDB-Tk reads ~85 GB of reference data. On Lustre/GPFS this can be slow
if many jobs load it concurrently. Options:

1. **Local to each node** (best if possible): copy databases to node-local
   SSD via a prolog script.
2. **Shared SSD tier**: place databases on a high-performance scratch tier
   rather than the slow scratch / home directory.
3. **Symlink from a cluster-wide reference location**: use the lab's shared
   database directory if one exists.

## Monitoring

```bash
# Live view
squeue -u $USER

# Per-job benchmarks after completion
meta-pipeline-MAGDrep benchmark results/
```

## Troubleshooting

- **GTDB-Tk OOM**: pplacer memory scales with tree size and genome count.
  Increase `mem_mb` for `gtdbtk_batch` or decrease `pplacer_cpus`.
- **Job pending for hours**: check `sinfo -p normal` for partition availability.
  Consider a different partition in `default-resources.slurm_partition`.
- **"Command not found: meta-pipeline-MAGDrep"**: the `magdrep` conda env is
  not activated on compute nodes. Add `source activate magdrep` to a prolog
  script or ensure conda init runs in SLURM's bash profile.
