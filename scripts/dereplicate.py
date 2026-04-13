"""Species-level genome dereplication via skani triangle + average-linkage clustering."""
from __future__ import annotations
import math
import subprocess
from pathlib import Path

import numpy as np
from scipy.cluster.hierarchy import linkage, fcluster
from scipy.spatial.distance import squareform


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

    # Coerce weights to float (Snakemake's config pipeline can stringify values)
    w_qscore = float(weights.get("w_qscore", 1.0))
    w_completeness = float(weights.get("w_completeness", 1.0))
    w_n50 = float(weights.get("w_n50", 0.5))
    w_contam = float(weights.get("w_contam", 0.5))

    raw_qscore = [float(genomes[m].get("quality_score", 0)) for m in mag_ids]
    raw_comp = [float(genomes[m].get("completeness", 0)) for m in mag_ids]
    raw_n50 = [math.log10(max(float(genomes[m].get("n50_bp", 1)), 1)) for m in mag_ids]
    raw_contam = [100.0 - float(genomes[m].get("contamination", 0)) for m in mag_ids]

    norm_qscore = _min_max_normalize(raw_qscore)
    norm_comp = _min_max_normalize(raw_comp)
    norm_n50 = _min_max_normalize(raw_n50)
    norm_contam = _min_max_normalize(raw_contam)

    scores = {}
    for i, mid in enumerate(mag_ids):
        scores[mid] = (
            w_qscore * norm_qscore[i]
            + w_completeness * norm_comp[i]
            + w_n50 * norm_n50[i]
            + w_contam * norm_contam[i]
        )
    return scores


def build_distance_matrix(
    mag_ids: list[str],
    edges: list[dict],
    min_af: float,
) -> np.ndarray:
    """Build a symmetric ANI distance matrix from skani edges.

    - Pairs passing the bi-directional AF filter: distance = 100 - ANI
    - Pairs failing AF filter or with no edge: distance = 100 (blocked)
    """
    n = len(mag_ids)
    idx = {mid: i for i, mid in enumerate(mag_ids)}
    dist = np.full((n, n), 100.0)
    np.fill_diagonal(dist, 0.0)

    for e in edges:
        ref, query = e["ref"], e["query"]
        if ref not in idx or query not in idx:
            continue
        # Bi-directional AF filter
        if e["af_ref"] < min_af or e["af_query"] < min_af:
            continue
        d = 100.0 - e["ani"]
        i, j = idx[ref], idx[query]
        dist[i, j] = d
        dist[j, i] = d

    return dist


