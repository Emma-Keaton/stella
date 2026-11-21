"""Feature: saas_metrics — SaaS metrics calculation.
MRR, ARR, churn rate, LTV, CAC, LTV:CAC ratio, NRR.
Source: claude-skills — Commercial & Finance division.
"""
from __future__ import annotations

from typing import Any

FEATURE_METADATA = {
    "name": "saas_metrics",
    "aliases": ["saas_metrics", "saas_kpis", "saas_metrics_skill", "mrr_churn", "ltv_cac", "saas_analytics"],
    "description": "Calculates key SaaS metrics: MRR, ARR, churn rate, LTV, CAC, LTV:CAC ratio, net revenue retention.",
    "triggers": ["saas metrics", "saas kpis", "mrr", "arr", "churn rate", "ltv", "cac", "ltv cac ratio", "net revenue retention", "nrr"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "enum": ["mrr_arr", "churn_rate", "ltv_cac", "nrr", "all", "sources"],
                "description": "One of: mrr_arr | churn_rate | ltv_cac | nrr | all | sources.",
            },
            "monthly_revenue": {
                "type": "NUMBER",
                "description": "Monthly recurring revenue (MRR).",
            },
            "customers": {
                "type": "INTEGER",
                "description": "Number of paying customers.",
            },
            "churn_rate": {
                "type": "NUMBER",
                "description": "Monthly churn rate as decimal (e.g., 0.05 for 5%).",
            },
            "arpu": {
                "type": "NUMBER",
                "description": "Average revenue per user per month.",
            },
            "cac": {
                "type": "NUMBER",
                "description": "Customer acquisition cost.",
            },
        },
        "required": ["operation"],
    },
    "source": "claude-skills",
    "division": "commercial_finance",
    "version": "1.0.0",
    "active": True,
}

_OPERATIONS = {}
_OPERATION_TITLES = {}
_ALIASES = {}

def _op_mrr_arr(kwargs: dict) -> dict:
    monthly_revenue = kwargs.get("monthly_revenue", 0)
    if monthly_revenue <= 0:
        return {"ok": False, "value": None, "error": "monthly_revenue is required and must be > 0 for mrr_arr"}
    arr = monthly_revenue * 12
    return {
        "ok": True,
        "value": {
            "operation": "mrr_arr",
            "monthly_revenue": monthly_revenue,
            "arr": arr,
            "formatted_mrr": f"${monthly_revenue:,.2f}/mo",
            "formatted_arr": f"${arr:,.2f}/yr",
        },
    }

def _op_churn_rate(kwargs: dict) -> dict:
    customers = kwargs.get("customers", 0)
    churn_rate = kwargs.get("churn_rate", 0)
    if not customers:
        return {"ok": False, "value": None, "error": "customers is required for churn_rate"}
    lost_customers = customers * churn_rate
    remaining = customers - lost_customers
    return {
        "ok": True,
        "value": {
            "operation": "churn_rate",
            "customers": customers,
            "churn_rate": churn_rate,
            "churn_rate_pct": f"{churn_rate * 100:.1f}%",
            "lost_customers": round(lost_customers, 1),
            "remaining_customers": round(remaining, 1),
        },
    }


def _op_ltv_cac(kwargs: dict) -> dict:
    arpu = kwargs.get("arpu", 0)
    churn_rate = kwargs.get("churn_rate", 0)
    cac = kwargs.get("cac", 0)
    if not arpu or not churn_rate or not cac:
        return {"ok": False, "value": None, "error": "arpu, churn_rate, and cac are required for ltv_cac"}
    ltv = arpu / churn_rate if churn_rate > 0 else 0
    ltv_cac_ratio = ltv / cac if cac > 0 else 0
    return {
        "ok": True,
        "value": {
            "operation": "ltv_cac",
            "arpu": arpu,
            "churn_rate": churn_rate,
            "cac": cac,
            "ltv": round(ltv, 2),
            "ltv_cac_ratio": round(ltv_cac_ratio, 2),
            "interpretation": "Healthy" if ltv_cac_ratio >= 3 else "Needs improvement" if ltv_cac_ratio >= 1 else "Unsustainable",
        },
    }

