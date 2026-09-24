"""Synthetic, seeded fleet of Base-style home batteries."""
import random
from dataclasses import dataclass

MAX_KW = 11.5
CAPACITIES_KWH = (30.0, 39.0, 39.0, 48.0)


@dataclass
class Home:
    id: int
    cap_kwh: float
    soc_kwh: float
    floor_kwh: float
    max_kw: float = MAX_KW

    def discharge_headroom_kw(self, duration_h: float) -> float:
        """Max kW this home can export for `duration_h` without dipping below its backup floor."""
        return max(0.0, min(self.max_kw, (self.soc_kwh - self.floor_kwh) / duration_h))

    def charge_headroom_kw(self, duration_h: float) -> float:
        """Max kW this home can absorb for `duration_h` without overfilling."""
        return max(0.0, min(self.max_kw, (self.cap_kwh - self.soc_kwh) / duration_h))


def make_fleet(n: int, reserve: float, seed: int = 7) -> list[Home]:
    """n homes with varied capacity and state of charge; every home keeps `reserve` of capacity as backup."""
    rng = random.Random(seed)
    homes = []
    for i in range(n):
        cap = rng.choice(CAPACITIES_KWH)
        soc = cap * rng.uniform(0.35, 0.95)
        homes.append(Home(id=i, cap_kwh=cap, soc_kwh=soc, floor_kwh=cap * reserve))
    return homes
