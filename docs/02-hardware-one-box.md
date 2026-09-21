# 2. One box behind the TV: hardware design

Target: one enclosure, N HDMI inputs, 1 HDMI output, 1 power cord, 1 LED lead. Every part below was checked by web search on 2026-09-21; prices are as observed that day in the linked page or its search snippet and must be re-checked at checkout. Evidence labels as in `docs/00-status.md`.

## 2.1 Block diagram

```
                       ┌─────────────────────────── SYNC BOX (one enclosure) ───────────────────────────┐
  PS5 ──HDMI──►[IN 1]──┤  HDMI switch/splitter ──OUT 1──►[HDMI OUT]──HDMI──► TV                          │
  (2nd src)──►[IN 2]───┤        (scaler ON out 2)                                                        │
                       │                 └──OUT 2 (1080p)──► MS2130 USB grabber ──USB 3──► Raspberry Pi 5 │
                       │                                                               │  HyperHDR       │
                       │   5 V supply ──► Pi (5 V header) ──USB──► Pico (HyperSerialPico) ──data──►[LED]──┼──► strip
  mains ──►[IEC inlet]─┤       └────────────────────────── 5 V, GND ──────────────────────────►[LED]    │
                       │   status LED [●]                                                                 │
                       └──────────────────────────────────────────────────────────────────────────────────┘
```

## 2.2 Switch + splitter collapsed into one HDMI unit

Finding from the search (full table with 20 candidates in the research notes): **no HDMI 2.0 splitter or matrix on the market converts HDR to SDR on its downscaled output.** They all send 1080p *HDR* (BT.2020/PQ) to the capture card. HyperHDR's LUT tone mapping is therefore part of the design, not an option. The HyperHDR author says the same ([discussion 884](https://github.com/awawa-dev/HyperHDR/discussions/884)).

