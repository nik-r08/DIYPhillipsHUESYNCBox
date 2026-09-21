import struct

import numpy as np
from syncbox.outputs.adalight import build_adalight_frame
from syncbox.outputs.hue_entertainment import build_hue_message, map_channels_to_zones
from syncbox.outputs.rpi_spi import LUT, encode_ws2812
from syncbox.outputs.wled_ddp import build_ddp_packets
from syncbox.zones import build_layout


def test_ddp_single_packet():
    pkts = build_ddp_packets(bytes(range(9)), seq=3)
    assert len(pkts) == 1
    flags, seq, dtype, dest, offset, length = struct.unpack(">BBBBIH", pkts[0][:10])
    assert flags == 0x41 and seq == 3 and dtype == 0x0B and dest == 1 and offset == 0 and length == 9
    assert pkts[0][10:] == bytes(range(9))


def test_ddp_splits_at_480_pixels():
    data = bytes(500 * 3)
    pkts = build_ddp_packets(data)
    assert len(pkts) == 2
    f0, _, _, _, off0, len0 = struct.unpack(">BBBBIH", pkts[0][:10])
    f1, _, _, _, off1, len1 = struct.unpack(">BBBBIH", pkts[1][:10])
    assert f0 == 0x40 and len0 == 1440 and off0 == 0
    assert f1 == 0x41 and off1 == 1440 and len1 == 60


def test_adalight_header():
    f = build_adalight_frame(bytes(3 * 300))
    count = 299
    assert f[:3] == b"Ada" and f[3] == count >> 8 and f[4] == count & 0xFF and f[5] == (count >> 8) ^ (count & 0xFF) ^ 0x55


def test_hue_message_layout():
    eid = "12345678-1234-1234-1234-123456789abc"
    msg = build_hue_message(eid, 7, [(0, (255, 0, 128)), (3, (0, 255, 0))])
    assert msg[:9] == b"HueStream" and msg[9:11] == b"\x02\x00" and msg[11] == 7
    assert msg[14] == 0 and msg[16:52] == eid.encode()
    assert len(msg) == 52 + 2 * 7
    assert msg[52] == 0 and struct.unpack(">HHH", msg[53:59]) == (65535, 0, 128 * 257)
    assert msg[59] == 3


def test_hue_channel_mapping_by_position():
    rects = build_layout(8, 4, 8, 4)
    channels = [
        {"channel_id": 0, "position": {"x": -1.0, "y": 0.5, "z": 0.0}},   # left of TV
        {"channel_id": 1, "position": {"x": 1.0, "y": 0.5, "z": 0.0}},    # right of TV
        {"channel_id": 2, "position": {"x": 0.0, "y": 0.5, "z": 1.0}},    # above
    ]
    m = dict(map_channels_to_zones(channels, rects))
    assert rects[m[0]][0] == 0.0          # left edge
    assert rects[m[1]][2] == 1.0          # right edge
    assert rects[m[2]][1] == 0.0          # top edge
    m2 = dict(map_channels_to_zones(channels, rects, {"1": 5}))
    assert m2[1] == 5


def test_ws2812_spi_encoding():
    # 0b10101010 -> 110 100 110 100 110 100 110 100 = 0xD3 0x4D 0x34
    assert list(LUT[0b10101010]) == [0xD3, 0x4D, 0x34]
    assert list(LUT[0xFF]) == [0xDB, 0x6D, 0xB6]
    assert list(LUT[0x00]) == [0x92, 0x49, 0x24]
    stream = encode_ws2812(np.array([[255, 0, 0]], dtype=np.uint8), "GRB")
    assert stream[:3] == bytes([0x92, 0x49, 0x24])       # G first (0)
    assert stream[3:6] == bytes([0xDB, 0x6D, 0xB6])      # then R (255)
    assert stream[-120:] == bytes(120)
