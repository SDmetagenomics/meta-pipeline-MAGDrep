"""Input uniqueness checks and optional renaming.

Pipeline tools (CheckM2, GTDB-Tk, skani) all assume unique genome filenames
and unique contig names within each genome. This module:

1. Verifies both invariants.
2. When asked (--rename), produces a normalized staging directory:
   - Duplicate genome IDs get an _A, _B, ... suffix.
   - Every contig in every genome is renamed to {genome_id}_scaffold_{N}.
"""
from __future__ import annotations

import gzip
import string
from collections import Counter, defaultdict
from pathlib import Path

from .inputs import collect_all_fasta_paths, mag_id_from_path


class InputValidationError(ValueError):
    """Raised when input genomes fail uniqueness checks and --rename isn't set."""


def _open_fasta(path: Path):
    """Return an open file handle for a FASTA file (gzipped or plain, text mode)."""
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt")
    return open(path, "r")


def _iter_contig_headers(path: Path):
    """Yield contig names (everything after '>' up to first whitespace) in order."""
    with _open_fasta(path) as f:
        for line in f:
            if line.startswith(">"):
                yield line[1:].strip().split(None, 1)[0]


def check_contig_uniqueness(path: Path) -> list[str]:
    """Return the list of duplicated contig names in a FASTA (empty if unique)."""
    seen = Counter()
    for name in _iter_contig_headers(path):
        seen[name] += 1
    return [n for n, c in seen.items() if c > 1]


def assign_unique_genome_ids(paths: list[Path]) -> dict[Path, str]:
    """Return {original_path: final_mag_id} resolving duplicate stems via _A, _B, ... suffixes.

    Suffixes are assigned in the order paths appear. Lone IDs are left alone.
    For collisions > 26 we wrap to AA, AB, ... so we can scale.
    """
    # Group paths by their raw stem ID
    groups: dict[str, list[Path]] = defaultdict(list)
    for p in paths:
        groups[mag_id_from_path(p)].append(p)

    mapping: dict[Path, str] = {}
    for base, ps in groups.items():
        if len(ps) == 1:
            mapping[ps[0]] = base
            continue
        for i, p in enumerate(ps):
            mapping[p] = f"{base}_{_suffix(i)}"
    return mapping


def _suffix(index: int) -> str:
    """0 → A, 25 → Z, 26 → AA, 27 → AB, …"""
    letters = string.ascii_uppercase
    if index < 26:
        return letters[index]
    q, r = divmod(index, 26)
    return _suffix(q - 1) + letters[r]


def check_uniqueness(input_source) -> dict:
    """Return a report describing any uniqueness problems. Empty dict = all good."""
    paths = collect_all_fasta_paths(input_source)

    # Genome ID collisions
    id_counts: dict[str, list[Path]] = defaultdict(list)
    for p in paths:
        id_counts[mag_id_from_path(p)].append(p)
    duplicate_genome_ids = {mid: ps for mid, ps in id_counts.items() if len(ps) > 1}

    # Contig uniqueness (within each genome only)
    contig_collisions: dict[str, list[str]] = {}
    for p in paths:
        dups = check_contig_uniqueness(p)
        if dups:
            contig_collisions[str(p)] = dups

    report: dict = {}
    if duplicate_genome_ids:
        report["duplicate_genome_ids"] = {
            mid: [str(p) for p in ps] for mid, ps in duplicate_genome_ids.items()
        }
    if contig_collisions:
        report["contig_collisions"] = contig_collisions
    return report


def format_uniqueness_report(report: dict) -> str:
    """Render a human-readable summary of uniqueness issues."""
    lines = []
    if "duplicate_genome_ids" in report:
        lines.append(f"Duplicate genome IDs ({len(report['duplicate_genome_ids'])}):")
        for mid, ps in report["duplicate_genome_ids"].items():
            lines.append(f"  {mid}:")
            for p in ps:
                lines.append(f"    - {p}")
    if "contig_collisions" in report:
        lines.append(f"Duplicate contig names within genomes ({len(report['contig_collisions'])}):")
        for fasta, dups in report["contig_collisions"].items():
            lines.append(f"  {fasta}: {', '.join(dups[:5])}" + (f" ...and {len(dups)-5} more" if len(dups) > 5 else ""))
    return "\n".join(lines)


def _write_renamed_fasta(src: Path, dst: Path, genome_id: str) -> int:
    """Copy *src* to *dst* rewriting each contig header to {genome_id}_scaffold_{N}.

    Returns the number of contigs written.
    """
    contig_n = 0
    dst.parent.mkdir(parents=True, exist_ok=True)
    # Output as plain FASTA (no gzip) for downstream tool compatibility —
    # Snakemake rules copy/symlink these into batch dirs.
    with _open_fasta(src) as fin, open(dst, "w") as fout:
        for line in fin:
            if line.startswith(">"):
                contig_n += 1
                fout.write(f">{genome_id}_scaffold_{contig_n}\n")
            else:
                fout.write(line)
    return contig_n


def stage_normalized_inputs(
    input_source,
    staging_dir: Path,
    rename: bool,
) -> tuple[Path, dict[str, Path]]:
    """Produce a flat directory of MAGs ready for the pipeline.

    Behavior:
      - rename=False: validate uniqueness; fail with InputValidationError
        if any collisions exist. Otherwise symlink originals into
        staging_dir/.
      - rename=True:  resolve duplicate genome IDs via _A, _B suffixes and
        rewrite every contig header to {genome_id}_scaffold_{N}. Writes
        full copies (always plain .fna) so downstream tools see consistent
        naming.

    Returns (staging_dir, {mag_id: path}).
    """
    staging_dir = Path(staging_dir)
    paths = collect_all_fasta_paths(input_source)

    if not paths:
        raise InputValidationError(f"No FASTA files found from {input_source}")

    if not rename:
        report = check_uniqueness(input_source)
        if report:
            msg = format_uniqueness_report(report)
            raise InputValidationError(
                "Input genomes failed uniqueness checks:\n" + msg
                + "\n\nRe-run with --rename to auto-resolve "
                  "(suffixes duplicate genome IDs and rewrites contig headers)."
            )

    staging_dir.mkdir(parents=True, exist_ok=True)

    id_map: dict[str, Path] = {}
    if rename:
        final_ids = assign_unique_genome_ids(paths)
        for src, mag_id in final_ids.items():
            dst = staging_dir / f"{mag_id}.fna"
            _write_renamed_fasta(src, dst, mag_id)
            id_map[mag_id] = dst
    else:
        # Uniqueness verified above; straight symlink.
        for src in paths:
            mag_id = mag_id_from_path(src)
            dst = staging_dir / src.name
            if not dst.exists():
                import os
                os.symlink(src.resolve(), dst)
            id_map[mag_id] = dst

    return staging_dir, id_map