def _find_connected_components(
    mag_ids: list[str],
    edges: list[dict],
    min_af: float,
    component_ani: float = 90.0,
) -> list[list[str]]:
    """Find connected components in the genome similarity graph.

    An edge is included if ANI >= component_ani AND both AF directions >= min_af.
    Genomes with no qualifying edges become singleton components.
    """
    mag_set = set(mag_ids)
    adj: dict[str, set[str]] = {m: set() for m in mag_ids}
    for e in edges:
        ref, query = e["ref"], e["query"]
        if ref not in mag_set or query not in mag_set:
            continue
        if e["ani"] < component_ani:
            continue
        if e["af_ref"] < min_af or e["af_query"] < min_af:
            continue
        adj[ref].add(query)
        adj[query].add(ref)

    visited: set[str] = set()
    components: list[list[str]] = []
    for mid in mag_ids:
        if mid in visited:
            continue
        # BFS
        component = []
        queue = [mid]
        visited.add(mid)
        while queue:
            node = queue.pop(0)
            component.append(node)
            for neighbor in adj[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        components.append(sorted(component))

    return components


def _cluster_component(
    component: list[str],
    scores: dict[str, float],
    edges: list[dict],
    ani_threshold: float,
    min_af: float,
    pair_ani: dict[tuple[str, str], tuple[float, float]],
) -> list[tuple[str, list[str]]]:
    """Run average-linkage clustering on a single connected component.

    Returns a list of (representative, members) tuples.
    """
    # Singleton — trivial cluster
    if len(component) == 1:
        return [(component[0], component)]

    # Two genomes — check if they cluster
    if len(component) == 2:
        a, b = component
        ani_val, _ = pair_ani.get((a, b), (0.0, 0.0))
        if ani_val >= ani_threshold:
            rep = max(component, key=lambda m: scores.get(m, 0))
            return [(rep, component)]
        else:
            return [(a, [a]), (b, [b])]

    dist = build_distance_matrix(component, edges, min_af)
    condensed = squareform(dist)
    Z = linkage(condensed, method="average")
    cut_distance = 100.0 - ani_threshold
    labels = fcluster(Z, t=cut_distance, criterion="distance")

    label_members: dict[int, list[str]] = {}
    for i, lab in enumerate(labels):
        label_members.setdefault(lab, []).append(component[i])

    result = []
    for members in label_members.values():
        rep = max(members, key=lambda m: scores.get(m, 0))
        result.append((rep, members))
    return result


def average_linkage_cluster(
    scores: dict[str, float],
    edges: list[dict],
    ani_threshold: float,
    min_af: float,
) -> dict[str, dict]:
    """
    Species-level clustering via average linkage (UPGMA).

    For scalability, genomes are first partitioned into connected components
    at 90% ANI. Average-linkage clustering is then performed independently
    within each component, avoiding a single large distance matrix.

    1. Find connected components at 90% ANI (with AF filter).
    2. Within each component, build distance matrix and run average linkage.
    3. Cut dendrogram at (100 - ani_threshold) to define species clusters.
    4. Select the highest composite-score genome as representative per cluster.
    """
    mag_ids = sorted(scores.keys())
    if not mag_ids:
        return {}

    # Build pair lookup for ANI/AF to representative
    pair_ani: dict[tuple[str, str], tuple[float, float]] = {}
    for e in edges:
        pair_ani[(e["ref"], e["query"])] = (e["ani"], e["af_ref"])
        pair_ani[(e["query"], e["ref"])] = (e["ani"], e["af_query"])

    components = _find_connected_components(mag_ids, edges, min_af)

    clusters: dict[str, dict] = {}
    cluster_counter = 0

    for component in components:
        sub_clusters = _cluster_component(
            component, scores, edges, ani_threshold, min_af, pair_ani,
        )
        for rep, members in sub_clusters:
            cluster_counter += 1
            cluster_id = f"cluster_{str(cluster_counter).zfill(4)}"

            for member in members:
                if member == rep:
                    ani_to_rep = 100.0
                    af_to_rep = 100.0
                else:
                    ani_to_rep, af_to_rep = pair_ani.get((member, rep), (0.0, 0.0))

                clusters[member] = {
                    "mag_id": member,
                    "cluster_id": cluster_id,
                    "representative": rep,
                    "is_representative": member == rep,
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
    """Run skani triangle on filtered genomes.

    *input_dir* may be either a directory of FASTAs or a text file with one
    FASTA path per line. Resolution is delegated to the shared inputs module
    so the Snakefile and this script stay in sync.
    """
    mag_ids = []
    with open(filtered_report) as f:
        header = f.readline().strip().split("\t")
        mag_idx = header.index("mag_id")
        for line in f:
            parts = line.strip().split("\t")
            if parts:
                mag_ids.append(parts[mag_idx])

    from meta_pipeline_magdrep.inputs import build_mag_path_map
    path_map = build_mag_path_map(input_dir)
    genome_paths = [str(path_map[mid]) for mid in mag_ids if mid in path_map]

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
    clusters = average_linkage_cluster(scores, edges, ani_threshold, min_af)

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
    import json
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
        weights = json.loads(args.score_weights) if args.score_weights else {}
        run_cluster(args.edge_list, args.filtered_report,
                    args.output_clusters, args.output_derep_report,
                    args.ani_threshold, args.min_af, weights)
