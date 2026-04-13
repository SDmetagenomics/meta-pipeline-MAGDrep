import math
import pytest
from scripts.dereplicate import (
    compute_composite_scores,
    average_linkage_cluster,
    build_distance_matrix,
    parse_edge_list,
    _find_connected_components,
)


def test_compute_composite_scores_basic():
    genomes = {
        "mag_A": {"quality_score": 90, "completeness": 95, "n50_bp": 100000,
                   "contamination": 1.0, "css": 0.1},
        "mag_B": {"quality_score": 50, "completeness": 65, "n50_bp": 10000,
                   "contamination": 8.0, "css": 0.4},
    }
    weights = {"w_qscore": 1.0, "w_completeness": 1.0, "w_n50": 0.5,
               "w_contam": 0.5}
    scores = compute_composite_scores(genomes, weights)
    assert scores["mag_A"] > scores["mag_B"]


def test_compute_composite_scores_identical_values():
    genomes = {
        "mag_A": {"quality_score": 90, "completeness": 95, "n50_bp": 50000,
                   "contamination": 1.0, "css": 0.0},
        "mag_B": {"quality_score": 90, "completeness": 95, "n50_bp": 50000,
                   "contamination": 1.0, "css": 0.0},
    }
    weights = {"w_qscore": 1.0, "w_completeness": 1.0, "w_n50": 0.5,
               "w_contam": 0.5}
    scores = compute_composite_scores(genomes, weights)
    assert scores["mag_A"] == pytest.approx(scores["mag_B"])


def test_parse_edge_list(tmp_path):
    edge_file = tmp_path / "edges.tsv"
    edge_file.write_text(
        "Ref_file\tQuery_file\tANI\tAlign_fraction_ref\tAlign_fraction_query\tRef_name\tQuery_name\n"
        "/mags/mag_A.fna\t/mags/mag_B.fna\t97.5\t85.0\t82.0\tmag_A\tmag_B\n"
        "/mags/mag_A.fna\t/mags/mag_C.fna\t96.0\t70.0\t5.0\tmag_A\tmag_C\n"
    )
    edges = parse_edge_list(edge_file)
    assert len(edges) == 2
    assert edges[0]["ani"] == pytest.approx(97.5)
    assert edges[0]["af_ref"] == pytest.approx(85.0)
    assert edges[0]["af_query"] == pytest.approx(82.0)


def test_build_distance_matrix_basic():
    mag_ids = ["mag_A", "mag_B", "mag_C"]
    edges = [
        {"ref": "mag_A", "query": "mag_B", "ani": 98.0, "af_ref": 80.0, "af_query": 75.0},
        {"ref": "mag_A", "query": "mag_C", "ani": 96.0, "af_ref": 70.0, "af_query": 65.0},
        {"ref": "mag_B", "query": "mag_C", "ani": 97.0, "af_ref": 60.0, "af_query": 55.0},
    ]
    dist = build_distance_matrix(mag_ids, edges, min_af=10.0)
    assert dist[0, 0] == pytest.approx(0.0)  # self
    assert dist[0, 1] == pytest.approx(2.0)  # 100 - 98
    assert dist[0, 2] == pytest.approx(4.0)  # 100 - 96
    assert dist[1, 2] == pytest.approx(3.0)  # 100 - 97
    # Symmetric
    assert dist[1, 0] == pytest.approx(dist[0, 1])


def test_build_distance_matrix_af_filter():
    """Pairs failing bi-directional AF should get distance 100."""
    mag_ids = ["mag_A", "mag_B"]
    edges = [
        {"ref": "mag_A", "query": "mag_B", "ani": 99.0, "af_ref": 80.0, "af_query": 5.0},
    ]
    dist = build_distance_matrix(mag_ids, edges, min_af=10.0)
    assert dist[0, 1] == pytest.approx(100.0)  # blocked


def test_build_distance_matrix_no_edge():
    """Pairs with no skani edge get distance 100."""
    mag_ids = ["mag_A", "mag_B"]
    dist = build_distance_matrix(mag_ids, [], min_af=10.0)
    assert dist[0, 1] == pytest.approx(100.0)


