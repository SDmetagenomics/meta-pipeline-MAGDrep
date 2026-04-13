"""MAG input resolution — directory or path-list file.

Used by both the Snakefile (via rules/common.smk) and the dereplicate.py
script so the same logic governs every part of the pipeline.
"""
from __future__ import annotations
from pathlib import Path

FASTA_SUFFIXES = (".fasta.gz", ".fa.gz", ".fna.gz", ".fasta", ".fna", ".fa")


def mag_id_from_path(path) -> str:
    """Extract a MAG ID by stripping any recognized FASTA suffix."""
    name = Path(path).name
    for suffix in FASTA_SUFFIXES:
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def build_mag_path_map(input_source) -> dict[str, Path]:
    """Return {mag_id: absolute Path} from a directory or a path-list file.

    - If *input_source* is a directory, every FASTA in it becomes a MAG.
    - If *input_source* is a regular file, each non-empty, non-comment line
      is treated as a path to a FASTA file. Allows MAGs scattered across
      multiple directories or a hand-picked subset.

    Raises ValueError if any line in a list file references a missing file
    or two MAGs would share the same ID.
    """
    p = Path(input_source)
    paths: list[Path] = []

    if p.is_dir():
        patterns = ["*.fasta", "*.fa", "*.fna", "*.fasta.gz", "*.fa.gz", "*.fna.gz"]
        for pattern in patterns:
            paths.extend(p.glob(pattern))
    elif p.is_file():
        with open(p) as f:
            for lineno, raw in enumerate(f, 1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                fpath = Path(line).expanduser()
                if not fpath.is_absolute():
                    fpath = (p.parent / fpath).resolve()
                if not fpath.exists():
                    raise ValueError(
                        f"{p}:{lineno} — FASTA path does not exist: {fpath}"
                    )
                paths.append(fpath)
    else:
        raise ValueError(
            f"Input must be a directory or a text file with FASTA paths: {input_source}"
        )

    id_to_path: dict[str, Path] = {}
    for path in paths:
        mid = mag_id_from_path(path)
        if mid in id_to_path and id_to_path[mid].resolve() != path.resolve():
            raise ValueError(
                f"Duplicate MAG ID '{mid}' from {id_to_path[mid]} and {path}. "
                f"Rename one of the files to avoid the collision."
            )
        id_to_path[mid] = path.resolve()

    return id_to_path
