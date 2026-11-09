"""
skills/math_research/skill.py - Stella Mathematics Research skill.

Provides real mathematics operations backed by sympy and numpy/scipy:
  - equation_solver: Solve algebraic equations symbolically (sympy)
  - calculus: Differentiate / integrate symbolically (sympy)
  - statistics: Descriptive statistics (mean, median, std dev) via statistics/statistics
  - linear_algebra: Matrix operations via numpy/scipy
  - differential_equations: ODE solutions via sympy.dsolve
  - number_theory: Primes, GCD, modular arithmetic via sympy
  - geometry: Geometric calculations
  - sources: Return skill metadata

All operations run locally with no API key. Degrades gracefully if sympy/numpy
are unavailable.
"""

from __future__ import annotations

from typing import Any

try:
    import sympy as sp
    _HAS_SYMPY = True
except Exception:  # pragma: no cover
    _HAS_SYMPY = False

try:
    import numpy as np
    _HAS_NUMPY = True
except Exception:  # pragma: no cover
    _HAS_NUMPY = False


def _op(operation: str, ok: bool, value=None, error: str = "") -> dict:
    return {"operation": operation, "ok": ok, "value": value, "error": error}


def _op_equation_solver(kwargs: dict) -> dict:
    equation = (kwargs.get("equation") or "").strip()
    variable = (kwargs.get("variable") or "x").strip()
    if not equation:
        return _op("equation_solver", False, None, "Provide an equation (equation=...).")
    if not _HAS_SYMPY:
        return _op("equation_solver", False, None, "sympy not installed: pip install sympy")
    try:
        x = sp.symbols(variable)
        expr = sp.sympify(equation)
        if "=" in equation:
            lhs, rhs = equation.split("=", 1)
            eq = sp.Eq(sp.sympify(lhs), sp.sympify(rhs))
            sols = sp.solve(eq, x)
        else:
            sols = sp.solve(sp.Eq(expr, 0), x)
        return _op("equation_solver", True, {
            "equation": equation,
            "variable": variable,
            "solutions": [str(s) for s in sols],
            "content": "Solutions for " + variable + ": " + ", ".join(str(s) for s in sols),
        })
    except Exception as exc:
        return _op("equation_solver", False, None, str(exc))


def _op_calculus(kwargs: dict) -> dict:
    operation_type = (kwargs.get("operation_type") or "differentiate").strip()
    function = (kwargs.get("function") or "x**2").strip()
    variable = (kwargs.get("variable") or "x").strip()
    if not _HAS_SYMPY:
        return _op("calculus", False, None, "sympy not installed: pip install sympy")
    try:
        x = sp.symbols(variable)
        expr = sp.sympify(function)
        if operation_type.lower() == "differentiate":
            result = sp.diff(expr, x)
        elif operation_type.lower() == "integrate":
            result = sp.integrate(expr, x)
        else:
            return _op("calculus", False, None, "operation_type must be 'differentiate' or 'integrate'")
        return _op("calculus", True, {
            "operation_type": operation_type,
            "function": function,
            "variable": variable,
            "result": str(result),
            "content": f"d/d{variable} [{function}] = {result}" if operation_type.lower() == "differentiate" else f"integral [{function}] d{variable} = {result}",
        })
    except Exception as exc:
        return _op("calculus", False, None, str(exc))


def _op_statistics(kwargs: dict) -> dict:
    data = (kwargs.get("data") or "1,2,3,4,5").strip()
    test_type = (kwargs.get("test_type") or "descriptive").strip()
    try:
        values = [float(x.strip()) for x in data.split(",")]
    except ValueError:
        return _op("statistics", False, None, "data must be comma-separated numbers")
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std_dev = variance ** 0.5
    sorted_vals = sorted(values)
    median = sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
    lines = []
    lines.append(f"Statistical Analysis: {test_type.title()}")
    lines.append(f"Sample Size: {n}")
    lines.append(f"Mean: {mean:.4f}")
    lines.append(f"Median: {median:.4f}")
    lines.append(f"Variance: {variance:.4f}")
    lines.append(f"Standard Deviation: {std_dev:.4f}")
    lines.append(f"Range: {min(values):.4f} - {max(values):.4f}")
    content = "\n".join(lines)
    return _op("statistics", True, {
        "data": values,
        "test_type": test_type,
        "mean": mean,
        "median": median,
        "variance": variance,
        "std_dev": std_dev,
        "content": content,
    })


