# 2. Signal chain and wiring

## 2.1 HDMI chain

```
                 ┌──────────────┐        ┌────────────────────┐   out 1 (4K HDR)   ┌──────┐
 PS5 ───────────►│              │        │  HDMI 1x2 splitter │───────────────────►│  TV  │
 Apple TV ──────►│ HDMI switch  │───────►│  (4K60, downscaler)│                    └──┬───┘
 Cable box ─────►│  (auto)      │        │                    │   out 2 (1080p)       │ eARC
                 └──────────────┘        └─────────┬──────────┘                       ▼
                                                   │                             ┌──────────┐
                                                   ▼                             │ Sound bar│
                                        ┌──────────────────┐   USB 3             └──────────┘
                                        │ USB HDMI capture │──────────► Raspberry Pi
                                        └──────────────────┘             (video + audio)
```

Rules:

1. **Everything you want synced must pass through the splitter before it reaches the TV.** Sources plugged straight into the TV are invisible to the capture card.
2. **Use the TV's eARC/ARC output for the sound bar as before.** The TV still gets the full signal, so audio to the sound bar is unaffected. If your sound bar is an HDMI *pass-through* device (sources plug into the sound bar), put the splitter between the sound bar and the TV.
3. **One splitter, many sources.** An auto HDMI switch in front of the splitter picks whichever source is on. Many TVs also let you use the TV itself as the switch, but then the sources bypass the splitter, so do not.
4. **Turn HDCP off on game consoles.** PS5: Settings > System > HDMI > Enable HDCP > off. Xbox: Settings > General > TV & display options > Video modes > uncheck "Allow HDCP" (varies by generation). Games then capture cleanly with any splitter. Streaming apps re-enable HDCP by themselves.
5. **Protected content.** Netflix, Disney+ etc. require HDCP. Many cheap splitters output an unencrypted signal on their second port and the community relies on that. Whether that is legal where you live is your call; the official box is a licensed HDCP repeater, a DIY chain is not.
6. **Match resolutions to what the card can take.** MS2130 accepts 4K input and downscales; MS2109 needs 1080p or lower at its input, so pair it with a downscaling splitter or set the source to 1080p.

### What about HDR, 4K120, VRR, Dolby Vision?

| Feature | Cheap 4K60 splitter ($20 to $40) | HDMI 2.1 splitter ($60 to $120) |
|---|---|---|
| 4K60 HDR10 to TV | yes | yes |
| 4K120 / 120 Hz | no, console falls back to 60 Hz | yes |
| VRR | no | usually |
| Dolby Vision | usually breaks (falls back to HDR10) | some |
| eARC through the splitter | not needed, eARC is between TV and sound bar | |
| CEC (TV remote controls the console) | often flaky through a splitter | varies |

The capture side is always 1080p or lower SDR: the LEDs cannot show HDR anyway.

## 2.2 Wiring the LED strip to an ESP32

```
                       5V 10A power supply
                       ┌────────────┐
                       │ +5V   GND  │
                       └──┬──────┬──┘
                          │      │
                    fuse  │      │
                   ┌─[10A]┘      │
                   │             │
     ┌─────────────┼─────────────┼───────────────────────────────┐
     │             │             │                               │
     │      ┌──────┴──────┐      │       ┌────────────────────┐  │
     │      │ 1000uF cap  │      │       │  74AHCT125         │  │
     │      │  + │   │ -  │      │       │  pin14 VCC ◄───────┼──┤ 5V
     │      └──┬─┘   └──┬─┘      │       │  pin7  GND ◄───────┼──┼──── GND
     │         │        │        │       │  pin1  1OE ◄───────┼──┼──── GND (enable)
     │         │        │        │       │  pin2  1A  ◄───────┼──┼──── ESP32 GPIO16
     │         │        │        │       │  pin3  1Y  ────┐   │  │
     │         │        │        │       └────────────────┼───┘  │
     │         │        │        │                        │      │
     │         ▼        ▼        │                 330 ohm│      │
     │   ┌─────────────────────────────────────────────┐  │      │
     ├──►│ +5V                                         │  │      │
     │   │ DIN ◄───────────────────────────────────────┼──┘      │
     ├──►│ GND        WS2812B strip, LED 0 → LED N     │         │
     │   └─────────────────────────────────────────────┘         │
     │                                                           │
     │   ESP32 DevKit                                            │
     │   ┌─────────────┐                                         │
     ├──►│ VIN (5V)    │                                         │
     ├──►│ GND         │◄──── must share GND with strip & supply │
     │   │ GPIO16 ─────┼──────────────────────────► shifter 1A   │
     │   └─────────────┘                                         │
     └───────────────────────────────────────────────────────────┘
```

Checklist:

- **Common ground.** Supply GND, strip GND and ESP32 GND all connected. The single most common cause of flicker.
- **Power the ESP32 from the same 5 V supply** via its VIN/5V pin. Do not power a 300-LED strip from the ESP32's USB port.
- **Level shifter.** WS2812B wants a data high of at least 0.7 x VDD = 3.5 V; the ESP32 outputs 3.3 V. It often works without a shifter over a 10 cm wire and then randomly does not. The 74AHCT125 costs a dollar. Tie its OE pin (pin 1) to GND to enable channel 1; leave unused inputs (pins 5, 9, 12) tied to GND too.
- **330 ohm resistor** in series with data, mounted at the strip end. Damps ringing on the line.
- **1000 uF capacitor** across 5 V and GND at the strip's input, rated 6.3 V or more, mind the polarity (long leg is +).
- **Data direction.** Strips have arrows printed on them. Feed data into the end the arrows point away from.
- **Fuse** on the 5 V line between supply and strip. 10 A blade fuse for a 10 A supply.

