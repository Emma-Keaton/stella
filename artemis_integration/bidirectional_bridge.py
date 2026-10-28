"""
Bidirectional Bridge for Stella and Android
Enables mobile-as-host and PC-to-mobile communication
"""

import asyncio
import websockets
import json
from typing import Dict, Any

class BidirectionalBridge:
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.clients = set()
        self.device_manager = None
    
    async def start_server(self):
        async with websockets.serve(self.handle_client, self.host, self.port):
            print(f"Bidirectional bridge started on {self.host}:{self.port}")
            await asyncio.Future()
    
    async def handle_client(self, websocket):
        self.clients.add(websocket)
        try:
            async for message in websocket:
                data = json.loads(message)
                response = await self.process_command(data)
                await websocket.send(json.dumps(response))
        finally:
            self.clients.remove(websocket)
    
    async def process_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        action = command.get("action")
        params = command.get("params", {})
        
        if action == "device_control":
            # Execute device control via Artemis
            result = self.execute_device_control(params)
            return {"status": "success", "result": result}
        elif action == "power_share":
            return {"status": "success", "result": "power sharing enabled"}
        elif action == "get_status":
            return {"status": "success", "result": {"bridge_active": True}}
        
        return {"status": "error", "message": "unknown action"}
    
    def execute_device_control(self, params: Dict[str, Any]) -> str:
        # Integrate with ActionExecutor
        return "device controlled"
    
    async def broadcast_to_clients(self, message: Dict[str, Any]):
        if self.clients:
            await asyncio.gather(
                *[client.send(json.dumps(message)) for client in self.clients]
            )
