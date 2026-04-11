"""Species-level genome dereplication via skani triangle + greedy clustering."""
from __future__ import annotations
import math
import subprocess
from pathlib import Path


def parse_edge_list(edge_path: Path) -> list[dict]:
    """Parse skani triangle edge list output."""
    edges = []
    with open(edge_path) as f:
        header = f.readline()  # skip header
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 5:
                continue
            ref_name = Path(parts[0]).stem
            query_name = Path(parts[1]).stem
            for ext in (".fna", ".fasta", ".fa"):
                ref_name = ref_name.removesuffix(ext)
                query_name = query_name.removesuffix(ext)
            edges.append({
                "ref": ref_name,
                "query": query_name,
                "ani": float(parts[2]),
                "af_ref": float(parts[3]),
                "af_query": float(parts[4]),
            })
    return edges


def _min_max_normalize(values: list[float]) -> list[float]:
    """Min-max normalize values to [0, 1]. Returns 1.0 for all if range is 0."""
    if not values:
        return []
    vmin = min(values)
    vmax = max(values)
    if vmax == vmin:
        return [1.0] * len(values)
    return [(v - vmin) / (vmax - vmin) for v in values]


def compute_composite_scores(genomes: dict[str, dict], weights: dict) -> dict[str, float]:
    """
    Compute normalized composite quality scores for representative selection.

    Each metric is min-max normalized to [0, 1] across the filtered genome set,
    then weighted and summed. Higher score = better representative.
    """
    mag_ids = list(genomes.keys())
    if not mag_ids:
        return {}

    raw_qscore = [float(genomes[m].get("quality_score", 0)) for m in mag_ids]
    raw_comp = [float(genomes[m].get("completeness", 0)) for m in mag_ids]
    raw_n50 = [math.log10(max(float(genomes[m].get("n50_bp", 1)), 1)) for m in mag_ids]
    raw_contam = [100.0 - float(genomes[m].get("contamination", 0)) for m in mag_ids]
    raw_gunc = [1.0 - float(genomes[m].get("css", 0)) for m in mag_ids]

    norm_qscore = _min_max_normalize(raw_qscore)
    norm_comp = _min_max_normalize(raw_comp)
    norm_n50 = _min_max_normalize(raw_n50)
    norm_contam = _min_max_normalize(raw_contam)
    norm_gunc = _min_max_normalize(raw_gunc)

    scores = {}
    for i, mid in enumerate(mag_ids):
        scores[mid] = (
            weights.get("w_qscore", 1.0) * norm_qscore[i]
            + weights.get("w_completeness", 1.0) * norm_comp[i]
            + weights.get("w_n50", 0.5) * norm_n50[i]
            + weights.get("w_contam", 0.5) * norm_contam[i]
            + weights.get("w_gunc", 0.5) * norm_gunc[i]
        )
    return scores


def greedy_cluster(
    scores: dict[str, float],
    edges: list[dict],
    ani_threshold: float,
    min_af: float,
) -> dict[str, dict]:
    """
    Greedy species-level clustering.

    1. Sort genomes by composite_score descending.
    2. For each unclustered genome: make it a new cluster representative.
    3. Assign unclustered neighbors where ANI >= threshold AND
       both AF directions >= min_af.
    """
    adj: dict[str, list[tuple[str, float, float, float]]] = {m: [] for m in scores}
    for e in edges:
        ref, query = e["ref"], e["query"]
        if ref in scores and query in scores:
            adj[ref].append((query, e["ani"], e["af_ref"], e["af_query"]))
            adj[query].append((ref, e["ani"], e["af_query"], e["af_ref"]))

    sorted_mags = sorted(scores.keys(), key=lambda m: scores[m], reverse=True)

    clusters: dict[str, dict] = {}
    assigned: set[str] = set()
    cluster_counter = 0

    for mag_id in sorted_mags:
        if mag_id in assigned:
            continue

        cluster_counter += 1
        cluster_id = f"cluster_{str(cluster_counter).zfill(4)}"
        members = [mag_id]
        assigned.add(mag_id)

        for neighbor, ani, af_to_neighbor, af_from_neighbor in adj[mag_id]:
            if neighbor in assigned:
                continue
            if (ani >= ani_threshold
                    and af_to_neighbor >= min_af
                    and af_from_neighbor >= min_af):
                members.append(neighbor)
                assigned.add(neighbor)

        for member in members:
            ani_to_rep = 100.0
            af_to_rep = 100.0
            if member != mag_id:
                for n, ani, af_r, af_q in adj[member]:
                    if n == mag_id:
                        ani_to_rep = ani
                        af_to_rep = af_r
                        break
            clusters[member] = {
                "mag_id": member,
                "cluster_id": cluster_id,
                "representative": mag_id,
                "is_representative": member == mag_id,
                "composite_score": scores.get(member, 0),
                "ani_to_rep": ani_to_rep,
                "af_to_rep": af_to_rep,
                "cluster_size": len(members),
            }

    return clusters


