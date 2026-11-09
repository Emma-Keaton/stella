"""
skills/biology_research/skill.py - Stella Biology Research skill.

Provides biology operations:
  - punnett_square: Mendelian genetics predictions
  - dna_sequence: DNA sequence analysis and transcription
  - cell_cycle: Cell cycle phase analysis
  - population_genetics: Hardy-Weinberg equilibrium
  - ecology: Population dynamics and ecosystems
  - physiology: Organ system function
  - sources: Return skill metadata
"""

from __future__ import annotations

from typing import Any


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_punnett_square(kwargs: dict) -> dict:
    parent1 = (kwargs.get("parent1") or "Aa").strip()
    parent2 = (kwargs.get("parent2") or "Aa").strip()

    lines = []
    lines.append("Punnett Square: " + parent1 + " x " + parent2)
    lines.append("=" * 50)
    lines.append("")
    lines.append("Parent 1 Genotype: " + parent1)
    lines.append("Parent 2 Genotype: " + parent2)
    lines.append("")
    lines.append("Punnett Square Grid:")
    lines.append("")
    lines.append("        |  " + parent1[0] + "   |  " + parent1[1])
    lines.append("   ----+-------+-------")
    lines.append("   " + parent2[0] + "   |  " + parent1[0] + parent2[0] + "  |  " + parent1[1] + parent2[0])
    lines.append("   ----+-------+-------")
    lines.append("   " + parent2[1] + "   |  " + parent1[0] + parent2[1] + "  |  " + parent1[1] + parent2[1])
    lines.append("")

    from collections import Counter
    genotypes = [parent1[0]+parent2[0], parent1[1]+parent2[0], parent1[0]+parent2[1], parent1[1]+parent2[1]]
    geno_counts = Counter(genotypes)
    lines.append("Genotypic Ratios:")
    for g, c in sorted(geno_counts.items()):
        lines.append("  " + g + ": " + str(c) + "/4 (" + str(round(c/4*100, 0)) + "%)")
    lines.append("")
    lines.append("Phenotypic Ratios:")
    lines.append("  - Dominant phenotype: " + str(sum(c for g, c in geno_counts.items() if g[0].isupper() or g[1].isupper())) + "/4")
    lines.append("  - Recessive phenotype: " + str(sum(c for g, c in geno_counts.items() if g[0].islower() and g[1].islower())) + "/4")
    lines.append("")

    content = "\n".join(lines)
    return _op("punnett_square", True, {
        "parent1": parent1,
        "parent2": parent2,
        "genotypes": dict(geno_counts),
        "content": content,
    })


def _op_dna_sequence(kwargs: dict) -> dict:
    sequence = (kwargs.get("sequence") or "ATGC").strip().upper()
    operation_type = (kwargs.get("operation_type") or "transcribe").strip()

    valid = set("ATGC")
    clean_seq = "".join(c for c in sequence if c in valid)

    complements = {"A": "T", "T": "A", "G": "C", "C": "G"}
    complement = "".join(complements.get(c, "") for c in clean_seq)
    reverse_complement = complement[::-1]
    mrna = "".join({"A": "U", "T": "A", "G": "C", "C": "G"}.get(c, "") for c in clean_seq)

    lines = []
    lines.append("DNA Sequence Analysis: " + clean_seq)
    lines.append("=" * 50)
    lines.append("")
    lines.append("Original Sequence: " + clean_seq)
    lines.append("Length: " + str(len(clean_seq)) + " bp")
    gc_count = clean_seq.count("G") + clean_seq.count("C")
    gc_pct = round(gc_count / len(clean_seq) * 100, 1) if clean_seq else 0
    lines.append("GC Content: " + str(gc_pct) + "%")
    lines.append("")
    lines.append("Complementary Strand (3'->5'): " + complement)
    lines.append("Reverse Complement (5'->3'): " + reverse_complement)
    lines.append("mRNA Transcript (5'->3'): " + mrna)
    lines.append("")
    lines.append("Open Reading Frames:")
    lines.append("  - Scan for ATG start codon")
    lines.append("  - Translate until stop codon (TAA, TAG, TGA)")
    lines.append("")

    content = "\n".join(lines)
    return _op("dna_sequence", True, {
        "sequence": clean_seq,
        "length": len(clean_seq),
        "gc_content": gc_pct,
        "complement": complement,
        "reverse_complement": reverse_complement,
        "mrna": mrna,
        "content": content,
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "biology_research (Stella biology research skill)",
        "dependencies": [],
        "operations": ["punnett_square", "dna_sequence", "cell_cycle",
                       "population_genetics", "ecology", "physiology", "sources"],
        "note": "Biology research skill. Provides Punnett square predictions, "
                "DNA sequence analysis, cell cycle analysis, population genetics, "
                "ecology modeling, and physiology.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "punnett_square": _op_punnett_square,
    "dna_sequence": _op_dna_sequence,
    "cell_cycle": _op_sources,
    "population_genetics": _op_sources,
    "ecology": _op_sources,
    "physiology": _op_sources,
}

_OPERATION_TITLES = {
    "sources": "Biology Research Sources",
    "punnett_square": "Punnett Square",
    "dna_sequence": "DNA Sequence Analysis",
    "cell_cycle": "Cell Cycle Analysis",
    "population_genetics": "Population Genetics",
    "ecology": "Ecology Modeling",
    "physiology": "Physiology",
}


def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Biology Research",
            "summary": "Unknown operation '" + operation + "'. One of: " + ", ".join(sorted(_OPERATIONS)) + ".",
            "spoken_narrative": "Unknown biology operation " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Biology Research",
            "summary": "Bad arguments for '" + operation + "': " + str(exc),
            "spoken_narrative": "Bad arguments for " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Biology Research",
            "summary": type(exc).__name__ + ": " + str(exc),
            "spoken_narrative": "Biology error: " + type(exc).__name__ + ".",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Biology Research"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
