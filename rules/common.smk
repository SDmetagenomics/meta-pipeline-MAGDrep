from pathlib import Path


def _coerce_int(val, default):
    if val is None or val == "None" or val == "" or val == "auto":
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def cfg_int(key, default):
    """Return config[key] as int, tolerating 'auto'/'None'/strings/missing."""
    return _coerce_int(config.get(key, default), default)


def cfg_nested_int(section, key, default):
    """Return config[section][key] as int, tolerating missing sections."""
    sect = config.get(section) or {}
    if not isinstance(sect, dict):
        return default
    return _coerce_int(sect.get(key, default), default)


from meta_pipeline_magdrep.inputs import build_mag_path_map

_MAG_PATH_CACHE: dict = {}


def _cached_map(input_source):
    key = str(Path(input_source).resolve())
    if key not in _MAG_PATH_CACHE:
        _MAG_PATH_CACHE[key] = build_mag_path_map(input_source)
    return _MAG_PATH_CACHE[key]


def discover_mag_ids(input_source):
    """Return sorted list of MAG IDs from a directory or path-list file."""
    return sorted(_cached_map(input_source).keys())


def mag_fasta(input_source, mag_id):
    """Return absolute path to FASTA file for a given MAG ID."""
    paths = _cached_map(input_source)
    if mag_id not in paths:
        raise FileNotFoundError(f"No FASTA file found for MAG ID: {mag_id}")
    return str(paths[mag_id])


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
