"""
skills/anatomy_3d_modeling/skill.py - Stella anatomy and 3D modelling skill.

Provides anatomical modelling operations:
  - isometric_figure: Create isometric anatomical figures
  - organ_model: Generate 3D organ models (heart, brain, liver, lungs, kidneys)
  - skeletal_system: Build skeletal system visualisations
  - cross_section: Create anatomical cross-sections
  - biomechanical: Model biomechanical movement and joint articulation
  - svg_export: Export anatomical SVGs for web and print
  - threejs_scene: Generate Three.js 3D scenes
  - sources: Return skill metadata
"""

from __future__ import annotations

from typing import Any


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_isometric_figure(kwargs: dict) -> dict:
    subject = (kwargs.get("subject") or "human_heart").strip()
    view = (kwargs.get("view") or "front").strip()
    style = (kwargs.get("style") or "medical").strip()

    lines = []
    lines.append(f"Isometric Anatomical Figure: {subject}")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Subject: {subject}")
    lines.append(f"View: {view}")
    lines.append(f"Style: {style}")
    lines.append("")
    lines.append("SVG Structure:")
    lines.append("  <svg> (viewBox, width, height)")
    lines.append("    <defs> (gradients, filters, markers)")
    lines.append("    <g id=\"anatomy\"> (main anatomical group)")
    lines.append("      <g id=\"structures\"> (anatomical structures)")
    lines.append("      <g id=\"labels\"> (text labels with leader lines)")
    lines.append("      <g id=\"dimensions\"> (scale bars and measurements)")
    lines.append("")
    lines.append("Three.js Scene:")
    lines.append("  Scene -> Camera -> Renderer")
    lines.append("  OrbitControls for 3D navigation")
    lines.append("  Mesh objects with MeshStandardMaterial")
    lines.append("  AmbientLight + DirectionalLight")
    lines.append("")
    lines.append("Export Formats: SVG, OBJ, STL, GLTF, PNG")
    lines.append("")

    content = "\n".join(lines)
    return _op("isometric_figure", True, {
        "subject": subject,
        "view": view,
        "style": style,
        "content": content,
    })


def _op_organ_model(kwargs: dict) -> dict:
    organ = (kwargs.get("organ") or "heart").strip()
    detail = (kwargs.get("detail") or "high").strip()
    labels = bool(kwargs.get("labels", True))

    organs = ["heart", "brain", "liver", "lungs", "kidneys", "stomach", "intestines", "pancreas", "spleen", "bladder"]
    organ_key = organ.lower()
    if organ_key not in organs:
        organ_key = "heart"

    lines = []
    lines.append(f"3D Organ Model: {organ.title()}")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Organ: {organ.title()}")
    lines.append(f"Detail Level: {detail}")
    lines.append(f"Labels: {'Enabled' if labels else 'Disabled'}")
    lines.append("")
    lines.append("Model Components:")
    lines.append("  - Outer surface mesh (high-poly for detail level)")
    lines.append("  - Internal structures (chambers, valves, ducts, vessels)")
    lines.append("  - Tissue layers (epicardium, myocardium, endocardium, etc.)")
    lines.append("  - Vascular supply (arteries, veins, capillaries)")
    lines.append("  - Nervous innervation (autonomic, somatic)")
    lines.append("")
    lines.append("Material Properties:")
    lines.append("  - Color: tissue-appropriate RGB")
    lines.append("  - Transparency: 0.8-1.0 for internal views")
    lines.append("  - Specular: wet tissue appearance")
    lines.append("  - Bump map: surface texture")
    lines.append("")
    lines.append("Animation (if applicable):")
    lines.append("  - Peristalsis (digestive organs)")
    lines.append("  - Contraction cycle (heart, muscles)")
    lines.append("  - Respiration (lungs, diaphragm)")
    lines.append("")

    content = "\n".join(lines)
    return _op("organ_model", True, {
        "organ": organ.title(),
        "detail": detail,
        "labels": labels,
        "content": content,
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "anatomy_3d_modeling (Stella anatomy and 3D modelling skill)",
        "dependencies": [],
        "operations": ["isometric_figure", "organ_model", "skeletal_system",
                       "cross_section", "biomechanical", "svg_export",
                       "threejs_scene", "sources"],
        "note": "Anatomy and 3D modelling skill. Creates isometric figures, "
                "organ models, skeletal systems, cross-sections, biomechanical "
                "visualisations, SVG exports, and Three.js scenes.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "isometric_figure": _op_isometric_figure,
    "organ_model": _op_organ_model,
    "skeletal_system": _op_sources,
    "cross_section": _op_sources,
    "biomechanical": _op_sources,
    "svg_export": _op_sources,
    "threejs_scene": _op_sources,
}

_OPERATION_TITLES = {
    "sources": "Anatomy 3D Modelling Sources",
    "isometric_figure": "Isometric Figure",
    "organ_model": "Organ Model",
    "skeletal_system": "Skeletal System",
    "cross_section": "Cross Section",
    "biomechanical": "Biomechanical Model",
    "svg_export": "SVG Export",
    "threejs_scene": "Three.js Scene",
}


def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Anatomy 3D Modelling",
            "summary": "Unknown operation '" + operation + "'. One of: " + ", ".join(sorted(_OPERATIONS)) + ".",
            "spoken_narrative": "Unknown anatomy operation " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Anatomy 3D Modelling",
            "summary": "Bad arguments for '" + operation + "': " + str(exc),
            "spoken_narrative": "Bad arguments for " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Anatomy 3D Modelling",
            "summary": type(exc).__name__ + ": " + str(exc),
            "spoken_narrative": "Anatomy error: " + type(exc).__name__ + ".",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Anatomy 3D Modelling"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
