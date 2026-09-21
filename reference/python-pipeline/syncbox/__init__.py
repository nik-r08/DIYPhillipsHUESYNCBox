"""syncbox - a DIY Philips Hue Sync Box.

Captures HDMI video (via a cheap USB capture card), extracts edge colours,
optionally mixes in audio reactivity, and streams the result to WS2812B LED
strips (via WLED / DDP, Adalight serial, or the Pi's own SPI bus) and/or to a
Philips Hue Bridge using the Hue Entertainment streaming API.
"""

__version__ = "0.1.0"
