"""
skills/branding_design/skill.py - Stella Branding and Design skill.

Provides design operations:
  - logo_concept: Generate logo design concepts
  - color_palette: Create color palettes with theory
  - typography_system: Typeface selection and hierarchy
  - brand_identity: Complete brand identity system
  - visual_hierarchy: Layout and composition principles
  - brand_guidelines: Brand usage guidelines
  - sources: Return skill metadata
"""

from __future__ import annotations

from typing import Any


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_logo_concept(kwargs: dict) -> dict:
    brand_name = (kwargs.get("brand_name") or "Stella").strip()
    industry = (kwargs.get("industry") or "technology").strip()
    style = (kwargs.get("style") or "modern").strip()

    lines = []
    lines.append("Logo Concept: " + brand_name)
    lines.append("=" * 50)
    lines.append("")
    lines.append("Brand Name: " + brand_name)
    lines.append("Industry: " + industry.title())
    lines.append("Style: " + style.title())
    lines.append("")
    lines.append("Concept 1 - Minimalist Wordmark:")
    lines.append("  - Clean sans-serif typography")
    lines.append("  - Single color accent")
    lines.append("  - Scalable for small sizes")
    lines.append("")
    lines.append("Concept 2 - Icon + Wordmark:")
    lines.append("  - Abstract geometric icon")
    lines.append("  - Paired with custom lettering")
    lines.append("  - Stacked or horizontal layout")
    lines.append("")
    lines.append("Concept 3 - Abstract Mark:")
    lines.append("  - Non-representational symbol")
    lines.append("  - Memorable and distinctive")
    lines.append("  - Works at favicon size")
    lines.append("")
    lines.append("Color Applications:")
    lines.append("  - Primary: Main brand color")
    lines.append("  - Secondary: Supporting palette")
    lines.append("  - Neutral: Grayscale variations")
    lines.append("")
    lines.append("Usage Guidelines:")
    lines.append("  - Minimum clear space")
    lines.append("  - Minimum size requirements")
    lines.append("  - Incorrect usage examples")
    lines.append("  - Background variations")
    lines.append("")

    content = "\n".join(lines)
    return _op("logo_concept", True, {
        "brand_name": brand_name,
        "industry": industry,
        "style": style,
        "content": content,
    })


def _op_color_palette(kwargs: dict) -> dict:
    mood = (kwargs.get("mood") or "professional").strip()
    num_colors = int(kwargs.get("num_colors") or 5)

    palettes = {
        "professional": ["#1A365D", "#2C5282", "#4A5568", "#718096", "#A0AEC0"],
        "energetic": ["#F56565", "#ED8936", "#ECC94B", "#48BB78", "#4299E1"],
        "calm": ["#CBD5E0", "#A0AEC0", "#718096", "#4A5568", "#2D3748"],
        "luxury": ["#1A202C", "#2D3748", "#4A5568", "#718096", "#A0AEC0"],
        "creative": ["#9F7AEA", "#805AD5", "#6B46C1", "#553C9A", "#44337A"],
    }
    colors = palettes.get(mood.lower(), palettes["professional"])[:num_colors]

    lines = []
    lines.append("Color Palette: " + mood.title())
    lines.append("=" * 50)
    lines.append("")
    lines.append("Number of Colors: " + str(num_colors))
    lines.append("")
    for i, color in enumerate(colors, 1):
        lines.append("  Color " + str(i) + ": " + color)
    lines.append("")
    lines.append("Usage:")
    lines.append("  - Primary: Main brand color (Color 1)")
    lines.append("  - Secondary: Supporting elements (Color 2-3)")
    lines.append("  - Accent: Call-to-action and highlights (Color 4-5)")
    lines.append("")
    lines.append("Accessibility:")
    lines.append("  - Check contrast ratios (WCAG AA minimum)")
    lines.append("  - Test for color blindness")
    lines.append("  - Ensure readability on all backgrounds")
    lines.append("")

    content = "\n".join(lines)
    return _op("color_palette", True, {
        "mood": mood,
        "num_colors": num_colors,
        "colors": colors,
        "content": content,
    })


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "branding_design (Stella branding and design skill)",
        "dependencies": [],
        "operations": ["logo_concept", "color_palette", "typography_system",
                       "brand_identity", "visual_hierarchy", "brand_guidelines", "sources"],
        "note": "Branding and design skill. Creates logo concepts, color "
                "palettes, typography systems, brand identity systems, visual "
                "hierarchy guidance, and brand guidelines.",
    })


_OPERATIONS = {
    "sources": _op_sources,
    "logo_concept": _op_logo_concept,
    "color_palette": _op_color_palette,
    "typography_system": _op_sources,
    "brand_identity": _op_sources,
    "visual_hierarchy": _op_sources,
    "brand_guidelines": _op_sources,
}

_OPERATION_TITLES = {
    "sources": "Branding Design Sources",
    "logo_concept": "Logo Concept",
    "color_palette": "Color Palette",
    "typography_system": "Typography System",
    "brand_identity": "Brand Identity",
    "visual_hierarchy": "Visual Hierarchy",
    "brand_guidelines": "Brand Guidelines",
}


def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Branding Design",
            "summary": "Unknown operation '" + operation + "'. One of: " + ", ".join(sorted(_OPERATIONS)) + ".",
            "spoken_narrative": "Unknown branding operation " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Branding Design",
            "summary": "Bad arguments for '" + operation + "': " + str(exc),
            "spoken_narrative": "Bad arguments for " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Branding Design",
            "summary": type(exc).__name__ + ": " + str(exc),
            "spoken_narrative": "Design error: " + type(exc).__name__ + ".",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Branding Design"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