def test_average_linkage_single_cluster():
    """Three genomes all >95% ANI should form one cluster."""
    scores = {"mag_A": 3.0, "mag_B": 2.0, "mag_C": 1.0}
    edges = [
        {"ref": "mag_A", "query": "mag_B", "ani": 98.0, "af_ref": 80.0, "af_query": 75.0},
        {"ref": "mag_A", "query": "mag_C", "ani": 97.0, "af_ref": 70.0, "af_query": 65.0},
        {"ref": "mag_B", "query": "mag_C", "ani": 96.5, "af_ref": 60.0, "af_query": 55.0},
    ]
    clusters = average_linkage_cluster(scores, edges, ani_threshold=95.0, min_af=10.0)
    assert len(set(c["cluster_id"] for c in clusters.values())) == 1
    # Highest-scoring genome is representative
    assert clusters["mag_A"]["is_representative"] is True
    assert clusters["mag_B"]["representative"] == "mag_A"
    assert clusters["mag_C"]["representative"] == "mag_A"


def test_average_linkage_two_clusters():
    """A-B are close (98%), C is distant (90%) — should split into two clusters."""
    scores = {"mag_A": 3.0, "mag_B": 2.0, "mag_C": 1.0}
    edges = [
        {"ref": "mag_A", "query": "mag_B", "ani": 98.0, "af_ref": 80.0, "af_query": 75.0},
        {"ref": "mag_A", "query": "mag_C", "ani": 90.0, "af_ref": 60.0, "af_query": 55.0},
        {"ref": "mag_B", "query": "mag_C", "ani": 89.0, "af_ref": 50.0, "af_query": 45.0},
    ]
    clusters = average_linkage_cluster(scores, edges, ani_threshold=95.0, min_af=10.0)
    assert len(set(c["cluster_id"] for c in clusters.values())) == 2
    assert clusters["mag_A"]["cluster_id"] == clusters["mag_B"]["cluster_id"]
    assert clusters["mag_C"]["is_representative"] is True


def test_average_linkage_af_blocks_clustering():
    """High ANI but low AF -> should NOT cluster together."""
    scores = {"mag_A": 3.0, "mag_B": 2.0}
    edges = [
        {"ref": "mag_A", "query": "mag_B", "ani": 99.0, "af_ref": 80.0, "af_query": 5.0},
    ]
    clusters = average_linkage_cluster(scores, edges, ani_threshold=95.0, min_af=10.0)
    assert len(set(c["cluster_id"] for c in clusters.values())) == 2


def test_average_linkage_no_edges():
    """No edges at all — every genome is its own cluster."""
    scores = {"mag_A": 3.0, "mag_B": 2.0, "mag_C": 1.0}
    edges = []
    clusters = average_linkage_cluster(scores, edges, ani_threshold=95.0, min_af=10.0)
    assert len(set(c["cluster_id"] for c in clusters.values())) == 3
    for mid in scores:
        assert clusters[mid]["is_representative"] is True


def test_average_linkage_single_genome():
    """Single genome: trivial cluster."""
    scores = {"mag_A": 3.0}
    clusters = average_linkage_cluster(scores, [], ani_threshold=95.0, min_af=10.0)
    assert len(clusters) == 1
    assert clusters["mag_A"]["is_representative"] is True
    assert clusters["mag_A"]["cluster_size"] == 1


def test_average_linkage_representative_is_highest_score():
    """The representative should be the genome with the highest composite score."""
    scores = {"mag_A": 1.0, "mag_B": 5.0, "mag_C": 3.0}
    edges = [
        {"ref": "mag_A", "query": "mag_B", "ani": 99.0, "af_ref": 80.0, "af_query": 75.0},
        {"ref": "mag_A", "query": "mag_C", "ani": 98.0, "af_ref": 70.0, "af_query": 65.0},
        {"ref": "mag_B", "query": "mag_C", "ani": 97.5, "af_ref": 60.0, "af_query": 55.0},
    ]
    clusters = average_linkage_cluster(scores, edges, ani_threshold=95.0, min_af=10.0)
    assert clusters["mag_B"]["is_representative"] is True
    assert clusters["mag_A"]["representative"] == "mag_B"