def run_triangle(
    filtered_report: str, input_dir: str,
    output_edges: str, output_genome_list: str, threads: int,
) -> None:
    """Run skani triangle on filtered genomes."""
    mag_ids = []
    with open(filtered_report) as f:
        header = f.readline().strip().split("\t")
        mag_idx = header.index("mag_id")
        for line in f:
            parts = line.strip().split("\t")
            if parts:
                mag_ids.append(parts[mag_idx])

    input_path = Path(input_dir)
    genome_paths = []
    for mid in mag_ids:
        for suffix in (".fna", ".fasta", ".fa", ".fna.gz", ".fasta.gz", ".fa.gz"):
            candidate = input_path / f"{mid}{suffix}"
            if candidate.exists():
                genome_paths.append(str(candidate.resolve()))
                break

    out_list = Path(output_genome_list)
    out_list.parent.mkdir(parents=True, exist_ok=True)
    with open(out_list, "w") as f:
        for p in genome_paths:
            f.write(p + "\n")

    out_edges = Path(output_edges)
    out_edges.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "skani", "triangle",
        "-l", str(out_list),
        "-t", str(threads),
        "-E",
        "--min-af", "10",
        "-o", str(out_edges),
    ]
    subprocess.run(cmd, check=True)


def run_cluster(
    edge_list: str, filtered_report: str,
    output_clusters: str, output_derep_report: str,
    ani_threshold: float, min_af: float,
    score_weights: dict,
) -> None:
    """Cluster genomes and select representatives."""
    genomes = {}
    with open(filtered_report) as f:
        header = f.readline().strip().split("\t")
        for line in f:
            values = line.strip().split("\t")
            row = dict(zip(header, values))
            mid = row["mag_id"]
            genomes[mid] = row

    edges = parse_edge_list(Path(edge_list))
    scores = compute_composite_scores(genomes, score_weights)
    clusters = greedy_cluster(scores, edges, ani_threshold, min_af)

    cluster_cols = [
        "mag_id", "cluster_id", "representative", "is_representative",
        "composite_score", "ani_to_rep", "af_to_rep", "cluster_size",
    ]
    out_clusters = Path(output_clusters)
    out_clusters.parent.mkdir(parents=True, exist_ok=True)
    with open(out_clusters, "w") as f:
        f.write("\t".join(cluster_cols) + "\n")
        for mid in sorted(clusters.keys()):
            c = clusters[mid]
            f.write("\t".join(str(c[col]) for col in cluster_cols) + "\n")

    reps = {mid for mid, c in clusters.items() if c["is_representative"]}
    report_header = list(genomes[next(iter(genomes))].keys()) if genomes else []
    extra_cols = ["cluster_id", "cluster_size", "composite_score"]
    out_derep = Path(output_derep_report)
    out_derep.parent.mkdir(parents=True, exist_ok=True)
    with open(out_derep, "w") as f:
        f.write("\t".join(report_header + extra_cols) + "\n")
        for mid in sorted(reps):
            row = genomes[mid]
            c = clusters[mid]
            values = [str(row.get(col, "")) for col in report_header]
            values += [str(c["cluster_id"]), str(c["cluster_size"]),
                       str(round(c["composite_score"], 4))]
            f.write("\t".join(values) + "\n")


if __name__ == "__main__":
    import ast
    import sys

    subcommand = sys.argv[1]

    if subcommand == "triangle":
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--filtered-report", required=True)
        parser.add_argument("--input-dir", required=True)
        parser.add_argument("--output-edges", required=True)
        parser.add_argument("--output-genome-list", required=True)
        parser.add_argument("--threads", type=int, default=64)
        args = parser.parse_args(sys.argv[2:])
        run_triangle(args.filtered_report, args.input_dir,
                     args.output_edges, args.output_genome_list, args.threads)

    elif subcommand == "cluster":
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--edge-list", required=True)
        parser.add_argument("--filtered-report", required=True)
        parser.add_argument("--output-clusters", required=True)
        parser.add_argument("--output-derep-report", required=True)
        parser.add_argument("--ani-threshold", type=float, default=95.0)
        parser.add_argument("--min-af", type=float, default=10.0)
        parser.add_argument("--score-weights", default="{}")
        args = parser.parse_args(sys.argv[2:])
        weights = ast.literal_eval(args.score_weights) if args.score_weights else {}
        run_cluster(args.edge_list, args.filtered_report,
                    args.output_clusters, args.output_derep_report,
                    args.ani_threshold, args.min_af, weights)
