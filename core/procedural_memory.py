import json, os, time
from pathlib import Path

TRACE_DIR = Path("evals/traces")
TRACE_DIR.mkdir(parents=True, exist_ok=True)

class ProceduralMemory:
    def store_trace(self, goal, tools, outcome, duration):
        trace = {
            "goal": goal,
            "tools": tools,
            "outcome": outcome,
            "duration": duration,
            "timestamp": time.time()
        }
        path = TRACE_DIR / f"{int(time.time()*1000)}.json"
        path.write_text(json.dumps(trace))
        return path
    
    def retrieve(self, task_similarity, top_k=5):
        # Simple similarity by goal substring
        matches = []
        for p in TRACE_DIR.glob("*.json"):
            data = json.loads(p.read_text())
            if task_similarity.lower() in data["goal"].lower():
                matches.append(data)
        return matches[:top_k]