def test_average_linkage_differs_from_greedy():
    """Average linkage can produce different results than greedy.

    Consider: A-B at 96%, A-C at 96%, B-C at 93%.
    Greedy (starting from highest score A): A claims B and C since both >95% to A.
    Average linkage: after merging A-B (distance 4), the average distance from
    {A,B} to C is (4 + 7)/2 = 5.5 > cut distance 5, so C stays separate.
    """
    scores = {"mag_A": 3.0, "mag_B": 2.0, "mag_C": 1.0}
    edges = [
        {"ref": "mag_A", "query": "mag_B", "ani": 96.0, "af_ref": 80.0, "af_query": 75.0},
        {"ref": "mag_A", "query": "mag_C", "ani": 96.0, "af_ref": 70.0, "af_query": 65.0},
        {"ref": "mag_B", "query": "mag_C", "ani": 93.0, "af_ref": 60.0, "af_query": 55.0},
    ]
    clusters = average_linkage_cluster(scores, edges, ani_threshold=95.0, min_af=10.0)
    # Average linkage: {A,B} merge at distance 4, but avg distance to C is 5.5 > 5.0
    # So C should be in its own cluster
    assert clusters["mag_A"]["cluster_id"] == clusters["mag_B"]["cluster_id"]
    assert clusters["mag_C"]["cluster_id"] != clusters["mag_A"]["cluster_id"]


# --- Connected component tests ---


def test_connected_components_single_group():
    """All genomes connected at >= 90% ANI form one component."""
    mag_ids = ["A", "B", "C"]
    edges = [
        {"ref": "A", "query": "B", "ani": 95.0, "af_ref": 80.0, "af_query": 75.0},
        {"ref": "B", "query": "C", "ani": 92.0, "af_ref": 60.0, "af_query": 55.0},
    ]
    components = _find_connected_components(mag_ids, edges, min_af=10.0)
    assert len(components) == 1
    assert sorted(components[0]) == ["A", "B", "C"]


def test_connected_components_two_groups():
    """A-B connected, C isolated (ANI to others < 90%)."""
    mag_ids = ["A", "B", "C"]
    edges = [
        {"ref": "A", "query": "B", "ani": 95.0, "af_ref": 80.0, "af_query": 75.0},
        {"ref": "A", "query": "C", "ani": 85.0, "af_ref": 60.0, "af_query": 55.0},
    ]
    components = _find_connected_components(mag_ids, edges, min_af=10.0)
    assert len(components) == 2
    sizes = sorted(len(c) for c in components)
    assert sizes == [1, 2]


def test_connected_components_af_filter():
    """High ANI but low AF should not connect genomes."""
    mag_ids = ["A", "B"]
    edges = [
        {"ref": "A", "query": "B", "ani": 95.0, "af_ref": 80.0, "af_query": 5.0},
    ]
    components = _find_connected_components(mag_ids, edges, min_af=10.0)
    assert len(components) == 2


def test_connected_components_all_singletons():
    """No edges at all — every genome is its own component."""
    mag_ids = ["A", "B", "C"]
    components = _find_connected_components(mag_ids, [], min_af=10.0)
    assert len(components) == 3


def test_average_linkage_with_components_large():
    """Test that component-based clustering handles multiple independent groups.

    Group 1: A, B, C (all >95% ANI to each other)
    Group 2: D, E (>95% ANI to each other, <90% to group 1)
    Singleton: F (no edges above 90%)
    """
    scores = {"A": 5.0, "B": 3.0, "C": 1.0, "D": 4.0, "E": 2.0, "F": 6.0}
    edges = [
        # Group 1
        {"ref": "A", "query": "B", "ani": 98.0, "af_ref": 80.0, "af_query": 75.0},
        {"ref": "A", "query": "C", "ani": 97.0, "af_ref": 70.0, "af_query": 65.0},
        {"ref": "B", "query": "C", "ani": 96.5, "af_ref": 60.0, "af_query": 55.0},
        # Group 2
        {"ref": "D", "query": "E", "ani": 96.0, "af_ref": 75.0, "af_query": 70.0},
        # Cross-group (below 90% — should not connect)
        {"ref": "A", "query": "D", "ani": 85.0, "af_ref": 50.0, "af_query": 45.0},
    ]
    clusters = average_linkage_cluster(scores, edges, ani_threshold=95.0, min_af=10.0)

    # 3 clusters: {A,B,C}, {D,E}, {F}
    cluster_ids = set(c["cluster_id"] for c in clusters.values())
    assert len(cluster_ids) == 3

    # Group 1 together, A is rep (highest score)
    assert clusters["A"]["cluster_id"] == clusters["B"]["cluster_id"]
    assert clusters["A"]["cluster_id"] == clusters["C"]["cluster_id"]
    assert clusters["A"]["is_representative"] is True

    # Group 2 together, D is rep
    assert clusters["D"]["cluster_id"] == clusters["E"]["cluster_id"]
    assert clusters["D"]["is_representative"] is True

    # F is singleton
    assert clusters["F"]["is_representative"] is True
    assert clusters["F"]["cluster_size"] == 1
