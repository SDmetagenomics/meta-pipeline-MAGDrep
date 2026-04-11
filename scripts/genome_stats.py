"""Compute genome-level statistics from a FASTA file.

Primary: SeqKit (fast, Go-based). Fallback: BioPython (pure Python).
Uses shutil.which() to check SeqKit availability at runtime.
"""
from __future__ import annotations
import gzip
import shutil
import subprocess
from pathlib import Path


def _compute_n50(lengths: list[int]) -> int:
    """Return N50 for a list of contig lengths."""
    if not lengths:
        return 0
    lengths = sorted(lengths, reverse=True)
    half_total = sum(lengths) / 2
    cumsum = 0
    for length in lengths:
        cumsum += length
        if cumsum >= half_total:
            return length
    return 0


def _stats_via_seqkit(fasta_path: Path) -> dict:
    """Compute stats using SeqKit (fast path)."""
    fasta_path = Path(fasta_path)

    # Get basic stats
    result = subprocess.run(
        ["seqkit", "stats", "--tabular", str(fasta_path)],
        capture_output=True, text=True, check=True,
    )
    lines = result.stdout.strip().split("\n")
    header = lines[0].split("\t")
    values = lines[1].split("\t")
    seqkit_stats = dict(zip(header, values))

    # Get per-contig GC and lengths
    result = subprocess.run(
        ["seqkit", "fx2tab", "--name", "--only-id", "--gc", "--length", str(fasta_path)],
        capture_output=True, text=True, check=True,
    )
    lengths = []
    gc_weighted_sum = 0.0
    total_length = 0
    for line in result.stdout.strip().split("\n"):
        parts = line.split("\t")
        if len(parts) >= 3:
            length = int(parts[2])
            gc = float(parts[1])
            lengths.append(length)
            gc_weighted_sum += gc * length
            total_length += length

    gc_pct = round(gc_weighted_sum / total_length, 2) if total_length > 0 else 0.0

    return {
        "total_length_bp": total_length,
        "gc_percent": gc_pct,
        "contig_count": len(lengths),
        "n50_bp": _compute_n50(lengths),
        "largest_contig_bp": max(lengths) if lengths else 0,
    }


def _stats_via_biopython(fasta_path: Path) -> dict:
    """Compute stats using BioPython (fallback path)."""
    from Bio import SeqIO
    from Bio.SeqUtils import gc_fraction

    fasta_path = Path(fasta_path)
    opener = gzip.open if fasta_path.suffix == ".gz" else open

    with opener(fasta_path, "rt") as f:
        records = list(SeqIO.parse(f, "fasta"))

    lengths = [len(r.seq) for r in records]
    total_length = sum(lengths)

    # Length-weighted GC across all contigs
    total_gc = sum(gc_fraction(r.seq) * len(r.seq) for r in records)
    gc_pct = round((total_gc / total_length) * 100, 2) if total_length > 0 else 0.0

    return {
        "total_length_bp": total_length,
        "gc_percent": gc_pct,
        "contig_count": len(records),
        "n50_bp": _compute_n50(lengths),
        "largest_contig_bp": max(lengths) if lengths else 0,
    }


def compute_genome_stats(fasta_path: Path) -> dict:
    """
    Compute genome stats from a FASTA file (plain or gzipped).
    Uses SeqKit if available, falls back to BioPython.
    """
    fasta_path = Path(fasta_path)

    # Derive MAG ID from filename
    mag_id = fasta_path.name
    for suffix in (".fasta.gz", ".fa.gz", ".fna.gz", ".fasta", ".fna", ".fa"):
        if mag_id.endswith(suffix):
            mag_id = mag_id[: -len(suffix)]
            break

    if shutil.which("seqkit"):
        stats = _stats_via_seqkit(fasta_path)
    else:
        stats = _stats_via_biopython(fasta_path)

    return {
        "mag_id": mag_id,
        "total_length_bp": stats["total_length_bp"],
        "gc_percent": stats["gc_percent"],
        "contig_count": stats["contig_count"],
        "n50_bp": stats["n50_bp"],
        "largest_contig_bp": stats["largest_contig_bp"],
    }


def write_stats_tsv(stats: dict, output_path: Path) -> None:
    """Write stats dict as a two-row TSV (header + data)."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(stats.keys())
    with open(output_path, "w") as f:
        f.write("\t".join(keys) + "\n")
        f.write("\t".join(str(stats[k]) for k in keys) + "\n")


if __name__ == "__main__":
    import sys
    fasta = Path(sys.argv[1])
    output = Path(sys.argv[2])
    stats = compute_genome_stats(fasta)
    write_stats_tsv(stats, output)
