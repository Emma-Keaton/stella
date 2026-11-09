import time
from typing import List, Dict

class MemoryHygiene:
    def __init__(self, max_age_days=30):
        self.max_age = max_age_days * 86400
    
    def write_policy(self, fact: Dict) -> bool:
        # Only keep facts with source and confidence
        if not fact.get("source") or fact.get("confidence", 0) < 0.5:
            return False
        return True
    
    def evict_stale(self, memory: List[Dict]) -> List[Dict]:
        now = time.time()
        return [m for m in memory if now - m.get("timestamp", now) < self.max_age]
    
    def resolve_contradictions(self, memory: List[Dict]) -> List[Dict]:
        # Keep latest per key
        latest = {}
        for m in memory:
            key = m.get("key")
            if key not in latest or m.get("timestamp",0) > latest[key].get("timestamp",0):
                latest[key] = m
        return list(latest.values())
