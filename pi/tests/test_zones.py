import numpy as np
from syncbox.zones import ZoneSampler, build_layout, nearest_zone_for_angle, zone_angles


def test_counts_and_order_clockwise():
    r = build_layout(top=4, right=2, bottom=4, left=2, start="bottom-left", direction="clockwise", border=0.1)
    assert r.shape == (12, 4)
    # first LED: left edge, bottom end
    assert r[0][0] == 0 and r[0][3] == 1.0
    # after left (2) come the top LEDs left->right
    assert r[2][1] == 0 and r[2][0] == 0 and r[5][2] == 1.0
    # then right edge top->bottom
    assert r[6][2] == 1.0 and r[6][1] == 0
    # then bottom right->left
    assert r[8][3] == 1.0 and r[8][2] == 1.0 and r[11][0] == 0


def test_counterclockwise_starts_along_bottom():
    r = build_layout(4, 2, 4, 2, start="bottom-left", direction="counterclockwise", border=0.1)
    assert r[0][0] == 0 and r[0][3] == 1.0 and r[0][1] == 0.9   # bottom edge, leftmost
    assert r[3][2] == 1.0                                        # bottom edge, rightmost
    assert r[4][2] == 1.0 and r[4][3] == 1.0                     # right edge, bottom end


def test_start_corner_and_offset():
    base = build_layout(4, 2, 4, 2, start="bottom-left")
    tl = build_layout(4, 2, 4, 2, start="top-left")
    assert np.allclose(tl[0], base[2])
    off = build_layout(4, 2, 4, 2, start="bottom-left", offset=3)
    assert np.allclose(off[0], base[3])
    assert np.allclose(off[-1], base[2])


def test_no_bottom_leds():
    r = build_layout(10, 5, 0, 5)
    assert r.shape == (20, 4)


def test_sampler_matches_bruteforce():
    rng = np.random.default_rng(0)
    rects = build_layout(8, 4, 8, 4, border=0.1)
    w, h = 64, 36
    img = rng.integers(0, 256, size=(h, w, 3), dtype=np.uint8)
    s = ZoneSampler(rects, w, h)
    got = s.sample(img)
    for i in range(len(rects)):
        x0, x1, y0, y1 = s.x0[i], s.x1[i], s.y0[i], s.y1[i]
        expected = img[y0:y1, x0:x1].reshape(-1, 3).mean(axis=0)
        assert np.allclose(got[i], expected, atol=1e-3)


def test_angles_and_nearest():
    rects = build_layout(8, 4, 8, 4)
    ang = zone_angles(rects)
    top_mid = nearest_zone_for_angle(ang, np.pi / 2)
    assert rects[top_mid][1] == 0.0            # on the top edge
    assert abs((rects[top_mid][0] + rects[top_mid][2]) / 2 - 0.5) < 0.13
    left_mid = nearest_zone_for_angle(ang, np.pi)
    assert rects[left_mid][0] == 0.0


def test_edges_follow_layout():
    from syncbox.zones import build_layout_with_edges
    _, edges = build_layout_with_edges(4, 2, 4, 2, start="bottom-left", direction="clockwise")
    assert edges == ["left"] * 2 + ["top"] * 4 + ["right"] * 2 + ["bottom"] * 4
    _, edges = build_layout_with_edges(4, 2, 4, 2, start="top-right", direction="counterclockwise", offset=1)
    assert edges[:3] == ["top", "top", "top"] and edges[3] == "left"
