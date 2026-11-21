"""Feature: pricing_strategy — Pricing strategy recommendations.
Cost-plus, value-based, competitive, penetration, skimming, tiered, freemium.
Source: claude-skills — Commercial & Finance division.
"""
from __future__ import annotations

from typing import Any

FEATURE_METADATA = {
    "name": "pricing_strategy",
    "aliases": ["pricing_strategy", "pricing", "price_strategy", "pricing_model", "pricing_strategy_skill"],
    "description": "Recommends pricing strategies: cost-plus, value-based, competitive, penetration, skimming, tiered, freemium.",
    "triggers": ["pricing", "price strategy", "pricing strategy", "pricing model", "cost-plus", "value-based pricing", "competitive pricing", "penetration pricing", "skimming", "tiered pricing", "freemium"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "operation": {
                "type": "STRING",
                "enum": ["cost_plus", "value_based", "competitive", "penetration", "skimming", "tiered", "freemium", "all", "sources"],
                "description": "One of: cost_plus | value_based | competitive | penetration | skimming | tiered | freemium | all | sources.",
            },
            "cost": {
                "type": "NUMBER",
                "description": "Unit cost of product/service.",
            },
            "margin": {
                "type": "NUMBER",
                "description": "Desired profit margin as decimal (e.g., 0.30 for 30%).",
            },
            "value_perceived": {
                "type": "NUMBER",
                "description": "Perceived value to customer.",
            },
            "competitor_price": {
                "type": "NUMBER",
                "description": "Competitor price for similar product.",
            },
            "market_position": {
                "type": "STRING",
                "description": "Market position: premium | mid-market | budget.",
            },
        },
        "required": ["operation"],
    },
    "source": "claude-skills",
    "division": "commercial_finance",
    "version": "1.0.0",
    "active": True,
}

def _op_cost_plus(kwargs: dict) -> dict:
    cost = kwargs.get("cost", 0)
    margin = kwargs.get("margin", 0.3)
    if not cost:
        return {"ok": False, "value": None, "error": "cost is required for cost_plus"}
    price = cost * (1 + margin)
    profit = price - cost
    return {
        "ok": True,
        "value": {
            "operation": "cost_plus",
            "cost": cost,
            "margin": margin,
            "price": round(price, 2),
            "profit": round(profit, 2),
            "formatted_price": f"${price:,.2f}",
        },
    }

def _op_value_based(kwargs: dict) -> dict:
    value_perceived = kwargs.get("value_perceived", 0)
    margin = kwargs.get("margin", 0.5)
    if not value_perceived:
        return {"ok": False, "value": None, "error": "value_perceived is required for value_based"}
    price = value_perceived * margin
    return {
        "ok": True,
        "value": {
            "operation": "value_based",
            "value_perceived": value_perceived,
            "margin": margin,
            "price": round(price, 2),
            "formatted_price": f"${price:,.2f}",
        },
    }

_OPERATIONS = {}
_OPERATION_TITLES = {}

def _op_competitive(kwargs: dict) -> dict:
    competitor_price = kwargs.get("competitor_price", 0)
    market_position = kwargs.get("market_position", "mid-market")
    if not competitor_price:
        return {"ok": False, "value": None, "error": "competitor_price is required for competitive"}
    adjustments = {"premium": 1.1, "mid-market": 1.0, "budget": 0.9}
    factor = adjustments.get(market_position, 1.0)
    price = competitor_price * factor
    return {
        "ok": True,
        "value": {
            "operation": "competitive",
            "competitor_price": competitor_price,
            "market_position": market_position,
            "price": round(price, 2),
            "formatted_price": f"${price:,.2f}",
        },
    }

def _op_penetration(kwargs: dict) -> dict:
    competitor_price = kwargs.get("competitor_price", 0)
    if not competitor_price:
        return {"ok": False, "value": None, "error": "competitor_price is required for penetration"}
    price = competitor_price * 0.85
    return {
        "ok": True,
        "value": {
            "operation": "penetration",
            "competitor_price": competitor_price,
            "price": round(price, 2),
            "discount_pct": "15%",
            "formatted_price": f"${price:,.2f}",
            "strategy": "Price below competitors to gain market share",
        },
    }

def _op_skimming(kwargs: dict) -> dict:
    competitor_price = kwargs.get("competitor_price", 0)
    if not competitor_price:
        return {"ok": False, "value": None, "error": "competitor_price is required for skimming"}
    price = competitor_price * 1.4
    return {
        "ok": True,
        "value": {
            "operation": "skimming",
            "competitor_price": competitor_price,
            "price": round(price, 2),
            "premium_pct": "40%",
            "formatted_price": f"${price:,.2f}",
            "strategy": "Price above competitors for premium positioning",
        },
    }