def _op_linear_algebra(kwargs: dict) -> dict:
    if not _HAS_NUMPY:
        return _op("linear_algebra", False, None, "numpy not installed")
    import numpy as np
    matrix_str = (kwargs.get("matrix") or "1,2;3,4").strip()
    operation_type = (kwargs.get("operation_type") or "det").strip()
    try:
        rows = [r.strip() for r in matrix_str.split(";")]
        mat = np.array([[float(v) for v in row.split(",")] for r in rows], dtype=float)
    except Exception as exc:
        return _op("linear_algebra", False, None, f"Invalid matrix: {exc}")
    try:
        if operation_type.lower() == "det":
            result = float(np.linalg.det(mat))
        elif operation_type.lower() == "inv":
            result = np.linalg.inv(mat).tolist()
        elif operation_type.lower() == "eig":
            w, v = np.linalg.eig(mat)
            result = {"eigenvalues": w.tolist(), "eigenvectors": v.tolist()}
        elif operation_type.lower() == "inv":
            result = np.linalg.inv(mat).tolist()
        else:
            return _op("linear_algebra", False, None, "operation_type: det|inv|eig")
        return _op("linear_algebra", True, {
            "operation_type": operation_type,
            "matrix": mat.tolist(),
            "result": result,
            "content": str(result),
        })
    except Exception as exc:
        return _op("linear_algebra", False, None, str(exc))


def _op_differential_equations(kwargs: dict) -> dict:
    if not _HAS_SYMPY:
        return _op("differential_equations", False, None, "sympy not installed")
    equation = (kwargs.get("equation") or "Derivative(x(t), t) - k*x(t)").strip()
    try:
        t = sp.symbols("t")
        x = sp.Function("x")
        k = sp.symbols("k", positive=True)
        ode = sp.Eq(sp.diff(x(t), t), sp.sympify(equation.split("=")[1]) if "=" in equation else sp.sympify(equation))
        sol = sp.dsolve(ode)
        return _op("differential_equations", True, {
            "equation": equation,
            "solution": str(sol),
            "content": f"ODE solution: {sol}",
        })
    except Exception as exc:
        return _op("differential_equations", False, None, str(exc))


def _op_number_theory(kwargs: dict) -> dict:
    if not _HAS_SYMPY:
        return _op("number_theory", False, None, "sympy not installed")
    n = int(kwargs.get("n") or 100)
    try:
        primes = list(sp.primerange(2, n + 1))
        gcd_val = sp.gcd(*[int(x) for x in (kwargs.get("nums") or "12,18").split(",")])
        return _op("number_theory", True, {
            "primes_up_to_n": primes[:50],
            "prime_count": len(primes),
            "gcd": int(gcd_val),
            "content": f"Primes up to {n}: {primes[:20]}... (total {len(primes)})",
        })
    except Exception as exc:
        return _op("number_theory", False, None, str(exc))


def _op_geometry(kwargs: dict) -> dict:
    shape = (kwargs.get("shape") or "circle").strip()
    radius = float(kwargs.get("radius") or 1.0)
    lines = []
    lines.append(f"Geometry: {shape.title()}")
    lines.append("=" * 40)
    if shape.lower() == "circle":
        area = math.pi * radius ** 2
        circ = 2 * math.pi * radius
        lines.append(f"Radius: {radius}")
        lines.append(f"Area: {area:.4f}")
        lines.append(f"Circumference: {circ:.4f}")
        content = "\n".join(lines)
        return _op("geometry", True, {
            "shape": "circle", "radius": radius,
            "area": area, "circumference": circ, "content": content,
        })
    return _op("geometry", False, None, "shape: circle (rectangle, triangle coming)")


import math

_OPERATIONS = {
    "sources": _op_sources if False else None,
    "equation_solver": _op_equation_solver,
    "calculus": _op_calculus,
    "statistics": _op_statistics,
    "linear_algebra": _op_linear_algebra,
    "differential_equations": _op_differential_equations,
    "number_theory": _op_number_theory,
    "geometry": _op_geometry,
}


def _op_sources(kwargs: dict) -> dict:
    return _op("sources", True, {
        "source": "math_research (Stella mathematics research skill)",
        "dependencies": ["sympy", "numpy"],
        "operations": list(_OPERATIONS.keys() - {"sources"}),
        "note": "Mathematics research skill backed by sympy and numpy. All local, no API key.",
    })


_OPERATIONS["sources"] = _op_sources

_OPERATION_TITLES = {
    "sources": "Math Research Sources",
    "equation_solver": "Equation Solver",
    "calculus": "Calculus",
    "statistics": "Statistics",
    "linear_algebra": "Linear Algebra",
    "differential_equations": "Differential Equations",
    "number_theory": "Number Theory",
    "geometry": "Geometry",
}


def execute(**kwargs) -> dict:
    operation = (kwargs.get("operation") or "sources").strip().lower()
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Math Research",
            "summary": "Unknown operation '" + operation + "'. One of: " + ", ".join(sorted(_OPERATIONS)) + ".",
            "spoken_narrative": "Unknown math operation " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Math Research",
            "summary": "Bad arguments for '" + operation + "': " + str(exc),
            "spoken_narrative": "Bad arguments for " + operation + ".",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Math Research",
            "summary": type(exc).__name__ + ": " + str(exc),
            "spoken_narrative": "Math error: " + type(exc).__name__ + ".",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Math Research"),
        "summary": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "spoken_narrative": str((record.get("value") or {}).get("content", record.get("error", "")))[:200],
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }


if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="sources"))
