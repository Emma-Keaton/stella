class FrontierRouter:
    def __init__(self):
        self.local_default = True
        self.cost_policy = {"local": 0, "frontier": 1}
    
    def triage(self, task: dict) -> str:
        # Task triage: local by default, frontier on opt-in or complexity
        if not self.local_default:
            return "frontier"
        complexity = task.get("complexity", 0)
        requires_frontier = task.get("requires_frontier", False)
        if requires_frontier or complexity > 0.8:
            return "frontier"
        return "local"
    
    def route(self, task):
        mode = self.triage(task)
        if mode == "local":
            return {"provider": "local", "cost": self.cost_policy["local"]}
        return {"provider": "frontier", "cost": self.cost_policy["frontier"]}
