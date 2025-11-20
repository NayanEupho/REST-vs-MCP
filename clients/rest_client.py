import httpx
import time
import asyncio
import json
from typing import Dict, Any, List

from .network_sim import NetworkSimulator

class RestClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=30.0)
        self.async_client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
        self.network_sim = NetworkSimulator()
        
    def set_network_conditions(self, latency_ms: int, packet_loss_rate: float, bandwidth_mbps: float = 0.0):
        self.network_sim.set_conditions(latency_ms, packet_loss_rate, bandwidth_mbps)

    def ping(self) -> float:
        start = time.perf_counter()
        response = self.client.get("/status")
        response.raise_for_status()
        end = time.perf_counter()
        return (end - start) * 1000

    async def ping_async(self) -> tuple[float, int]:
        await self.network_sim.simulate_network()
        start = time.perf_counter()
        response = await self.async_client.get("/status")
        response.raise_for_status()
        end = time.perf_counter()
        bytes_sent = len(response.content) + 100 # Approx headers
        return (end - start) * 1000, bytes_sent

    def echo(self, message: str) -> float:
        start = time.perf_counter()
        response = self.client.post("/echo", json={"message": message})
        response.raise_for_status()
        end = time.perf_counter()
        return (end - start) * 1000

    async def echo_async(self, message: str) -> float:
        await self.network_sim.simulate_network()
        start = time.perf_counter()
        await self.async_client.post("/echo", json={"message": message})
        end = time.perf_counter()
        return (end - start) * 1000

    def calculate(self, operation: str, a: float, b: float) -> float:
        start = time.perf_counter()
        response = self.client.post("/tools/calculate", json={"operation": operation, "a": a, "b": b})
        response.raise_for_status()
        end = time.perf_counter()
        return (end - start) * 1000

    def get_context(self, size: int) -> float:
        start = time.perf_counter()
        response = self.client.get(f"/context?size={size}")
        response.raise_for_status()
        end = time.perf_counter()
        return (end - start) * 1000

    async def chat_turn(self, history: List[Dict[str, str]], message: str) -> Dict[str, Any]:
        start = time.perf_counter()
        
        payload = {
            "message": message,
            "history": history
        }
        
        # Simulate upload bandwidth
        await self.network_sim.simulate_transfer(len(json.dumps(payload)))
        
        response = await self.async_client.post("/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        
        # Simulate download bandwidth
        await self.network_sim.simulate_transfer(len(json.dumps(data)))
        
        end = time.perf_counter()
        
        return {
            "latency_ms": (end - start) * 1000,
            "response": data["response"],
            "bytes_sent": len(json.dumps(payload))
        }

    def run_task_polling(self, complexity: int) -> Dict[str, Any]:
        start = time.perf_counter()
        bytes_sent = 0
        import json
        
        # 1. Start Task
        payload = {"complexity": complexity}
        resp = self.client.post("/tasks/generate", json=payload)
        bytes_sent += len(json.dumps(payload)) + 100 # + headers
        task_id = resp.json()["task_id"]
        
        polls = 0
        while True:
            polls += 1
            time.sleep(0.1) # Poll interval
            status_resp = self.client.get(f"/tasks/{task_id}")
            bytes_sent += 100 # headers
            status = status_resp.json()
            
            if status["status"] == "completed":
                break
                
        end = time.perf_counter()
        return {
            "latency_ms": (end - start) * 1000,
            "polls": polls,
            "bytes_sent": bytes_sent
        }

    def chain_workflow(self, input_data: str) -> Dict[str, Any]:
        start = time.perf_counter()
        bytes_sent = 0
        
        # Step 1
        resp1 = self.client.post("/workflow/step1", json={"input_data": input_data})
        resp1.raise_for_status()
        out1 = resp1.json()["output"]
        bytes_sent += len(input_data) + 100
        
        # Step 2
        resp2 = self.client.post("/workflow/step2", json={"input_data": out1})
        resp2.raise_for_status()
        out2 = resp2.json()["output"]
        bytes_sent += len(out1) + 100
        
        # Step 3
        resp3 = self.client.post("/workflow/step3", json={"input_data": out2})
        resp3.raise_for_status()
        out3 = resp3.json()["output"]
        bytes_sent += len(out2) + 100
        
        end = time.perf_counter()
        return {
            "latency_ms": (end - start) * 1000,
            "result": out3,
            "bytes_sent": bytes_sent,
            "steps": 3
        }

    def close(self):
        self.client.close()
    
    async def close_async(self):
        await self.async_client.aclose()