def _op_tiered(kwargs: dict) -> dict:
    base_price = kwargs.get("competitor_price", 0)
    if not base_price:
        return {"ok": False, "value": None, "error": "competitor_price (base) is required for tiered"}
    return {
        "ok": True,
        "value": {
            "operation": "tiered",
            "tiers": [
                {"name": "Basic", "price": round(base_price * 0.7, 2)},
                {"name": "Standard", "price": round(base_price, 2)},
                {"name": "Pro", "price": round(base_price * 1.5, 2)},
                {"name": "Enterprise", "price": round(base_price * 2.5, 2)},
            ],
        },
    }

def _op_freemium(kwargs: dict) -> dict:
    base_price = kwargs.get("competitor_price", 0)
    if not base_price:
        return {"ok": False, "value": None, "error": "competitor_price is required for freemium"}
    return {
        "ok": True,
        "value": {
            "operation": "freemium",
            "free_tier": {"price": 0, "features": ["Basic features"]},
            "paid_tier": {"price": round(base_price, 2), "features": ["Premium features", "Priority support"]},
            "upgrade_prompt": f"Upgrade for ${base_price:,.2f}/mo",
        },
    }

_ALIASES = {}


def _op_all(kwargs: dict) -> dict:
    cost = kwargs.get("cost", 0)
    margin = kwargs.get("margin", 0.3)
    value_perceived = kwargs.get("value_perceived", 0)
    competitor_price = kwargs.get("competitor_price", 0)
    results = {}
    if cost:
        price = cost * (1 + margin)
        results["cost_plus"] = {"price": round(price, 2), "profit": round(price - cost, 2)}
    if value_perceived:
        results["value_based"] = {"price": round(value_perceived * margin, 2)}
    if competitor_price:
        results["competitive"] = {"price": round(competitor_price, 2)}
        results["penetration"] = {"price": round(competitor_price * 0.85, 2)}
        results["skimming"] = {"price": round(competitor_price * 1.4, 2)}
    return {
        "ok": True,
        "value": {
            "operation": "all",
            "strategies": results,
        },
    }

def _op_sources(kwargs: dict) -> dict:
    return {
        "ok": True,
        "value": {
            "operation": "sources",
            "frameworks": ["Cost-Plus Pricing", "Value-Based Pricing", "Competitive Pricing", "Penetration Pricing", "Price Skimming", "Tiered Pricing", "Freemium"],
            "note": "Pricing strategies based on standard marketing frameworks.",
        },
    }


_OPERATIONS = {
    "cost_plus": _op_cost_plus,
    "value_based": _op_value_based,
    "competitive": _op_competitive,
    "penetration": _op_penetration,
    "skimming": _op_skimming,
    "tiered": _op_tiered,
    "freemium": _op_freemium,
    "all": _op_all,
    "sources": _op_sources,
}

_OPERATION_TITLES = {
    "cost_plus": "Cost-Plus Pricing",
    "value_based": "Value-Based Pricing",
    "competitive": "Competitive Pricing",
    "penetration": "Penetration Pricing",
    "skimming": "Price Skimming",
    "tiered": "Tiered Pricing",
    "freemium": "Freemium",
    "all": "All Pricing Strategies",
    "sources": "Pricing Sources",
}

_ALIASES = {
    "cost-plus": "cost_plus",
    "value-based": "value_based",
    "penetration_pricing": "penetration",
    "price_skimming": "skimming",
    "tiered_pricing": "tiered",
}

def execute(**kwargs) -> dict:
    """Run one pricing strategy operation."""
    operation = (kwargs.get("operation") or "").strip().lower()
    operation = _ALIASES.get(operation, operation)
    handler = _OPERATIONS.get(operation)
    if handler is None:
        return {
            "title": "Pricing Strategy",
            "summary": f"Unknown operation '{operation}'. One of: {', '.join(sorted(_OPERATIONS))}.",
            "spoken_narrative": f"Unknown pricing strategy operation {operation}.",
            "ok": False,
            "operation": operation,
        }
    try:
        record = handler(kwargs)
    except TypeError as exc:
        return {
            "title": "Pricing Strategy",
            "summary": f"Bad arguments for '{operation}': {exc}",
            "spoken_narrative": f"Bad arguments for {operation}.",
            "ok": False,
            "operation": operation,
        }
    except Exception as exc:
        return {
            "title": "Pricing Strategy",
            "summary": f"{type(exc).__name__}: {exc}",
            "spoken_narrative": f"Pricing strategy error: {type(exc).__name__}.",
            "ok": False,
            "operation": operation,
        }
    return {
        "title": _OPERATION_TITLES.get(operation, "Pricing Strategy"),
        "summary": record.get("value", {}).get("price", "Operation completed"),
        "spoken_narrative": record.get("value", {}).get("price", "Operation completed"),
        "operation": operation,
        "ok": bool(record.get("ok")),
        "record": record,
    }

if __name__ == "__main__":  # pragma: no cover
    import pprint
    pprint.pprint(execute(operation="cost_plus", cost=100, margin=0.3))