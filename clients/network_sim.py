import asyncio
import random
import time

class NetworkSimulator:
    def __init__(self, latency_ms: int = 0, packet_loss_rate: float = 0.0, bandwidth_mbps: float = 0.0):
        self.latency_ms = latency_ms
        self.packet_loss_rate = packet_loss_rate
        self.bandwidth_mbps = bandwidth_mbps
        
    async def simulate_network(self):
        """
        Simulates network conditions (Latency + Packet Loss).
        """
        if self.packet_loss_rate > 0 and random.random() < self.packet_loss_rate:
            await asyncio.sleep(self.latency_ms / 1000.0) 
            raise ConnectionError("Simulated Network Packet Loss")
            
        if self.latency_ms > 0:
            await asyncio.sleep(self.latency_ms / 1000.0)

    async def simulate_transfer(self, bytes_count: int):
        """
        Simulates data transfer time based on bandwidth.
        Time = (Bytes * 8) / (Mbps * 1,000,000)
        Also adds standard latency.
        """
        await self.simulate_network() # Base latency/loss
        
        if self.bandwidth_mbps > 0:
            bits = bytes_count * 8
            bits_per_second = self.bandwidth_mbps * 1_000_000
            transfer_time = bits / bits_per_second
            await asyncio.sleep(transfer_time)
            
    def set_conditions(self, latency_ms: int, packet_loss_rate: float, bandwidth_mbps: float = 0.0):
        self.latency_ms = latency_ms
        self.packet_loss_rate = packet_loss_rate
        self.bandwidth_mbps = bandwidth_mbps
