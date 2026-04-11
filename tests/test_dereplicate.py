import math
import pytest
from scripts.dereplicate import (
    compute_composite_scores,
    greedy_cluster,
    parse_edge_list,
)


def test_compute_composite_scores_basic():
    genomes = {
        "mag_A": {"quality_score": 90, "completeness": 95, "n50_bp": 100000,
                   "contamination": 1.0, "css": 0.1},
        "mag_B": {"quality_score": 50, "completeness": 65, "n50_bp": 10000,
                   "contamination": 8.0, "css": 0.4},
    }
    weights = {"w_qscore": 1.0, "w_completeness": 1.0, "w_n50": 0.5,
               "w_contam": 0.5, "w_gunc": 0.5}
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
               "w_contam": 0.5, "w_gunc": 0.5}
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


def test_greedy_cluster_single_cluster():
    scores = {"mag_A": 3.0, "mag_B": 2.0, "mag_C": 1.0}
    edges = [
        {"ref": "mag_A", "query": "mag_B", "ani": 98.0, "af_ref": 80.0, "af_query": 75.0},
        {"ref": "mag_A", "query": "mag_C", "ani": 97.0, "af_ref": 70.0, "af_query": 65.0},
        {"ref": "mag_B", "query": "mag_C", "ani": 96.5, "af_ref": 60.0, "af_query": 55.0},
    ]
    clusters = greedy_cluster(scores, edges, ani_threshold=95.0, min_af=10.0)
    assert len(set(c["cluster_id"] for c in clusters.values())) == 1
    assert clusters["mag_A"]["is_representative"] is True
    assert clusters["mag_B"]["representative"] == "mag_A"


def test_greedy_cluster_two_clusters():
    scores = {"mag_A": 3.0, "mag_B": 2.0, "mag_C": 1.0}
    edges = [
        {"ref": "mag_A", "query": "mag_B", "ani": 98.0, "af_ref": 80.0, "af_query": 75.0},
        {"ref": "mag_A", "query": "mag_C", "ani": 90.0, "af_ref": 60.0, "af_query": 55.0},
        {"ref": "mag_B", "query": "mag_C", "ani": 89.0, "af_ref": 50.0, "af_query": 45.0},
    ]
    clusters = greedy_cluster(scores, edges, ani_threshold=95.0, min_af=10.0)
    assert len(set(c["cluster_id"] for c in clusters.values())) == 2
    assert clusters["mag_A"]["cluster_id"] == clusters["mag_B"]["cluster_id"]
    assert clusters["mag_C"]["is_representative"] is True


def test_greedy_cluster_af_filter():
    """High ANI but low AF -> should NOT cluster together."""
    scores = {"mag_A": 3.0, "mag_B": 2.0}
    edges = [
        {"ref": "mag_A", "query": "mag_B", "ani": 99.0, "af_ref": 80.0, "af_query": 5.0},
    ]
    clusters = greedy_cluster(scores, edges, ani_threshold=95.0, min_af=10.0)
    assert len(set(c["cluster_id"] for c in clusters.values())) == 2


def test_greedy_cluster_no_edges():
    scores = {"mag_A": 3.0, "mag_B": 2.0, "mag_C": 1.0}
    edges = []
    clusters = greedy_cluster(scores, edges, ani_threshold=95.0, min_af=10.0)
    assert len(set(c["cluster_id"] for c in clusters.values())) == 3
    for mid in scores:
        assert clusters[mid]["is_representative"] is True
