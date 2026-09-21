# 8. Parity with the Philips Hue Play HDMI Sync Box

Compared against the **Sync Box 8K** (current flagship, 2024) and, where different, the new single-input **Sync Box 4K** (September 2026). Values: **matched**, **partial**, **not matched**. Each row cites a test result or a source. Prices and specs observed 2026-09-21. "Pending" means the test exists in docs/07 but has not been run on hardware.

| Feature | Philips 8K box | This build | Status | Evidence |
|---|---|---|---|---|
| HDMI inputs | 4 | 1 (EZ-SP12H2) or 4 (OREI UHDS-402A) | matched with the matrix, partial with the default | docs/02 |
| Max passthrough | 8K60, 4K120, HDR10, HDR10+, Dolby Vision, VRR, ALLM, HDCP 2.3 ([TechRadar](https://www.techradar.com/home/small-appliances/philips-hue-play-hdmi-sync-box-8k-review)) | 4K60 HDR10, HDCP 2.2 (HDMI 2.0 unit); 4K120/VRR only with the EZ-SP12H21 upgrade | **not matched** on 4K120/VRR/DV by default; partial with the 2.1 unit | docs/02 §2.2 |
| Dolby Vision | passes through | falls back to HDR10 when the capture output is scaled | **not matched** | EZCOO manual, [HyperHDR 1505](https://github.com/awawa-dev/HyperHDR/discussions/1505) |
| Screen-to-light latency | not published; reviews "no lag" | target ≤ 80 ms; parts measured at 50 to 66 ms by the HyperHDR author | pending T1 | docs/07 |
| Light update rate | Zigbee ~25 Hz to the lights | 50 to 60 Hz to the strip | matched or better, pending T2 | [node-phea](https://github.com/JakeBednard/node-phea) |
| Light zones on a 55" TV | 7 (gradient strip) | 142 at 60/m, 3 sides | better | [Hueblog](https://hueblog.com/2020/10/05/my-review-philips-hue-play-gradient-lightstrip/) |
| Sync modes Video / Game / Music | yes | yes (Game, Video, Movie, Music) | matched (SYN) | `tools/tests/test_ui.py` |
| Intensity Subtle / Moderate / High / Extreme | yes | yes | matched (SYN) | same |
| Brightness, on/off from a phone | Hue app | control page on port 80 | matched (SYN) | same |
| Auto input switching | yes | yes, in the HDMI unit | matched | product spec |
| HDR content colour correctness | native | needs the one-time LUT calibration | partial (one manual step) | docs/05 |
| Black-bar handling | yes | yes (HyperHDR) | matched (COMM), pending T5 | docs/01 |
| Turns off with the TV | CEC power detection | signal detection (source sleeps → lights off); CEC only with an extra HDMI cable | partial | docs/05 |
| Built-in smart-TV apps | not supported (Philips' answer is the separate Screen Sync camera) | not supported | matched (both cannot) | [Hueblog](https://hueblog.com/2023/01/04/community-question-of-the-week-sync-box-and-internal-tv-apps/) |
| Audio-reactive (Music mode) | yes | yes (HyperHDR sound capture from HDMI audio) | matched (COMM), untested here | docs/01 |
| Hue ecosystem: drives Hue lights | native | HyperHDR Hue Entertainment v2 | partial; **untested in this project** | docs/05 |
| Hue ecosystem: appears in the Hue app, scenes, automations, voice assistants | yes | no (only via diyHue emulation, out of scope) | **not matched** | |
| eARC | input 4 supports eARC | no eARC through the box; TV-to-bar eARC unaffected | partial | docs/02 |
| One box, one plug | yes; the gradient strip has its own plug (2 plugs total) | yes; strip powered from the box (1 plug total) | matched or better | docs/02 §2.8 |
| Boots unattended | yes | yes, target ≤ 30 s | pending T0 | docs/07 |
| Power-loss resilience | appliance firmware | read-only root, watchdog | pending T7 | docs/05 |
| Updates | automatic via Hue app | one command; rollback | partial (manual) | docs/05 |
| Warranty and support | 2 years, Philips | none; community (HyperHDR issues) and you | **not matched** | |
| HDCP compliance | licensed repeater | relies on the splitter's unencrypted scaled output; legal grey area for protected streams | **not matched** | docs/02 |
| Price, single input | Sync Box 4K (2026) $149.99 + gradient strip 55" $274.99 = **$424.98** | about **$260 to $300** (Build A) | better on price, 20x the zones | docs/02 §2.7 |
| Price, four inputs, 4K120 | Sync Box 8K $384.99 + strip $274.99 = **$659.98** | about **$330 to $400** with the OREI matrix or the EZ-SP12H21 plus a 1080p120 grabber | better | docs/02 |

## What cannot reach parity, and why

1. **HDCP-protected streaming apps** on the PS5: works only because the splitter emits an unencrypted scaled copy. Philips holds an HDCP licence; a DIY box does not. If a future splitter firmware or console stops that, this build loses streaming sync while the Philips box keeps it.
2. **Dolby Vision** through affordable splitters: HDR10 fallback whenever the capture output is scaled. Only HDFury-class units (about $300+) keep DV, at which point the price advantage is gone.
3. **4K120 / VRR** without an HDMI 2.1 unit and a 1080p120 capture card: about $150 extra and still community-reported quirks.
4. **Hue ecosystem integration**: the Philips box lives inside the Hue app with scenes, schedules and voice control. This box drives Hue lights through HyperHDR but is invisible to the Hue app.
5. **Warranty**: none. Mitigation is that every part is a commodity replaceable for $10 to $65.
