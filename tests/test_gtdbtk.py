import pytest
from pathlib import Path
from scripts.run_gtdbtk import parse_gtdbtk_output

MOCK_BAC120_TSV = (
    "user_genome\tclassification\tfastani_reference\tfastani_radius\tfastani_ani\t"
    "fastani_af\tclosest_placement_reference\tclosest_placement_radius\t"
    "closest_placement_ani\tclosest_placement_af\tpplacer_taxonomy\t"
    "classification_method\tnote\tother_related_references(genome_id,species_name,radius,ANI,AF)\taa_percent\ttranslation_table\tred_value\twarnings\n"
    "synthetic_mag_001\td__Bacteria;p__Proteobacteria;c__Gammaproteobacteria;"
    "o__Enterobacterales;f__Enterobacteriaceae;g__Escherichia;s__Escherichia coli\t"
    "GCF_000005845.2\t95.0\t98.5\t0.92\tGCF_000005845.2\t95.0\t98.5\t0.92\t"
    "d__Bacteria;p__Proteobacteria\tANI\tN/A\tN/A\t95.2\t11\t0.95\tN/A\n"
)

MOCK_AR53_TSV = (
    "user_genome\tclassification\tfastani_reference\tfastani_radius\tfastani_ani\t"
    "fastani_af\tclosest_placement_reference\tclosest_placement_radius\t"
    "closest_placement_ani\tclosest_placement_af\tpplacer_taxonomy\t"
    "classification_method\tnote\tother_related_references(genome_id,species_name,radius,ANI,AF)\taa_percent\ttranslation_table\tred_value\twarnings\n"
    "synthetic_mag_002\td__Archaea;p__Euryarchaeota;c__Methanobacteria;"
    "o__Methanobacteriales;f__Methanobacteriaceae;g__Methanobacterium;s__Methanobacterium sp001\t"
    "GCF_000007345.1\t95.0\t96.1\t0.85\tGCF_000007345.1\t95.0\t96.1\t0.85\t"
    "d__Archaea;p__Euryarchaeota\tANI\tN/A\tN/A\t88.4\t11\t0.91\tN/A\n"
)


def test_parse_gtdbtk_bac120(tmp_path):
    bac = tmp_path / "gtdbtk.bac120.summary.tsv"
    bac.write_text(MOCK_BAC120_TSV)
    rows = parse_gtdbtk_output(bac120_path=bac)
    assert len(rows) == 1
    assert rows[0]["mag_id"] == "synthetic_mag_001"
    assert rows[0]["domain"] == "Bacteria"
    assert rows[0]["genus"] == "Escherichia"
    assert rows[0]["species"] == "Escherichia coli"
    assert rows[0]["fastani_ani"] == pytest.approx(98.5)
    assert rows[0]["classification_method"] == "ANI"


def test_parse_gtdbtk_both_domains(tmp_path):
    bac = tmp_path / "gtdbtk.bac120.summary.tsv"
    bac.write_text(MOCK_BAC120_TSV)
    ar = tmp_path / "gtdbtk.ar53.summary.tsv"
    ar.write_text(MOCK_AR53_TSV)
    rows = parse_gtdbtk_output(bac120_path=bac, ar53_path=ar)
    assert len(rows) == 2
    domains = {r["domain"] for r in rows}
    assert domains == {"Bacteria", "Archaea"}


def test_parse_gtdbtk_empty_results(tmp_path):
    bac = tmp_path / "gtdbtk.bac120.summary.tsv"
    header = MOCK_BAC120_TSV.split("\n")[0] + "\n"
    bac.write_text(header)
    rows = parse_gtdbtk_output(bac120_path=bac)
    assert len(rows) == 0
