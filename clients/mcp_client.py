import httpx
import time
import json
import asyncio
from typing import Dict, Any, Optional

from .network_sim import NetworkSimulator

class McpClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8001"):
        self.base_url = base_url
        self.client = httpx.Client(base_url=base_url, timeout=30.0)
        self.async_client = httpx.AsyncClient(base_url=base_url, timeout=30.0)
        self.request_id = 0
        self.session_id = None
        self.network_sim = NetworkSimulator()

    def set_network_conditions(self, latency_ms: int, packet_loss_rate: float, bandwidth_mbps: float = 0.0):
        self.network_sim.set_conditions(latency_ms, packet_loss_rate, bandwidth_mbps)

    def _get_next_id(self):
        self.request_id += 1
        return self.request_id

    def _send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Sync client doesn't support async sleep easily, skipping sim for sync for now
        if self.network_sim.latency_ms > 0:
            time.sleep(self.network_sim.latency_ms / 1000.0)

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._get_next_id()
        }
        response = self.client.post("/message", json=payload)
        response.raise_for_status()
        return response.json()
    
    async def _send_request_async(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        await self.network_sim.simulate_network()

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": self._get_next_id()
        }
        response = await self.async_client.post("/message", json=payload)
        response.raise_for_status()
        return response.json()

    def initialize(self):
        return self._send_request("initialize")

    async def initialize_async(self):
        return await self._send_request_async("initialize")
        
    async def connect_sse(self):
        # Connect to SSE and get session ID
        async with self.async_client.stream("GET", "/sse") as response:
            async for line in response.aiter_lines():
                if line.startswith("event: connection"):
                    # Next line is data: <session_id>
                    pass
                elif line.startswith("data: "):
                    data = line[6:]
                    try:
                        # Try to parse as JSON first (normal messages)
                        msg = json.loads(data)
                    except:
                        self.session_id = data.strip()
                        return self.session_id
                        
    async def listen_for_events(self, duration: float = 5.0):
        events = []
        start = time.time()
        try:
            async with self.async_client.stream("GET", "/sse") as response:
                async for line in response.aiter_lines():
                    if time.time() - start > duration:
                        break
                    if line.startswith("data: "):
                        data = line[6:]
                        try:
                            msg = json.loads(data)
                            events.append(msg)
                            if msg.get("params", {}).get("status") == "completed":
                                break
                        except:
                            pass
        except httpx.ReadTimeout:
            pass
        return events

    def list_tools(self):
        return self._send_request("tools/list")

    def call_tool(self, name: str, arguments: Dict[str, Any]) -> float:
        start = time.perf_counter()
        self._send_request("tools/call", {"name": name, "arguments": arguments})
        end = time.perf_counter()
        return (end - start) * 1000

    async def call_tool_async(self, name: str, arguments: Dict[str, Any]) -> tuple[float, int]:
        start = time.perf_counter()
        
        # Calculate approx payload size
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
            "id": self.request_id + 1
        }
        bytes_sent = len(json.dumps(payload))
        
        await self._send_request_async("tools/call", {"name": name, "arguments": arguments})
        end = time.perf_counter()
        return (end - start) * 1000, bytes_sent

    def list_resources(self):
        return self._send_request("resources/list")

    def read_resource(self, uri: str) -> float:
        start = time.perf_counter()
        self._send_request("resources/read", {"uri": uri})
        end = time.perf_counter()
        return (end - start) * 1000

    async def subscribe_to_resource(self, uri: str):
        # Send subscribe request
        await self._send_request_async("resources/subscribe", {"uri": uri})
        
        # Listen for updates
        updates = []
        start_time = time.time()
        
        async with self.async_client.stream("GET", "/sse") as response:
            async for line in response.aiter_lines():
                if time.time() - start_time > 5.0: # Listen for 5 seconds
                    break
                    
                if line.startswith("data: "):
                    data = line[6:].strip()
                    try:
                        msg = json.loads(data)
                        if msg.get("method") == "notifications/resources/updated":
                            if msg["params"]["uri"] == uri:
                                updates.append({
                                    "timestamp": time.time(),
                                    "data": msg["params"]["delta"]
                                })
                    except:
                        pass
        return updates

    async def chat_turn(self, session_id: str, message: str, turn_count: int) -> Dict[str, Any]:
        start = time.perf_counter()
        
        args = {
            "message": message,
            "sessionId": session_id,
            "turnCount": turn_count
        }
        
        # Simulate upload bandwidth
        payload_size = len(json.dumps(args)) + 100
        await self.network_sim.simulate_transfer(payload_size)
        
        response = await self._send_request_async("prompts/chat", args)
        
        # Simulate download bandwidth
        await self.network_sim.simulate_transfer(len(json.dumps(response)))
        
        end = time.perf_counter()
        
        result = response["result"]
        result["latency_ms"] = (end - start) * 1000
        result["bytes_sent"] = payload_size
        return result

    async def run_task_with_notifications(self, complexity: int) -> Dict[str, Any]:
        start = time.perf_counter()
        event_count = 0
        session_id = None
        task_started = False
        bytes_sent = 0
        
        async with self.async_client.stream("GET", "/sse") as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:].strip()
                    
                    # 1. Get Session ID
                    if not session_id:
                        try:
                            # Check if it looks like a float/int (our simple session ID)
                            float(data) 
                            session_id = data
                            
                            # 2. Start Task immediately after getting Session ID
                            args = {"complexity": complexity, "sessionId": session_id}
                            await self._send_request_async("tools/call", {
                                "name": "generate_task", 
                                "arguments": args
                            })
                            
                            # Calculate bytes
                            payload = {
                                "jsonrpc": "2.0",
                                "method": "tools/call",
                                "params": {"name": "generate_task", "arguments": args},
                                "id": 0 
                            }
                            bytes_sent = len(json.dumps(payload))
                            
                            task_started = True
                            continue
                        except ValueError:
                            pass
                    
                    # 3. Listen for progress
                    if task_started:
                        try:
                            msg = json.loads(data)
                            # Check if it's a notification
                            if msg.get("method") == "notifications/progress":
                                event_count += 1
                                if msg.get("params", {}).get("status") == "completed":
                                    break
                        except:
                            pass
                            
        end = time.perf_counter()
        return {
            "latency_ms": (end - start) * 1000,
            "events": event_count,
            "bytes_sent": bytes_sent
        }


    def chain_workflow(self, input_data: str) -> Dict[str, Any]:
        start = time.perf_counter()
        bytes_sent = 0
        
        # Step 1
        # Note: call_tool returns latency, not result in our current impl. 
        # We need to modify call_tool or use _send_request directly to get data.
        # Let's use _send_request for this specific flow to get the output
        
        # Re-implementing logic here for data access
        def call_step(step, data):
            payload = {
                "jsonrpc": "2.0", 
                "method": "tools/call", 
                "params": {"name": "workflow_step", "arguments": {"step": step, "input_data": data}},
                "id": self._get_next_id()
            }
            resp = self.client.post("/message", json=payload)
            resp.raise_for_status()
            r = resp.json()
            content = json.loads(r["result"]["content"][0]["text"])
            return content["output"], len(json.dumps(payload))

        out1, b1 = call_step(1, input_data)
        out2, b2 = call_step(2, out1)
        out3, b3 = call_step(3, out2)
        
        bytes_sent = b1 + b2 + b3
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
