"""Drive WS2812B directly from the Raspberry Pi SPI MOSI pin (GPIO10).

Each WS2812B bit is sent as 3 SPI bits at 2.4 MHz:  1 -> 110, 0 -> 100, which
gives T1H ~0.83 us / T0H ~0.42 us - inside the WS2812B tolerance.  A
3.3 V -> 5 V level shifter (74AHCT125) on the data line is strongly
recommended.  Works on Pi 3/4/5 and Zero 2 W.

Kernel setup (see docs/04-setup-guide.md):
    dtparam=spi=on                     in /boot/firmware/config.txt
    spidev.bufsiz=65536                appended to /boot/firmware/cmdline.txt
"""
from __future__ import annotations

import numpy as np

from ..processor import apply_color_correction
from . import Output

try:
    import spidev
except Exception:  # pragma: no cover
    spidev = None

SPI_HZ = 2_400_000
RESET_BYTES = 120   # 120 bytes * 8 bits / 2.4 MHz = 400 us > 280 us reset


def _build_lut() -> np.ndarray:
    """256 x 3 table: byte value -> the 3 SPI bytes that encode it."""
    lut = np.zeros((256, 3), dtype=np.uint8)
    for value in range(256):
        bits = 0
        for i in range(8):
            bit = (value >> (7 - i)) & 1
            bits = (bits << 3) | (0b110 if bit else 0b100)
        lut[value] = [(bits >> 16) & 0xFF, (bits >> 8) & 0xFF, bits & 0xFF]
    return lut


LUT = _build_lut()
ORDER_INDEX = {"RGB": [0, 1, 2], "GRB": [1, 0, 2], "BGR": [2, 1, 0], "BRG": [2, 0, 1], "RBG": [0, 2, 1], "GBR": [1, 2, 0]}


def encode_ws2812(colors_u8: np.ndarray, color_order: str = "GRB") -> bytes:
    """(N,3) RGB uint8 -> SPI byte stream including the reset gap."""
    idx = ORDER_INDEX[color_order.upper()]
    ordered = colors_u8[:, idx].reshape(-1)
    return LUT[ordered].reshape(-1).tobytes() + bytes(RESET_BYTES)


class SPIOutput(Output):
    name = "spi"

    def __init__(self, cfg: dict):
        if spidev is None:
            raise RuntimeError("spidev is required (pip install spidev)")
        dev = cfg.get("device", "/dev/spidev0.0")
        bus, cs = (int(x) for x in dev.replace("/dev/spidev", "").split("."))
        self.spi = spidev.SpiDev()
        self.spi.open(bus, cs)
        self.spi.max_speed_hz = SPI_HZ
        self.spi.mode = 0
        self.order = cfg.get("color_order", "GRB")
        self.correction = cfg.get("color_correction")
        self.error = None

    def send(self, colors: np.ndarray) -> None:
        colors = apply_color_correction(colors, self.correction)
        try:
            self.spi.writebytes2(encode_ws2812(colors, self.order))
            self.error = None
        except Exception as exc:
            self.error = str(exc)

    def close(self) -> None:
        self.spi.close()