| Use case | Unit | Verified facts | Price (observed 2026-09-21) | Label |
|---|---|---|---|---|
| **One source (your PS5). Default.** | **EZCOO EZ-SP12H2** 1x2 splitter with per-output DIP-switch scaler | 4K60 4:4:4 HDR10 on OUT 1, OUT 2 scaled to 1080p60 keeping refresh; HDCP 2.2 in, unencrypted scaled out (the reason the ambilight community uses it); no ARC/eARC/CEC/VRR/4K120. Dolby Vision drops to HDR10 when the scaler is on. **Recommended by the HyperHDR author** ("still recommended", [884](https://github.com/awawa-dev/HyperHDR/discussions/884); wiki: TV on OUT 1 scaler off, grabber on OUT 2 scaler on). | Amazon [B07VP37KMB](https://www.amazon.com/SP12H2-4K-HDMI-Splitter-HDCP2-2/dp/B07VP37KMB), [easycoolav.com](https://www.easycoolav.com/products/4k60-hdmi-splitter-1x2-dolby-vision-hdr-scaler-edid-setting-sp12h2). Price not visible through the search proxy; historically $40 to $50. **Verify.** | COMM |
| Two to four sources, one unit | **OREI UHDS-402A** 4x2 matrix, or its successor **UHD-402D** | 4 in / 2 out, 18 Gbps, HDR10, "independent 4K to 1080p downscaling" per output, ARC on input 4 to output A, IR remote, auto-switch. DV/HDR10+ passthrough claimed on the unscaled output only. No ambilight community reports found. | [orei.com UHDS-402A](https://www.orei.com/collections/hdmi-matrix/products/uhds402a-4-in-2-hdmi-matrix-arc-support), [Amazon B07ZTWGBHL](https://us.amazon.com/OREI-Extraction-Management-Downscaling-UHDS-402A/dp/B07ZTWGBHL), [UHD-402D](https://www.orei.com/products/4k-4x2-hdmi-matrix-switch-with-arc-audio-extraction-hdr-downscaling-uhd-402d). Price not visible. | UNT (product claims only) |
| Two to four sources, proven parts | **Kinivo 550BN** 5x1 auto switch + EZ-SP12H2 | Switch: 4K60 HDR, DV, CEC ([Amazon B07CRWBPN4](https://www.amazon.com/Kinivo-Premium-5-Port-Switch-Remote/dp/B07CRWBPN4)). Two small PCBs inside the same enclosure; the switch's own 5 V adapter is replaced by the box supply. | Kinivo price not visible; historically $40 to $60 | COMM for the SP12H2, UNT for the combination |
| Budget matrix | Monoprice Blackbird 39667 4x2 | Output B only downscales; no ARC; "limited supply" on some pages | $124.99 [monoprice.com](https://www.monoprice.com/product?p_id=39667) | UNT |

**HDMI 2.1 option for PS5 4K120 / VRR:** **EZCOO EZ-SP12H21** 1x2, 48 Gbps. 8K60 / 4K120 / VRR / ALLM confirmed to OUT 1 by HyperHDR users ([1004](https://github.com/awawa-dev/HyperHDR/discussions/1004)); OUT 2 scales 4K120 to **1080p120**, which an MS2130 cannot accept, so the whole chain drops to 60 Hz unless the grabber is a 1080p120 unit (Elgato HD60 X or Ezcap 331). Reports of grainy output in some configurations and reboots when switching sources ([1505](https://github.com/awawa-dev/HyperHDR/discussions/1505)). Price **$79.99** (was $189.99) at [easycoolav.com](https://www.easycoolav.com/products/4k-120hz-hdmi-21-splitter-8k-60hz-1-in2-out-vrr-allm), observed 2026-09-21. **Price difference: about +$35 for the splitter plus +$60 to +$150 for a 1080p120 capture card.** Your Insignia F50 is a 4K60 panel without HDMI 2.1, so this option buys you nothing today.

**What happens to Dolby Vision:** with any of the units above, enabling the scaler on the capture output makes the source fall back to HDR10 (EZCOO manual and [1505](https://github.com/awawa-dev/HyperHDR/discussions/1505)). The Insignia F50 supports HDR10 and Dolby Vision; expect HDR10 while the box is in the chain. The Philips 8K box passes Dolby Vision; that is a parity gap and is recorded as such in docs/08.

**What happens to 4K120 / VRR behind an HDMI 2.0 unit:** the PS5 reads the EDID, sees 4K60 max, and silently settles at 4K60 with the 120 Hz and VRR toggles greyed out. No black screen ([FlatpanelsHD](https://www.flatpanelshd.com/focus.php?subaction=showfull&id=1607403735), [TechRadar](https://www.techradar.com/opinion/i-love-using-the-philips-hue-sync-box-with-my-tv-but-it-needs-an-hdmi-21-upgrade-for-ps5)).

## 2.3 Capture: MS2130 USB grabber, not a CSI board

| | MS2130 USB 3 dongle | TC358743 HDMI-to-CSI (Geekworm C790, Auvidea B102) |
|---|---|---|
| Latency, measured | ~50 ms at 1080p120, ~66 ms at 1080p60 by the HyperHDR author ([499](https://github.com/awawa-dev/HyperHDR/discussions/499), [729](https://github.com/awawa-dev/HyperHDR/discussions/729)) | Only Pi 5 frame-counted figure found: 166 to 250 ms glass-to-glass with ffplay ([Geekworm forum](https://geekworm.com/community/forum/topic/143212/c790-hdmitocsi2-module-high-latency-on-pi-5-)). Pi 4 users say "faster than USB" but publish no numbers |
| Pi 5 support | Plug and play (UVC) | Works only via `media-controller=1` and hand-wired `media-ctl` pipelines; kernel 6.12.53 regression broke it; no libcamera support ([RPi forum](https://forums.raspberrypi.com/viewtopic.php?t=365019), [6.12.53 report](https://forums.raspberrypi.com/viewtopic.php?p=2377728)) |
| Audio | USB audio class, 48 kHz stereo PCM; HyperHDR captures it ([866](https://github.com/awawa-dev/HyperHDR/discussions/866)) | I2S wiring plus `tc358743-audio` overlay; unverified on Pi 5 |
| HyperHDR support | First class; author's test firmware available | One user report on Pi 4 needing a watchdog script after each mode change ([1440](https://github.com/awawa-dev/HyperHDR/discussions/1440)); no maintainer response |
| Price | ~$10 to $15 generic ([eBay](https://www.ebay.com/itm/354397788289)); $20 to $30 branded (Hagibis [B0CMT5SNFQ](https://www.amazon.com/dp/B0CMT5SNFQ)) | ~$27 to $40 (C790 [Amazon B0B74JRGWM](https://www.amazon.com/dp/B0B74JRGWM)) |

**Recommendation: MS2130 in a blue USB 3 port, YUYV at 640x480x60 or 1280x720x60 (the author's recommended ambilight settings, [661](https://github.com/awawa-dev/HyperHDR/discussions/661)).** Leave brightness/contrast/saturation/hue at 0 on 2023+ firmware. Keep the MS2109 off the list: USB 2, MJPEG only, ~50 ms slower.

## 2.4 LED driver: a Pico inside the box, not the Pi's SPI

Phase 2 asked for the strip on the Pi's SPI. The search shows the HyperHDR author explicitly does **not** support that: "Direct driving ws2812b / sk6812 from Raspberry Pi is NOT officially supported ... does not work at all on Rpi5" ([320](https://github.com/awawa-dev/HyperHDR/discussions/320)); the Pi 5 PIO path needs root and a patched kernel ([wiki](https://github.com/awawa-dev/HyperHDR/wiki/Raspberry-Pi-5-PWM)). His supported LED path is a microcontroller running **HyperSerialPico** (RP2040) or **HyperSerialESP32** over USB at 2 Mbaud, with the `awa` protocol that includes frame checksums and a "data-not-received" watchdog.

So the box contains a **Raspberry Pi Pico** (about $4 to $5, label UNT for price) on a 10 cm USB lead to the Pi, plus the 74AHCT125 level shifter. Externally nothing changes: one LED lead. HyperHDR sees an `awa` serial device; that path is COMM.

WLED on an external ESP32 over Wi-Fi remains documented in docs/04 as the alternative for a Pi that cannot sit behind the TV.

## 2.5 Single power supply, sized for a 55" TV

**LED count for the Insignia 55" F50** (typical 55" panel about 123 x 71 cm without stand; measure yours, this is UNT until you do). Strip runs 5 cm inside the edge: 113 cm top, 61 cm sides.

| Layout | 60 LEDs/m | 96 LEDs/m |
|---|---|---|
| 3 sides (top + both sides, like the Hue gradient strip) | 68 + 37 + 37 = **142** | 108 + 58 + 58 = 224 |
| 4 sides | 210 | 332 |

Current budget, 5 V:

| Load | Worst case | Typical film content (25 %) |
|---|---|---|
| 142 x WS2812B at 60 mA | 8.5 A | 2.1 A |
| 210 x WS2812B | 12.6 A | 3.2 A |
| Pi 5 + Active Cooler + MS2130 + Pico | 3.0 A budget (usb_max_current_enable) | 1.2 A |
| HDMI unit (EZ-SP12H2, USB powered) | 0.5 A | 0.3 A |
| **Total, 3 sides** | **12.0 A** | **3.6 A** |
| **Total, 4 sides** | **16.1 A** | **4.7 A** |

**Build A (recommended, one mains cord): Mean Well LRS-100-5**, 5 V 18 A 90 W, fanless, 129 x 97 x 30 mm, $18.60 at [TME](https://www.tme.com/us/en-us/details/lrs-100-5/built-in-power-supplies/mean-well/) / $24.60 at [TRC](https://www.trcelectronics.com/products/mean-well-lrs-100-5) (2026-09-21). Trim the V-adj pot to **5.15 V** measured at the Pi header to absorb wiring drop. Mains enters through a fused, grounded IEC C14 inlet; the LRS terminal block gets its plastic cover and the earth (FG) terminal is wired to the inlet earth. This is a mains build: if you are not comfortable wiring an IEC inlet and a terminal block, use Build B.

**Build B (no mains inside the box): BTF-LIGHTING 5 V 10 A ETL-listed desktop brick**, 5.5 x 2.1 mm plug ([Amazon B0G4KXT4BL](https://www.amazon.com/BTF-LIGHTING-100-240V-Converter-5-5x2-1mm-Electronics/dp/B0G4KXT4BL), price not visible, historically $15 to $20). 10 A covers a 3-side 60/m build with HyperHDR's current limiter set to 6.5 A for the LEDs. Not enough for 4 sides. Still one cord to the wall; the brick sits inline. Use a barrel jack rated 10 A or a screw-terminal jack, not a 5 A hobby jack.

**Powering the Pi from the same 5 V rail:** through GPIO header pins 2/4 (5 V) and 6 (GND), the way the official PoE HATs do ([RPi PoE HAT design note](https://www.raspberrypi.com/news/designing-the-poe-hat-for-raspberry-pi-5-compact-efficient-power-and-networking/)). This bypasses USB-C PD negotiation and the input protection, so: 5.1 to 5.15 V at the header, a **3 A polyfuse** in the Pi feed, 18 AWG wire to a screw terminal or soldered header, never Dupont jumpers ([bret.dk power guide](https://bret.dk/how-to-power-the-raspberry-pi-5-a-complete-guide/)). Because there is no PD negotiation the Pi 5 caps USB peripherals at 600 mA; add `usb_max_current_enable=1` to `config.txt` (official docs, [power-supplies.adoc](https://github.com/raspberrypi/documentation/blob/master/documentation/asciidoc/computers/raspberry-pi/power-supplies.adoc)). The MS2130 draws under 500 mA. Label: COMM for the method, UNT for undervoltage-free operation until measured (acceptance test T9 and `vcgencmd get_throttled`).

**Protection and wiring:**

| Item | Value | Why |
|---|---|---|
| LED feed fuse | 10 A blade (3 sides) / 15 A (4 sides) | below wire rating, above worst case |
| Pi feed fuse | 3 A polyfuse | Pi 4/5 have no input fuse on the header |
| Capacitor | 1000 µF 6.3 V+ at strip input | inrush |
| Data resistor | 330 Ω at strip DIN | ringing |
| Level shifter | 74AHCT125, $0.40 at [Digi-Key](https://www.digikey.com/en/products/detail/texas-instruments/SN74AHCT125N/375798) | 3.3 V to 5 V data |
| LED feed wire | 18 AWG (up to 16 A over 1 m) | |
| Power injection, 3 sides at 60/m (2.4 m) | feed at strip start **and** at the far end | keeps the far end above 4.7 V; each side is its own segment joined at the corners |
| Power injection, 4 sides | start, opposite corner, end | |
| LED-lead connector on the box | GX16-4 aviation connector, two pins paralleled for 5 V, one GND, one data | rated well above 8 A when doubled |

## 2.6 Strip: density and zones

| Option | Pixels per metre | Current per metre (BTF spec) | Hot spots at 15 cm from the wall | Notes |
|---|---|---|---|---|
| WS2812B 60/m | 60 | 2.2 A (11 W) | none in a frosted channel | **Default.** 142 zones on 3 sides |
| WS2812B 96/m | 96 | 3.4 A | none | finer gradient than the eye resolves on a wall; 224 zones |
| BTF FCOB WS2812B 5 V 180 LEDs/m | 180 LEDs, fewer ICs | 2.8 A (14 W) | none, continuous light bar | best look, but pixel count per metre depends on IC grouping; BTF's page does not state it clearly |
| WS2811 COB 24 V | 1 pixel per 50 mm | 0.9 A at 24 V | none | only 20 zones/m and needs a 24 V rail: rejected |

Sources: [BTF WS2812B page](https://www.btf-lighting.com/products/ws2812b-led-pixel-strip-30-60-74-96-100-144-pixels-leds-m) (60/m = 11 W/m, 96/m = 17 W/m), [BTF FCOB WS2812B](https://www.btf-lighting.com/products/fcob-ws2812b-rgb-addressable-led-strip-180pixels). Prices were not visible through the search proxy; historically $20 to $25 per 5 m at 60/m. **Verify.**

Channel: Muzata U1SW 17 x 7 mm with frosted cover, 6 x 1 m for $28.65 ([eBay](https://www.ebay.com/itm/127849962662), [Amazon B01M09PBYX](https://www.amazon.com/Muzata-Aluminum-Mounting-Installations-Diffuser/dp/B01M09PBYX)). The wall is the real diffuser: mount the channel 5 to 8 cm inside the TV edge, LEDs facing the wall, TV 10 to 20 cm from the wall. Corners: 30 mm wire loops with 3-pin JST-SM, not rigid corner connectors.

**Zones versus the Hue gradient strip:** the Hue Play Gradient Lightstrip 55" has **7 independently addressable segments** (3 top, 2 per side) and exposes 7 channels in the Entertainment API ([Hueblog review](https://hueblog.com/2020/10/05/my-review-philips-hue-play-gradient-lightstrip/)). The 3-side 60/m build has 142. That is not a marginal difference: the Hue strip shows three colours across the top of a 55" TV, this shows sixty-eight.

## 2.7 Compute and small parts (prices observed 2026-09-21)

| Part | Price | Source |
|---|---|---|
| Raspberry Pi 5 2 GB | $65 MSRP (after the April 2026 increase; 4 GB is $110) | [raspberrypi.com](https://www.raspberrypi.com/news/a-new-3gb-raspberry-pi-4-for-83-75-and-more-memory-driven-price-increases/), [TechPowerUp](https://www.techpowerup.com/347927/raspberry-pi-announces-more-price-hikes-3-gb-raspberry-pi-4-sku) |
| Raspberry Pi 4 2 GB (alternative; 18 ms decode vs 4 ms, 30 s boot vs 20 s) | $45 to $50, exact current MSRP not verified | same announcement |
| Active Cooler (Pi 5) | $5 | [raspberrypi.com](https://www.raspberrypi.com/products/active-cooler/) |
| microSD 32 GB A2 | ~$8 | not searched |
| Raspberry Pi Pico | ~$4 to $5 | not searched (UNT) |
| MS2130 grabber | $10 to $30 | see 2.3 |
| EZCOO EZ-SP12H2 | ~$40 to $50 | see 2.2 |
| Mean Well LRS-100-5 | $18.60 to $24.60 | see 2.5 |
| IEC C14 fused inlet, cord | ~$8 | not searched |
| 74AHCT125 | $0.40 | Digi-Key |
| Panel-mount HDMI M-to-F screw-mount 30 cm cables x2 (4K60-rated; the Neutrik NAHDMI-W is HDMI 1.3 rated and is **not** suitable) | under $10 to $25 each | [StarTech HDMIPNLFM3](https://www.amazon.com/StarTech-com-Standard-Cable-Panel-Mount/dp/B0035PS59K), [Qaoquda B07WJGPQSW](https://www.amazon.com/Qaoquda-Extension-Support-Resolution-Xbox360/dp/B07WJGPQSW) |
| GX16-4 panel connector pair | ~$3 | not searched |
| WS2812B 60/m 5 m + Muzata channel 6-pack | ~$22 + $28.65 | see 2.6 |
| Fuses, polyfuse, capacitor, resistor, wire, JST leads, standoffs | ~$15 | |
| 3D-printed enclosure (docs/03) or Hammond 1591XXFBK 221 x 150 x 63.5 mm at $14.53 ([Digi-Key](https://www.digikey.com/en/products/detail/hammond-manufacturing/1591XXFBK/2094786)) | $10 to $15 | |
| **Total, Build A, 3 sides** | **about $260 to $300** | |
| **Total, Build B, 3 sides** | **about $250 to $290** | |

For comparison on the same day: Philips Hue Play HDMI Sync Box 8K **$384.99** at Philips US / Home Depot, $264.99 at Woot ([Home Depot](https://www.homedepot.com/p/Philips-Hue-Play-HDMI-Sync-Box-8K-for-TV-Gaming-and-Music-579755/341539657), [Woot](https://tools.woot.com/offers/philips-hue-play-hdmi-sync-box-8k-5)); the new single-input Sync Box 4K (September 2026) **$149.99** ([Hueblog](https://hueblog.com/2026/08/24/this-is-the-new-philips-hue-play-sync-box-lite/)); Hue Play Gradient Lightstrip 55" **$274.99** ([Philips](https://www.philips-hue.com/en-us/p/gradient/046677560409)). Philips total for a single-input setup: **about $425**. This build: about $270 with 20x the zones, or about $310 with the 4x2 matrix. The 2024 price rises on the Pi 5 ate most of the margin the earlier docs promised; the honest number is "40 % cheaper with far better lights", not "one third the price".

## 2.8 Cable plan and count

Behind the TV, Build A, single source:

```
 wall ──mains cord──►[IEC]  SYNC BOX  [HDMI IN 1]◄──HDMI──── PS5
                            [HDMI OUT]───HDMI────► TV HDMI 1
                            [LED GX16]───lead────► strip start (5V, GND, DATA)   + injection lead to strip end
                            [●] status
```

| | Philips Sync Box 8K + gradient strip | This build (A) |
|---|---|---|
| Boxes behind the TV | 1 (plus the Hue Bridge at the router) | 1 |
| Cables into the box | HDMI x (sources+1), USB-C power | HDMI x (sources+1), mains cord, LED lead |
| Wall plugs | 1 (plus bridge) | 1 |
| LED leads | 1 (strip plugs into its own power adapter: **2nd wall plug**) | 1 lead, no separate strip supply |
| Wi-Fi/Ethernet dependency for syncing | Zigbee via bridge | none (LAN only for the control page) |
