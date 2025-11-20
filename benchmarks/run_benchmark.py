import time
import pandas as pd
import numpy as np
from typing import List, Dict
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from clients.rest_client import RestClient
from clients.mcp_client import McpClient

def run_benchmarks(iterations: int = 100):
    results = []
    
    print(f"Running benchmarks with {iterations} iterations...")
    
    # Initialize clients
    rest_client = RestClient()
    mcp_client = McpClient()
    
    try:
        # Warmup
        print("Warming up...")
        for _ in range(10):
            rest_client.ping()
            mcp_client.initialize()
            
        # 1. Ping/Pong (Latency)
        print("Benchmarking: Ping/Pong (Latency)")
        for _ in range(iterations):
            # REST
            lat = rest_client.ping()
            results.append({"protocol": "REST", "scenario": "Ping", "latency_ms": lat})
            
            # MCP (using initialize as a lightweight ping equivalent or just a simple tool call if available, 
            # but initialize is good for connection overhead check, let's use list_tools for a lightweight read)
            lat = mcp_client.list_tools() # This returns a dict, we need to measure time inside client or here
            # Wait, the client methods I wrote return latency. Let's check.
            # RestClient methods return float (latency).
            # McpClient methods:
            # initialize -> dict (no latency returned)
            # list_tools -> dict (no latency returned)
            # call_tool -> float (latency returned)
            # read_resource -> float (latency returned)
            
            # I need to wrap list_tools to measure latency or use call_tool
            start = time.perf_counter()
            mcp_client.list_tools()
            end = time.perf_counter()
            lat = (end - start) * 1000
            results.append({"protocol": "MCP", "scenario": "Ping", "latency_ms": lat})

        # 2. Tool Execution (Compute/Logic)
        print("Benchmarking: Tool Execution")
        for _ in range(iterations):
            # REST
            lat = rest_client.calculate("multiply", 123.45, 67.89)
            results.append({"protocol": "REST", "scenario": "Tool Call", "latency_ms": lat})
            
            # MCP
            lat = mcp_client.call_tool("calculate", {"operation": "multiply", "a": 123.45, "b": 67.89})
            results.append({"protocol": "MCP", "scenario": "Tool Call", "latency_ms": lat})

        # 3. Context Retrieval (Data Transfer)
        print("Benchmarking: Context Retrieval (Large Payload)")
        for _ in range(iterations):
            # REST
            lat = rest_client.get_context(1000)
            results.append({"protocol": "REST", "scenario": "Context Retrieval", "latency_ms": lat})
            
            # MCP
            lat = mcp_client.read_resource("context://large_data")
            results.append({"protocol": "MCP", "scenario": "Context Retrieval", "latency_ms": lat})

    finally:
        rest_client.close()
        mcp_client.close()
        
    df = pd.DataFrame(results)
    df.to_csv("reports/benchmark_results.csv", index=False)
    print("Benchmarks completed. Results saved to reports/benchmark_results.csv")

if __name__ == "__main__":
    run_benchmarks()
