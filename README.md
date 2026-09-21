# DIY Sync Box

**Engine decision: HyperHDR v22 is the engine.** This repository is the integration layer that turns HyperHDR, a Raspberry Pi 5, a USB HDMI grabber, an HDMI switch-splitter and an addressable LED strip into **one box behind the TV** that behaves like a Philips Hue Play HDMI Sync Box: one HDMI out, N HDMI in, one power cord, one LED lead, boots into sync unattended, controlled from a phone. The Python pipeline written earlier in this project is kept under `reference/` as an "understand how it works" module; it is not on the product path. Reasons and evidence: [docs/01-engine-decision.md](docs/01-engine-decision.md).

**Evidence status:** nothing in this repository has been run on real hardware yet. Every claim carries a label (HW / SYN / COMM / UNT) in [docs/00-status.md](docs/00-status.md), and every product target has a pass/fail test in [docs/07-acceptance-tests.md](docs/07-acceptance-tests.md) marked *pending user measurement*. Parts, prices and specs were verified by web search on 2026-09-21 and are dated in the docs.

## What it is

```
                       ┌──────────────── SYNC BOX ────────────────┐
  PS5 ──HDMI──►[IN 1]──┤ HDMI 1x2 scaler ──OUT 1──►[HDMI OUT]──► TV │
  (src 2)─────►[IN 2]──┤        └──OUT 2 (1080p)──► MS2130 grabber   │
  mains ───────►[AC]───┤ 5 V PSU ─► Pi 5 (HyperHDR) ─USB─► Pico ─►[LED]├──► WS2812B strip, 142 zones
                       │ [●] status                                │
                       └───────────────────────────────────────────┘
```

| | Philips Sync Box 4K (2026) + Gradient Lightstrip 55" | This build (Build A) |
|---|---|---|
| Price, observed 2026-09-21 | $149.99 + $274.99 = **$425** | **about $260 to $300** |
| Light zones on a 55" TV | 7 | 142 |
| Boxes / wall plugs behind the TV | 1 box, 2 plugs | 1 box, 1 plug |
| Update rate to the lights | ~25 Hz (Zigbee) | 50 to 60 Hz (serial) |
| Dolby Vision, 4K120, VRR, HDCP licence, Hue app integration, warranty | yes | **no** (see [docs/08-parity.md](docs/08-parity.md)) |

## The one-box design

- **HDMI unit:** EZCOO EZ-SP12H2 1x2 with per-output scaler (the HyperHDR author's recommendation) for one source; OREI UHDS-402A 4x2 matrix for up to four. Every affordable unit sends 1080p *HDR* to the grabber, so HyperHDR's LUT tone mapping is part of the design. HDMI 2.1 option: EZCOO EZ-SP12H21 at $79.99 (+ a 1080p120 grabber) for PS5 4K120/VRR. [docs/02](docs/02-hardware-one-box.md) §2.2.
- **Capture:** MS2130 USB 3 grabber, YUYV 640x480x60. Measured at 50 to 66 ms by the HyperHDR author. The TC358743 CSI board was evaluated and rejected for Pi 5: manual media-controller scripting, a 2025 kernel regression, unverified audio, and the only Pi 5 measurement found was slower. [docs/02](docs/02-hardware-one-box.md) §2.3.
- **Compute:** Raspberry Pi 5 2 GB ($65 after the 2026 price rises) with the Active Cooler. Pi 4 works with a slower decode and boot.
- **LED driver:** a Raspberry Pi Pico running HyperSerialPico, *inside the box*, on a 10 cm USB lead. HyperHDR explicitly does not support driving WS2812B from the Pi's own pins on a Pi 5; this is the author's supported path and it costs $5. WLED on an external ESP32 remains the documented alternative. [docs/02](docs/02-hardware-one-box.md) §2.4.
- **Power:** one Mean Well LRS-100-5 (5 V 18 A, $19 to $25) behind a fused IEC inlet feeds the strip, the Pi (through the 5 V header, fused) and the HDMI unit. Build B swaps it for an external 5 V 10 A brick if you do not want mains inside the box. Fuse, capacitor, wire gauge and injection points are calculated for a 55" TV in [docs/02](docs/02-hardware-one-box.md) §2.5.
- **Enclosure:** parametric OpenSCAD case (`hardware/enclosure.scad`) with panel-mount HDMI pass-throughs, a GX16 LED connector, a status LED and vents, or a Hammond 1591XXFBK with a drilling template. Dimensioned drawing in [docs/03](docs/03-enclosure.md).
- **Strip:** WS2812B 60/m in a Muzata frosted aluminium channel, 3 sides (142 LEDs) like the Hue strip, or 4 sides (210). [docs/02](docs/02-hardware-one-box.md) §2.6.

## Appliance behaviour

Boots to sync in about 25 s on a Pi 5 with no peripherals; read-only root with the hardware watchdog so a power cut cannot corrupt the card; lights off or ambient when there is no HDMI signal and back within about 2 s; sync follows whichever input is active; `syncbox.local`, no internet, no cloud; a phone-sized page with power, mode, intensity and brightness plus an advanced page; a first-boot wizard for LED counts and calibration; one-command update with rollback; Hue Entertainment through HyperHDR (untested here). Mechanisms and their evidence: [docs/05-operations.md](docs/05-operations.md).

## Install

Flash the image (build it with `image/build.sh`) or, on Raspberry Pi OS Lite 64-bit:

```bash
curl -fsSL https://raw.githubusercontent.com/nik-r08/DIYPhillipsHUESYNCBox/main/installer/install.sh | sudo bash
sudo reboot     # then open http://syncbox.local/ on your phone
```

Full steps, Pico flashing and the WLED alternative: [docs/04-install.md](docs/04-install.md).

## Prove it

[docs/07-acceptance-tests.md](docs/07-acceptance-tests.md) defines nine pass/fail tests (boot time, latency ≤ 80 ms filmed at 240 fps, ≥ 50 Hz for 8 h, passthrough integrity, colour, black bars, 24 h soak, recovery, thermal, wall power) with what a fail looks like and the first thing to change. The kit under `tools/tests/` generates the test videos, measures latency from a phone slow-motion clip (self-tested to recover a planted 50 ms delay exactly), logs the LED update rate, and logs temperature, throttling and restarts.

## Repository layout

```
README.md                     this page
docs/00-status.md             evidence audit of every claim
docs/01-engine-decision.md    HyperHDR vs the custom pipeline, with sources
docs/02-hardware-one-box.md   verified parts, HDMI unit, capture, power, strip, cable plan
docs/03-enclosure.md          case, drawing, wiring inside the box, drilling template
docs/04-install.md            image, one-line installer, Pico, WLED alternative
docs/05-operations.md         appliance behaviours and their mechanisms
docs/07-acceptance-tests.md   pass/fail table, fail signatures, first fixes
docs/08-parity.md             feature-by-feature parity with the Philips box
hardware/enclosure.scad       parametric case
installer/                    install.sh, persist.sh, systemd units, syncbox-ui, scripts
image/                        pi-gen stage and build script
tools/tests/                  test kit + fake HyperHDR + UI tests
reference/                    the earlier Python pipeline, ESP32 firmware and v1 docs
```

## Honest limits

Cannot sync the Fire TV's built-in apps (neither can Philips). Dolby Vision falls back to HDR10. 4K120/VRR need the HDMI 2.1 unit. HDCP-protected streams rely on splitter behaviour that is a legal grey area where you live. No Hue-app integration, no warranty. Details and mitigations in [docs/08-parity.md](docs/08-parity.md).