def _op_nrr(kwargs: dict) -> dict:
    starting_mrr = kwargs.get("monthly_revenue", 0)
    expansion = kwargs.get("expansion_revenue", 0)
    contraction = kwargs.get("contraction_revenue", 0)
    churn = kwargs.get("churn_revenue", 0)
    if not starting_mrr:
        return {"ok": False, "value": None, "error": "monthly_revenue is required for nrr"}
    ending_mrr = starting_mrr + expansion - contraction - churn
    nrr = (ending_mrr / starting_mrr) * 100 if starting_mrr > 0 else 0
    return {
        "ok": True,
        "value": {
            "operation": "nrr",
            "starting_mrr": starting_mrr,
            "expansion": expansion,
            "contraction": contraction,
            "churn": churn,
            "ending_mrr": ending_mrr,
            "nrr": round(nrr, 1),
            "nrr_pct": f"{nrr:.1f}%",
            "interpretation": "Growing" if nrr > 100 else "Shrinking",
        },
    }



def _op_all(kwargs: dict) -> dict:
    monthly_revenue = kwargs.get("monthly_revenue", 0)
    customers = kwargs.get("customers", 0)
    churn_rate = kwargs.get("churn_rate", 0)
    arpu = kwargs.get("arpu", 0)
    cac = kwargs.get("cac", 0)
    results = {}
    if monthly_revenue:
        results["mrr_arr"] = {
            "mrr": monthly_revenue,
            "arr": monthly_revenue * 12,
        }
    if customers and churn_rate:
        results["churn_rate"] = {
            "customers": customers,
            "churn_rate": churn_rate,
            "lost_customers": round(customers * churn_rate, 1),
        }
    if arpu and churn_rate and cac:
        ltv = arpu / churn_rate if churn_rate > 0 else 0
        results["ltv_cac"] = {
            "ltv": round(ltv, 2),
            "cac": cac,
            "ltv_cac_ratio": round(ltv / cac, 2) if cac > 0 else 0,
        }
    return {
        "ok": True,
        "value": {
            "operation": "all",
            "metrics": results,
        },
    }

def _op_sources(kwargs: dict) -> dict:
    return {
        "ok": True,
        "value": {
            "operation": "sources",
            "frameworks": ["SaaS Metrics Framework", "Bessemer Cloud Index", "KeyBanc SaaS Survey"],
            "metrics": ["MRR", "ARR", "Churn Rate", "LTV", "CAC", "LTV:CAC Ratio", "NRR"],
            "note": "SaaS metrics use industry-standard definitions.",
        },
    }


_OPERATIONS = {
    "mrr_arr": _op_mrr_arr,
    "churn_rate": _op_churn_rate,
    "ltv_cac": _op_ltv_cac,
    "nrr": _op_nrr,
    "all": _op_all,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "mrr_arr": "MRR/ARR Calculation",
    "churn_rate": "Churn Rate",
    "ltv_cac": "LTV:CAC Ratio",
    "nrr": "Net Revenue Retention",
    "all": "All SaaS Metrics",
    "sources": "SaaS Metrics Sources",
}

_ALIASES = {
    "mrr": "mrr_arr",
    "arr": "mrr_arr",
    "churn": "churn_rate",
    "ltv": "ltv_cac",
    "cac": "ltv_cac",
    "nrr": "nrr",
    "all_metrics": "all",
}

def execute(**kwargs) -> dict:
    """Run one SaaS metrics operation."""
    operation = (kwargs.get("operation") or "").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "SaaS Metrics",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown SaaS metrics operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "SaaS Metrics",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "SaaS Metrics",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"SaaS metrics error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "SaaS Metrics"),
        "summary": record.get("value", {}).get("recommendation", record.get("value", {}).get("interpretation", "Operation completed")),
        "spoken_narrative": record.get("value", {}).get("recommendation", record.get("value", {}).get("interpretation", "Operation completed")),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }

if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="mrr_arr", monthly_revenue=50000))