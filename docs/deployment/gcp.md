# Running MAGDrep on Google Cloud (Batch)

The `gcp` profile at `config/profiles/gcp/config.yaml` runs each Snakemake
rule as a Google Cloud Batch job. This lets you scale to thousands of
MAGs by parallelizing CheckM2/GTDB-Tk batches across many VMs with no
shared filesystem required.

## Cost sketch

For 10,000 MAGs (rough, us-central1 pricing as of 2026):

| Stage | Machines | Total | Notes |
|---|---|---|---|
| CheckM2 (50×200-MAG batches) | 50× n2-standard-16 preemptible | ~$20 | ~3h each, preemptible |
| GTDB-Tk (10×1000-MAG batches) | 10× n2-highmem-32 | ~$150 | ~8h each, standard (preemption costly) |
| skani triangle | 1× n2-standard-32 | ~$3 | ~30 min |
| Orchestration + small rules | various e2 | ~$2 | |
| **Total** | | **~$175** | |

Preemptibles cut CheckM2 by ~70% but require idempotent jobs (we are).
GTDB-Tk's pplacer step is hard to restart mid-genome, so keep it on
standard VMs.

## Prerequisites

1. GCP project with the **Batch API** and **Cloud Storage API** enabled.
2. `gcloud` CLI authenticated:
   ```bash
   gcloud auth application-default login
   gcloud config set project YOUR_PROJECT_ID
   ```
3. A service account with roles `roles/batch.jobsEditor` and
   `roles/storage.objectAdmin` on your bucket.
4. Python plugins installed locally:
   ```bash
   pip install snakemake-executor-plugin-googlebatch \
               snakemake-storage-plugin-gcs
   ```

## One-time setup

### 1. Create a GCS bucket for pipeline I/O

```bash
gsutil mb -l us-central1 gs://my-magdrep-bucket
```

### 2. Put your databases on GCS (or a persistent disk)

**Option A — copy to GCS once, mount at runtime with gcsfuse:**

```bash
gsutil -m cp -r databases/checkm2 gs://my-magdrep-bucket/databases/checkm2
gsutil -m cp -r databases/gtdbtk gs://my-magdrep-bucket/databases/gtdbtk
```

Then add a container startup script that runs `gcsfuse` to mount the bucket
at `/databases/` inside each job (see the Dockerfile section below).

**Option B — bake databases into a custom VM image (faster boot, no mount):**

Snapshot a disk containing the databases and reference it in the profile:

```yaml
googlebatch-boot-disk-image: projects/YOUR_PROJECT/global/images/magdrep-dbs-v1
```

**Option C — mount a persistent-disk snapshot read-only on every job:**

Each job attaches the disk at `/databases/`. Scales poorly beyond a few
dozen concurrent jobs because GCE persistent-disk snapshots have
attachment limits.

For most workflows **Option B** is fastest and simplest.

### 3. Build a container image with the magdrep env

`Dockerfile`:

```dockerfile
FROM mambaorg/micromamba:1.5.8
COPY environment.yml /tmp/environment.yml
RUN micromamba install -y -n base -f /tmp/environment.yml && \
    micromamba clean --all --yes
COPY . /opt/magdrep
RUN cd /opt/magdrep && pip install -e .
# Optional: install gcsfuse if using Option A
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcsfuse && rm -rf /var/lib/apt/lists/*
```

Build and push:

```bash
docker build -t gcr.io/YOUR_PROJECT/magdrep:v0.1 .
docker push gcr.io/YOUR_PROJECT/magdrep:v0.1
```

### 4. Export environment variables

```bash
export GOOGLE_BATCH_PROJECT=YOUR_PROJECT_ID
export GOOGLE_BATCH_REGION=us-central1
export GOOGLE_BATCH_BUCKET=my-magdrep-bucket
export MAGDREP_CONTAINER=gcr.io/YOUR_PROJECT/magdrep:v0.1
```

## Running

```bash
# Upload MAGs to GCS
gsutil -m cp mags/*.fna gs://my-magdrep-bucket/mags/

# Run pipeline — inputs and outputs on GCS
meta-pipeline-MAGDrep run \
    -i gs://my-magdrep-bucket/mags/ \
    -o gs://my-magdrep-bucket/runs/2026-04/ \
    --profile gcp \
    --config checkm2_batch_size=200 gtdbtk_batch_size=1000

# Monitor jobs
gcloud batch jobs list --location=us-central1
```

## Tuning

**Batch sizes.** CheckM2 with `batch_size=200` creates many small jobs → more
parallelism, more preemptibility. GTDB-Tk with `batch_size=1000` amortizes
the ~85 GB database load.

**Machine types.** The profile defaults are conservative starting points.
Check `benchmarks/` output from your first run and adjust. For example, if
GTDB-Tk `gtdbtk_batch` is hitting the memory ceiling, bump to
`n2-highmem-64` (432 GB).

**Quota.** Default Batch quotas in a fresh project are small. Request
increases for:
- CPUs in your region (default 72 → request 1000+)
- Disk space per region (default 5 TB → request 20 TB+)

**Region.** `us-central1` and `us-east1` have the most Batch capacity and
the lowest prices. `europe-west4` and `asia-east1` are fine alternatives.

## Troubleshooting

- **Jobs stuck in "SCHEDULED"**: quota hit. Check `gcloud compute
  regions describe us-central1` for current usage.
- **pplacer OOM**: memory per pplacer CPU too low. Raise
  `googlebatch_memory` for `gtdbtk_batch` or reduce `pplacer_cpus`.
- **Preempted CheckM2 job fails permanently**: Snakemake's default retry
  is 0. Add `--retries 3` or set `retries: 3` in the profile.
- **Container image not found**: set `$MAGDREP_CONTAINER` before
  invoking, or edit the profile to hardcode the URI.
