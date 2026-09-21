"""Output back-ends.  Each exposes ``send(colors_u8)`` and ``close()``."""
from __future__ import annotations

import numpy as np


class Output:
    name = "output"

    def send(self, colors: np.ndarray) -> None:  # (N,3) uint8, layout order
        raise NotImplementedError

    def close(self) -> None:
        pass


class MemoryOutput(Output):
    """Keeps the last frame - used by tests and the web preview."""

    name = "memory"

    def __init__(self):
        self.last = None
        self.count = 0

    def send(self, colors: np.ndarray) -> None:
        self.last = colors.copy()
        self.count += 1


def build_outputs(cfg: dict, layout_rects) -> list[Output]:
    """Instantiate every enabled output from the ``outputs`` config section."""
    outs: list[Output] = []
    o = cfg.get("outputs", {})
    if o.get("wled", {}).get("enabled"):
        from .wled_ddp import WLEDOutput
        outs.append(WLEDOutput(o["wled"]))
    if o.get("adalight", {}).get("enabled"):
        from .adalight import AdalightOutput
        outs.append(AdalightOutput(o["adalight"]))
    if o.get("spi", {}).get("enabled"):
        from .rpi_spi import SPIOutput
        outs.append(SPIOutput(o["spi"]))
    if o.get("hue", {}).get("enabled"):
        from .hue_entertainment import HueEntertainmentOutput
        outs.append(HueEntertainmentOutput(o["hue"], layout_rects))
    return outs