### Power injection

WS2812B strips have thin copper: after 2.5 to 3 m at high brightness the far end goes reddish-brown because the 5 V has sagged. Fix: run a second pair of 18 AWG wires from the supply to the far end of the strip (and to the middle for 5 m at 60/m). Alternatively use WS2815 12 V strips, which do not need injection over 5 m.

Current budget for a 65" TV with about 260 LEDs:

| Scenario | Current |
|---|---|
| All LEDs full white, no limiter | 260 x 60 mA = 15.6 A |
| Typical film content, brightness 0.8 | 3 to 5 A |
| WLED limiter at 8000 mA | never above 8 A |

Set the limiter (WLED: Config > LED Preferences > "Maximum current", or `MAX_MILLIAMPS` in the ESP32 firmware) to 80 % of your supply's rating.

### Which GPIO?

- ESP32 DevKit: GPIO16 (WLED default on classic ESP32). GPIO2 on boards with PSRAM. Any output-capable pin works, just avoid strapping pins 0, 2, 12, 15 and the input-only 34 to 39.
- ESP8266 D1 mini: GPIO2 (D4).
- Set the same pin in WLED under Config > LED Preferences.

## 2.3 Wiring the strip straight to the Raspberry Pi (no ESP32)

Use the SPI MOSI pin. It is a hardware peripheral, so the timing is exact even while the Pi is busy, unlike PWM-based libraries which do not work on the Pi 5 at all.

```
 Raspberry Pi 40-pin header (top view, USB ports facing down)

  3V3 (1)  (2)  5V
      (3)  (4)  5V
      (5)  (6)  GND ──────────────► shifter GND, strip GND, supply GND
      ...
      (17) (18)
 MOSI (19) (20) GND
 GPIO10 ────────────────────────► 74AHCT125 pin 2 (1A)   → pin 3 (1Y) → 330 ohm → strip DIN
      (21) (22)
      (23) (24)
```

Power the Pi from its own USB-C supply, the strip from the 5 V 10 A supply, and connect their grounds. Do **not** back-feed 5 V into the Pi header from the LED supply unless you know exactly what you are doing.

Kernel setup on Raspberry Pi OS Bookworm:

```
sudo raspi-config nonint do_spi 0             # enable SPI
sudo sed -i 's/$/ spidev.bufsiz=65536/' /boot/firmware/cmdline.txt   # >450 LEDs per transfer
sudo reboot
```

Then in `config.yaml`:

```yaml
outputs:
  spi: {enabled: true, device: /dev/spidev0.0, color_order: GRB}
  wled: {enabled: false}
```

## 2.4 Wired ESP32 (Adalight over USB)

If Wi-Fi is unreliable, connect the ESP32 to the Pi with a USB cable. It shows up as `/dev/ttyUSB0` (CP2102) or `/dev/ttyACM0` (native USB boards). WLED speaks Adalight on its serial port automatically; set the baud rate under Config > Sync Interfaces > Serial (500000 for 300 LEDs at 30 fps). Same for the firmware in `esp32/` (`SERIAL_BAUD`).

```yaml
outputs:
  adalight: {enabled: true, port: /dev/ttyUSB0, baud: 500000}
```

## 2.5 Mounting the strip behind the TV

- Keep the strip 5 to 10 cm inside the TV's outer edge and the TV 10 to 20 cm from the wall. Too close to the edge and you see dots; too far from the wall and the glow is dim.
- Aim LEDs at the wall (perpendicular), not sideways. Aluminium channel with a 45-degree profile does this neatly.
- Cut only at the marked copper pads. Use 3-pin JST leads or short wires at each corner. Corner connectors exist but a 30 mm wire loop is more reliable.
- Start at the corner nearest the ESP32/Pi and power supply, usually bottom-left or bottom-right. Note the start corner and direction (as seen from the front); the software needs them.
- Leave the bottom edge out if a stand or sound bar blocks it. Set `leds.bottom: 0`.

Typical LED counts at 60/m (strip 5 cm inside the edge):

| TV | Top / bottom | Left / right | Total |
|---|---|---|---|
| 55" | 70 | 38 | 216 |
| 65" | 83 | 46 | 258 |
| 75" | 96 | 53 | 298 |

## 2.6 Audio input options

1. **HDMI audio through the capture card (default).** The card enumerates as a USB audio input. `tools/list_devices.sh` shows it. Nothing to wire.
2. **Sound bar 3.5 mm / headphone out to a USB sound card's line-in.** Keep the sound bar volume moderate; a headphone output can clip a mic input. Use the sound card's line-in (blue) if it has one, otherwise the mic input at low gain.
3. **Optical out to a TOSLINK DAC to the USB sound card.** Same as 2 with a $12 DAC in between.
