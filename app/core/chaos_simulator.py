import asyncio
import random
import time
from typing import Dict, Any, Callable, List
from app.models.resilience import ChaosConfig, NetworkMode

class NetworkChaosSimulator:
    def __init__(self):
        self.config = ChaosConfig()
        self._flapping_task = None
        self._listeners: List[Callable[[Dict[str, Any]], None]] = []

    def get_status(self) -> Dict[str, Any]:
        return {
            "mode": self.config.mode,
            "latency_ms": self.config.latency_ms,
            "packet_loss_rate": self.config.packet_loss_rate,
            "is_connected": self.config.mode != NetworkMode.BLACKOUT,
            "description": self.config.description,
            "timestamp": time.time()
        }

    def set_mode(self, mode: str, latency_ms: int = None, packet_loss_rate: float = None) -> Dict[str, Any]:
        mode = mode.upper()
        if mode == NetworkMode.ONLINE:
            self.config.mode = NetworkMode.ONLINE
            self.config.latency_ms = latency_ms if latency_ms is not None else 20
            self.config.packet_loss_rate = packet_loss_rate if packet_loss_rate is not None else 0.0
            self.config.description = "Healthy high-speed broadband / low-latency uplink"
            self._stop_flapping()
        elif mode == NetworkMode.DEGRADED:
            self.config.mode = NetworkMode.DEGRADED
            self.config.latency_ms = latency_ms if latency_ms is not None else 650
            self.config.packet_loss_rate = packet_loss_rate if packet_loss_rate is not None else 0.45
            self.config.description = "Degraded rural satellite / edge cellular link (jitter & dropouts)"
            self._stop_flapping()
        elif mode == NetworkMode.BLACKOUT:
            self.config.mode = NetworkMode.BLACKOUT
            self.config.latency_ms = 0
            self.config.packet_loss_rate = 1.0
            self.config.description = "Complete network blackout (0 Mbps, isolated edge)"
            self._stop_flapping()
        elif mode == NetworkMode.FLAPPING:
            self.config.mode = NetworkMode.FLAPPING
            self.config.latency_ms = 350
            self.config.packet_loss_rate = 0.50
            self.config.description = "Intermittent flapping connection (alternating online/offline)"
            self._start_flapping()
        else:
            raise ValueError(f"Unknown network mode: {mode}")

        self._notify_listeners()
        return self.get_status()

    def should_drop_packet(self) -> bool:
        if self.config.mode == NetworkMode.BLACKOUT:
            return True
        if self.config.packet_loss_rate <= 0:
            return False
        return random.random() < self.config.packet_loss_rate

    async def apply_network_effects(self) -> bool:
        """
        Applies simulated latency and packet drop.
        Returns True if packet passes, raises ConnectionError if dropped.
        """
        if self.config.mode == NetworkMode.BLACKOUT:
            raise ConnectionError("Simulated Network Dropout: Connection timed out / unreachable.")

        if self.config.latency_ms > 0:
            # Add small random jitter (+-20%)
            jitter = random.uniform(0.8, 1.2)
            delay = (self.config.latency_ms * jitter) / 1000.0
            await asyncio.sleep(delay)

        if self.should_drop_packet():
            raise ConnectionError(f"Simulated Packet Loss: Network dropped trigger frame ({int(self.config.packet_loss_rate*100)}% loss rate).")

        return True

    def _start_flapping(self):
        self._stop_flapping()
        async def flap_loop():
            is_dropped = False
            while self.config.mode == NetworkMode.FLAPPING:
                await asyncio.sleep(self.config.auto_flap_interval_sec)
                is_dropped = not is_dropped
                self.config.packet_loss_rate = 1.0 if is_dropped else 0.1
                self.config.description = f"Flapping active: currently {'DISCONNECTED' if is_dropped else 'RECONNECTED'}"
                self._notify_listeners()
        try:
            loop = asyncio.get_running_loop()
            self._flapping_task = loop.create_task(flap_loop())
        except RuntimeError:
            pass

    def _stop_flapping(self):
        if self._flapping_task and not self._flapping_task.done():
            self._flapping_task.cancel()
            self._flapping_task = None

    def add_listener(self, cb: Callable[[Dict[str, Any]], None]):
        self._listeners.append(cb)

    def _notify_listeners(self):
        st = self.get_status()
        for cb in self._listeners:
            try:
                cb(st)
            except Exception:
                pass

# Global chaos simulator singleton
chaos = NetworkChaosSimulator()
