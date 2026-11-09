from __future__ import annotations
from typing import Any, Dict
import os, requests, importlib.util, pathlib

FEATURE_METADATA = {
    "name": "hummingbot_strategy_learn",
    "description": "Analyse backtest results and ask Stella's internal model for strategy improvements.",
    "triggers": ["learn strategy"],
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "backtest_result": {"type": "OBJECT", "description": "Result dict from hummingbot_backtest"},
            "strategy": {"type": "STRING", "description": "Strategy name"}
        },
        "required": ["backtest_result", "strategy"]
    }
}

def run(params: Dict[str, Any]) -> Dict[str, Any]:
    backtest = params.get("backtest_result")
    strategy = params.get("strategy")
    if not backtest or not strategy:
        return {"ok": False, "error": "Missing backtest_result or strategy"}
    # Prepare prompt for internal model
    prompt = (
        f"Given the following Hummingbot backtest output for strategy '{strategy}':\n"
        f"{json.dumps(backtest, indent=2)}\n"
        "Provide concrete suggestions to improve profitability, reduce drawdown, and adjust parameters."
    )
    model_endpoint = os.getenv("STELLA_MODEL_ENDPOINT", "http://localhost:8000/model/chat")
    try:
        r = requests.post(model_endpoint, json={"prompt": prompt}, timeout=60)
        r.raise_for_status()
        suggestion = r.json().get("response") or r.json().get("text") or str(r.json())
        return {"ok": True, "strategy": strategy, "suggestion": suggestion}
    except Exception as e:
        return {"ok": False, "error": str(e)}