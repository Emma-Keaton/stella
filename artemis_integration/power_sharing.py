"""
Processing power sharing protocol for Stella mobile devices
Enables compute offload between devices
"""

class ProcessingPowerSharingProtocol:
    def __init__(self):
        self.participants = {}
    
    def register_device(self, device_id: str, cpu_cores: int, ram_gb: float, load: float = 0.0):
        self.participants[device_id] = {
            "cpu_cores": cpu_cores,
            "ram_gb": ram_gb,
            "load": load,
            "status": "idle",
            "available_compute": cpu_cores * (1 - load)
        }
    
    def request_compute(self, from_device: str, to_device: str, compute_units: float) -> bool:
        if from_device not in self.participants or to_device not in self.participants:
            return False
        donor = self.participants[from_device]
        if donor["available_compute"] >= compute_units:
            donor["available_compute"] -= compute_units
            donor["load"] += compute_units / donor["cpu_cores"]
            self.participants[from_device] = donor
            # Orchestrate job offload via bidirectional bridge
            return True
        return False
    
    def defer_job(self, job_id: str, from_device: str, to_device: str, job_spec: dict) -> bool:
        # Defer heavy computation to stronger device
        return self.request_compute(from_device, to_device, job_spec.get("compute_units", 1.0))
    
    def get_compute_status(self) -> dict:
        return {k: v for k, v in self.participants.items()}
