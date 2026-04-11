from pathlib import Path


def discover_mag_ids(input_dir):
    """Return sorted list of MAG IDs from FASTA files in input_dir."""
    patterns = ["*.fasta", "*.fa", "*.fna", "*.fasta.gz", "*.fa.gz", "*.fna.gz"]
    paths = []
    for pattern in patterns:
        paths.extend(Path(input_dir).glob(pattern))
    ids = []
    for p in paths:
        name = p.name
        for suffix in (".fasta.gz", ".fa.gz", ".fna.gz", ".fasta", ".fna", ".fa"):
            if name.endswith(suffix):
                ids.append(name[: -len(suffix)])
                break
    return sorted(set(ids))


def mag_fasta(input_dir, mag_id):
    """Return path to FASTA file for a given MAG ID."""
    for suffix in (".fna", ".fasta", ".fa", ".fna.gz", ".fasta.gz", ".fa.gz"):
        candidate = Path(input_dir) / f"{mag_id}{suffix}"
        if candidate.exists():
            return str(candidate)
    raise FileNotFoundError(f"No FASTA file found for MAG ID: {mag_id}")


def make_batches(mag_ids, batch_size):
    """
    Split MAG IDs into numbered batches.
    Returns dict mapping batch_id strings to lists of MAG IDs.
    E.g. 2500 MAGs with batch_size=1000 ->
      {"batch_000": [...1000...], "batch_001": [...1000...], "batch_002": [...500...]}
    """
    batches = {}
    num_batches = max(1, (len(mag_ids) + batch_size - 1) // batch_size)
    width = max(3, len(str(num_batches - 1)))
    for i in range(0, len(mag_ids), batch_size):
        batch_id = f"batch_{str(i // batch_size).zfill(width)}"
        batches[batch_id] = mag_ids[i : i + batch_size]
    return batches


def create_batch_dir(batch_id, mag_ids, input_dir, batch_dir):
    """
    Create a directory of symlinks for a batch.
    For each MAG ID, symlink the original FASTA into batch_dir/.
    """
    import os
    batch_path = Path(batch_dir)
    batch_path.mkdir(parents=True, exist_ok=True)
    for mid in mag_ids:
        src = Path(mag_fasta(input_dir, mid))
        dst = batch_path / src.name
        if not dst.exists():
            os.symlink(src.resolve(), dst)


# Wildcard constraints
wildcard_constraints:
    mag_id="[A-Za-z0-9_.\\-]+",
    batch_id="batch_\\d+",
