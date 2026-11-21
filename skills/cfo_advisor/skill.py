"""Feature: cfo_advisor — CFO-level financial advisory.
Budgeting, forecasting, cash flow, financial planning, and capital allocation decisions.
Source: agency-agents — Finance division.
"""
from __future__ import annotations

from typing import Any

FEATURE_METADATA = {
    "name": "cfo_advisor",
    "aliases": ["cfo advisor", "cfo advice", "financial advice", "budget advice", "cash flow", "finance advisor"],
    "description": "CFO-level financial advisory covering budgeting, forecasting, cash flow, financial planning, and capital allocation decisions.",
    "triggers": ["cfo advice", "financial advice", "budget advice", "cash flow", "financial planning", "capital allocation", "finance advisor"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "description": "One of: budget | forecast | cashflow | investment | report | sources.",
            },
            "topic": {
                "type": "STRING",
                "description": "Financial topic or area of focus.",
            },
            "amount": {
                "type": "NUMBER",
                "description": "Amount or budget figure.",
            },
            "period": {
                "type": "STRING",
                "description": "Time period: monthly | quarterly | yearly.",
            },
        },
        "required": ["operation"],
    },
    "source": "agency-agents",
    "division": "c_level",
    "version": "1.0.0",
    "active": True,
}

_OPERATIONS = {}
_OPERATION_TITLES = {}
_ALIASES = {}

def _op_budget(kwargs: dict) -> dict:
    topic = kwargs.get("topic", "")
    amount = kwargs.get("amount", 0)
    period = kwargs.get("period", "monthly")

    recommendation = f"Budget guidance for {topic or 'financial planning'}: "
    if amount:
        recommendation += f"Budget of ${amount:,.2f} for {period}. Review variances monthly, maintain 3-6 months of runway."
    else:
        recommendation += "Review variances monthly, maintain 3-6 months of runway."

    return {
        "ok": True,
        "value": {
            "operation": "budget",
            "topic": topic,
            "amount": amount,
            "period": period,
            "recommendation": recommendation,
        },
    }

def _op_forecast(kwargs: dict) -> dict:
    topic = kwargs.get("topic", "")

    return {
        "ok": True,
        "value": {
            "operation": "forecast",
            "topic": topic,
            "method": "Bottom-up with top-down validation",
            "horizon": "12 months",
            "reviewCadence": "Monthly",
            "recommendation": "Update forecasts monthly based on actuals vs. plan variance.",
        },
    }

def _op_cashflow(kwargs: dict) -> dict:
    topic = kwargs.get("topic", "")

    return {
        "ok": True,
        "value": {
            "operation": "cashflow",
            "topic": topic,
            "recommendation": "Monitor weekly cash flow, maintain 13-week cash flow forecast, prioritize collections and manage payables.",
        },
    }

def _op_investment(kwargs: dict) -> dict:
    topic = kwargs.get("topic", "")
    amount = kwargs.get("amount", 0)

    return {
        "ok": True,
        "value": {
            "operation": "investment",
            "topic": topic,
            "amount": amount,
            "recommendation": f"Evaluate investment in {topic or 'opportunity'}: assess ROI, payback period, and risk before committing capital.",
        },
    }

def _op_report(kwargs: dict) -> dict:
    topic = kwargs.get("topic", "")

    return {
        "ok": True,
        "value": {
            "operation": "report",
            "topic": topic,
            "sections": ["Executive summary", "P&L review", "Cash flow statement", "Balance sheet", "Variance analysis", "Key metrics"],
            "recommendation": "Distribute monthly financial package to leadership team within 10 business days of month close.",
        },
    }

_OPERATIONS = {
    "budget": _op_budget,
    "forecast": _op_forecast,
    "cashflow": _op_cashflow,
    "investment": _op_investment,
    "report": _op_report,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "budget": "Budget Advice",
    "forecast": "Financial Forecast",
    "cashflow": "Cash Flow Management",
    "investment": "Investment Evaluation",
    "report": "Financial Report",
    "sources": "CFO Advisory Sources",
}

_ALIASES = {
    "budgeting": "budget",
    "forecasting": "forecast",
    "cash_flow": "cashflow",
    "invest": "investment",
    "reporting": "report",
}

def execute(**kwargs) -> dict:
    """Run one CFO advisor operation."""
    operation = (kwargs.get("operation") or "").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "CFO Advisor",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown CFO advisor operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "CFO Advisor",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "CFO Advisor",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"CFO advisor error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "CFO Advisor"),
        "summary": record.get("value", {}).get("recommendation", "Operation completed"),
        "spoken_narrative": record.get("value", {}).get("recommendation", "Operation completed"),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }

if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="budget", topic="Q1 marketing", amount=50000, period="quarterly"))

def _op_sources(kwargs: dict) -> dict:
    return {
        "ok": True,
        "value": {
            "operation": "sources",
            "frameworks": ["DCF", "Zero-based budgeting", "Rolling forecasts", "DuPont analysis"],
            "sources": ["GAAP financial statements", "SEC filings", "Industry benchmarks", "Management accounts"],
            "note": "CFO advisory uses corporate finance frameworks and publicly available financial data.",
        },
    }
