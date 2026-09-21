"""LED layout -> screen-edge sampling zones.

The strip runs around the back of the TV.  Each LED gets a small rectangle on
the edge of the picture (in normalised 0..1 coordinates) whose average colour
it will display.  ``build_layout`` returns those rectangles in *physical strip
order*, i.e. index 0 is the first LED after the controller.
"""
from __future__ import annotations

import math

import numpy as np

CORNERS = ("bottom-left", "top-left", "top-right", "bottom-right")


def _edge_rects(edge: str, n: int, border: float) -> list[tuple[float, float, float, float]]:
    rects = []
    for i in range(n):
        a, b = i / n, (i + 1) / n
        if edge == "top":         # left -> right
            rects.append((a, 0.0, b, border))
        elif edge == "right":     # top -> bottom
            rects.append((1.0 - border, a, 1.0, b))
        elif edge == "bottom":    # right -> left
            rects.append((1.0 - b, 1.0 - border, 1.0 - a, 1.0))
        elif edge == "left":      # bottom -> top
            rects.append((0.0, 1.0 - b, border, 1.0 - a))
        else:
            raise ValueError(edge)
    return rects


def build_layout_with_edges(
    top: int,
    right: int,
    bottom: int,
    left: int,
    start: str = "bottom-left",
    direction: str = "clockwise",
    border: float = 0.08,
    offset: int = 0,
) -> tuple[np.ndarray, list[str]]:
    """Like ``build_layout`` but also returns the edge name of every LED."""
    if start not in CORNERS:
        raise ValueError(f"start must be one of {CORNERS}")
    border = float(min(max(border, 0.01), 0.5))

    # Clockwise path starting at the bottom-left corner.
    segments = [
        ("bottom-left", "left", _edge_rects("left", left, border)),
        ("top-left", "top", _edge_rects("top", top, border)),
        ("top-right", "right", _edge_rects("right", right, border)),
        ("bottom-right", "bottom", _edge_rects("bottom", bottom, border)),
    ]
    if direction == "counterclockwise":
        segments = [
            ("bottom-left", "bottom", segments[3][2][::-1]),
            ("bottom-right", "right", segments[2][2][::-1]),
            ("top-right", "top", segments[1][2][::-1]),
            ("top-left", "left", segments[0][2][::-1]),
        ]
    elif direction != "clockwise":
        raise ValueError("direction must be clockwise or counterclockwise")

    names = [name for name, _, _ in segments]
    k = names.index(start)
    segments = segments[k:] + segments[:k]
    rects = [r for _, _, seg in segments for r in seg]
    edges = [edge for _, edge, seg in segments for _ in seg]
    arr = np.array(rects, dtype=np.float32).reshape(-1, 4)
    if offset and len(arr):
        shift = int(offset) % len(arr)
        arr = np.roll(arr, -shift, axis=0)
        edges = edges[shift:] + edges[:shift]
    return arr, edges


def build_layout(
    top: int,
    right: int,
    bottom: int,
    left: int,
    start: str = "bottom-left",
    direction: str = "clockwise",
    border: float = 0.08,
    offset: int = 0,
) -> np.ndarray:
    """Return an (N, 4) float32 array of [x0, y0, x1, y1] rectangles.

    ``start`` is the corner where the strip begins and ``direction`` is the way
    it runs *as seen from the front of the TV*.  ``offset`` shifts LED #0 that
    many LEDs further along the path (useful when the strip starts mid-edge).
    """
    return build_layout_with_edges(top, right, bottom, left, start, direction, border, offset)[0]


def layout_from_config(leds: dict) -> np.ndarray:
    return layout_with_edges_from_config(leds)[0]


def layout_with_edges_from_config(leds: dict) -> tuple[np.ndarray, list[str]]:
    return build_layout_with_edges(
        int(leds.get("top", 0)),
        int(leds.get("right", 0)),
        int(leds.get("bottom", 0)),
        int(leds.get("left", 0)),
        start=leds.get("start", "bottom-left"),
        direction=leds.get("direction", "clockwise"),
        border=float(leds.get("border", 0.08)),
        offset=int(leds.get("offset", 0)),
    )


def zone_centers(rects: np.ndarray) -> np.ndarray:
    """(N, 2) centre points of each zone in normalised screen coordinates."""
    cx = (rects[:, 0] + rects[:, 2]) / 2.0
    cy = (rects[:, 1] + rects[:, 3]) / 2.0
    return np.stack([cx, cy], axis=1)


def zone_angles(rects: np.ndarray) -> np.ndarray:
    """Angle (radians) of each zone around the screen centre, 0 = right, pi/2 = top."""
    c = zone_centers(rects)
    return np.arctan2(-(c[:, 1] - 0.5), c[:, 0] - 0.5)


def nearest_zone_for_angle(angles: np.ndarray, angle: float) -> int:
    """Index of the zone whose angle is closest to ``angle`` (wrap-around aware)."""
    diff = np.abs((angles - angle + math.pi) % (2 * math.pi) - math.pi)
    return int(np.argmin(diff))


class ZoneSampler:
    """Fast mean-colour extraction for all zones using a summed-area table."""

    def __init__(self, rects: np.ndarray, width: int, height: int):
        self.width, self.height = int(width), int(height)
        x0 = np.floor(rects[:, 0] * width).astype(np.int64)
        x1 = np.ceil(rects[:, 2] * width).astype(np.int64)
        y0 = np.floor(rects[:, 1] * height).astype(np.int64)
        y1 = np.ceil(rects[:, 3] * height).astype(np.int64)
        x0 = np.clip(x0, 0, width - 1)
        y0 = np.clip(y0, 0, height - 1)
        x1 = np.clip(np.maximum(x1, x0 + 1), 1, width)
        y1 = np.clip(np.maximum(y1, y0 + 1), 1, height)
        self.x0, self.x1, self.y0, self.y1 = x0, x1, y0, y1
        self.area = ((y1 - y0) * (x1 - x0)).astype(np.float32)[:, None]

    def sample(self, rgb: np.ndarray) -> np.ndarray:
        """``rgb`` is (H, W, 3) uint8; returns (N, 3) float32 mean colours."""
        if rgb.shape[0] != self.height or rgb.shape[1] != self.width:
            raise ValueError("frame size does not match sampler")
        sat = np.zeros((self.height + 1, self.width + 1, 3), dtype=np.int64)
        sat[1:, 1:] = rgb.astype(np.int64).cumsum(axis=0).cumsum(axis=1)
        total = (
            sat[self.y1, self.x1]
            - sat[self.y0, self.x1]
            - sat[self.y1, self.x0]
            + sat[self.y0, self.x0]
        )
        return total.astype(np.float32) / self.area
