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


def _glob_fastas(directory: Path) -> list[Path]:
    """Return all FASTA files in *directory* (non-recursive)."""
    patterns = ["*.fasta", "*.fa", "*.fna", "*.fasta.gz", "*.fa.gz", "*.fna.gz"]
    out: list[Path] = []
    for pattern in patterns:
        out.extend(directory.glob(pattern))
    return out


def build_mag_path_map(
    input_source,
    allow_duplicates: bool = False,
) -> dict[str, Path]:
    """Return {mag_id: absolute Path} from a directory or a list of directories.

    - If *input_source* is a directory, every FASTA in it becomes a MAG.
    - If *input_source* is a regular file, each non-empty, non-comment line
      is treated as a directory path whose FASTAs all become MAGs.
      This lets you run the pipeline on MAGs scattered across many
      sample-specific bin directories without symlinking them into one
      place first.

    With the default ``allow_duplicates=False``, any two FASTAs that
    would resolve to the same MAG ID (filename stem) raise a ValueError.
    Pass ``allow_duplicates=True`` when the caller intends to disambiguate
    the colliding names itself (e.g. the --rename pass-through).
    """
    p = Path(input_source)
    paths: list[Path] = []

    if p.is_dir():
        paths.extend(_glob_fastas(p))
    elif p.is_file():
        with open(p) as f:
            for lineno, raw in enumerate(f, 1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                dpath = Path(line).expanduser()
                if not dpath.is_absolute():
                    dpath = (p.parent / dpath).resolve()
                if not dpath.exists():
                    raise ValueError(
                        f"{p}:{lineno} — directory does not exist: {dpath}"
                    )
                if not dpath.is_dir():
                    raise ValueError(
                        f"{p}:{lineno} — expected a directory of FASTA files, got a file: {dpath}"
                    )
                dir_fastas = _glob_fastas(dpath)
                if not dir_fastas:
                    raise ValueError(
                        f"{p}:{lineno} — no FASTA files found in {dpath}"
                    )
                paths.extend(dir_fastas)
    else:
        raise ValueError(
            f"Input must be a directory or a text file listing MAG directories: {input_source}"
        )

    id_to_path: dict[str, Path] = {}
    for path in paths:
        mid = mag_id_from_path(path)
        if mid in id_to_path and id_to_path[mid].resolve() != path.resolve():
            if allow_duplicates:
                continue  # caller will disambiguate
            raise ValueError(
                f"Duplicate MAG ID '{mid}' from {id_to_path[mid]} and {path}. "
                f"Rename one of the files to avoid the collision, or pass --rename "
                f"to append _A, _B, ... suffixes automatically."
            )
        id_to_path[mid] = path.resolve()

    return id_to_path


def collect_all_fasta_paths(input_source) -> list[Path]:
    """Return every FASTA path discoverable from *input_source*, including
    duplicates by stem. Used by the rename logic to see the full raw set."""
    p = Path(input_source)
    paths: list[Path] = []

    if p.is_dir():
        paths.extend(_glob_fastas(p))
    elif p.is_file():
        with open(p) as f:
            for lineno, raw in enumerate(f, 1):
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                dpath = Path(line).expanduser()
                if not dpath.is_absolute():
                    dpath = (p.parent / dpath).resolve()
                if dpath.is_dir():
                    paths.extend(_glob_fastas(dpath))
    return [p.resolve() for p in paths]
