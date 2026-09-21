# 1. Engine decision: HyperHDR

**Decision: HyperHDR v22 is the engine. This repository is the integration layer around it: hardware selection, enclosure, single-cord power, installer, appliance hardening, a phone-sized control page, acceptance tests and documentation. The Python pipeline written earlier is kept under `reference/python-pipeline/` as an "understand how it works" module and is not on the product path.**

Date: 2026-09-21. Evidence labels as in `docs/00-status.md` (HW / SYN / COMM / UNT).

## Comparison against the Phase 4 acceptance criteria

| Criterion (target) | HyperHDR | Custom Python pipeline | Winner |
|---|---|---|---|
| Screen-to-LED latency (≤ 80 ms Game mode) | Author-measured ~50 ms at 1080p120 and ~66 ms at 1080p60 with an MS2130 grabber on Pi 4/5 ([discussion 499](https://github.com/awawa-dev/HyperHDR/discussions/499), [729](https://github.com/awawa-dev/HyperHDR/discussions/729)); built-in "USB grabber latency benchmark" in the UI. **COMM** | Never measured on any hardware; estimated 60 to 120 ms. **UNT** | HyperHDR |
| Sustained update rate (≥ 50 Hz for 8 h) | Smoothing engine default 50 Hz update frequency, configurable ([schema](https://github.com/awawa-dev/HyperHDR/blob/master/sources/base/schema/schema-smoothing.json)); users run 60 Hz on Pi 5 ([661](https://github.com/awawa-dev/HyperHDR/discussions/661)). **COMM** | 30 Hz loop tested for 6 s on x86. **SYN** | HyperHDR |
| Frame decode cost | Pi 5 decodes 1080p120 NV12 in 4 ms, Pi 4 in 18 ms (author, [661](https://github.com/awawa-dev/HyperHDR/discussions/661)); C++ with SIMD. **COMM** | numpy on x86 ~1 ms per 256x144 frame; never profiled on ARM. **SYN** | HyperHDR |
| HDR tone mapping | 3D LUT HDR-to-SDR, auto-generated since v21, automatic HDR detection, LUT calibration wizard ([wiki](https://github.com/awawa-dev/HyperHDR/wiki/LUT-calibration)). Every verified splitter leaves HDR on the scaled output (docs/02), so this is mandatory, not optional. **COMM** | None. Saturation and black-threshold knobs only. | HyperHDR, decisively |
| Black-bar detection | Modes default / classic / osd / letterbox, thresholds, inconsistency counters, years of field use ([schema](https://github.com/awawa-dev/HyperHDR/blob/master/sources/base/schema/schema-blackborderdetector.json)). **COMM** | Symmetric-row heuristic tested on synthetic arrays only. **SYN** | HyperHDR |
| No-signal handling | Manual and automatic signal detection with learned "no signal" frame, sleep/wake timers, LED-off pause for the grabber ([schema-videoGrabber](https://github.com/awawa-dev/HyperHDR/blob/master/sources/base/schema/schema-videoGrabber.json)). **COMM** | Stale-frame timer and long-black timer. **SYN** | HyperHDR |
| Stability over days | Runs as a systemd template unit with `Restart=on-failure`, thousands of installs since 2020, release v22.0.0 on 2026-09-01 ([releases](https://github.com/awawa-dev/HyperHDR/releases/tag/v22.0.0.0)). **COMM** | Never run longer than 6 s. **SYN** | HyperHDR |
| Who fixes bugs | One active maintainer plus contributors, issue tracker, regular releases (v19 2023, v21 2025, v22 2026). | You, or nobody. | HyperHDR |
| Ease of updates | Official apt repository (`awawa-dev.github.io`), so `apt upgrade` updates it; .deb packages kept for rollback ([wiki](https://github.com/awawa-dev/HyperHDR/wiki/Installation)). **COMM** | `git pull` and hope. | HyperHDR |
| Hue Entertainment | API v2 since v19, gradient strips supported, per-light placement ([wiki](https://github.com/awawa-dev/HyperHDR/wiki/Hue-Entertainment-API-v2)). **COMM** | Written to the protocol, never connected to a bridge. **UNT** | HyperHDR |
| Audio reactive | ALSA capture, spectrum and pulse effects ([wiki](https://github.com/awawa-dev/HyperHDR/wiki/Audio-reactive)). **COMM** | FFT tested on sine waves. **SYN** | HyperHDR |
| Local control API | JSON-RPC on 8090 (HTTP), 19444 (TCP), MQTT; components, adjustments, effects, instances ([wiki](https://github.com/awawa-dev/HyperHDR/wiki/JSON-API)). **COMM** | Flask API tested with a test client. **SYN** | HyperHDR (and it lets this repo build the simple UI on top) |
| Understandability for learning | 100k+ lines of C++ | 1,200 lines of Python with tests | Python, which is why it stays in `reference/` |

The Python pipeline does not meet the bar on any production criterion on real hardware, because it has never been on real hardware. Even if it were tuned for months, it would still lack HDR tone mapping and a maintainer. The decision is not close.

## What HyperHDR does not do, and how this repo covers it

| Gap | Handling in this repo |
|---|---|
| Does not officially support driving WS2812B straight from the Pi. SPI is "not recommended" and the Pi 5 PIO path needs root and a patched kernel ([320](https://github.com/awawa-dev/HyperHDR/discussions/320), [Pi 5 PWM wiki](https://github.com/awawa-dev/HyperHDR/wiki/Raspberry-Pi-5-PWM)). The author's supported path is a $4 to $6 microcontroller running his HyperSerial firmware over USB. | A Raspberry Pi Pico running HyperSerialPico lives **inside the enclosure** on a 10 cm USB lead. From outside it is still one box, one LED lead. See docs/02. |
| No first-boot wizard, no phone-sized "on / mode / brightness" page; its UI is an engineer's UI. | `syncbox-ui`, a small page on port 80 that talks to HyperHDR's JSON-RPC. See docs/05. |
| No read-only filesystem, watchdog, mDNS, or update/rollback tooling. | The installer and image in `installer/` and `image/`. See docs/04 and docs/05. |
| Cannot switch the HDMI input. | The HDMI unit auto-switches to the last active source; HyperHDR follows whatever it captures. No software involvement. |
| HDMI-CEC needs the Pi's own HDMI output on a TV port. | Optional extra cable; default design relies on HyperHDR signal detection instead. See docs/05. |

## Verified constraints that shaped Phase 2

- HyperHDR does not officially support Pi 3 or Zero 2 W with USB grabbers (legacy USB controller corrupts colour) ([Getting started](https://github.com/awawa-dev/HyperHDR/wiki/Getting-started.-Needed-components)). Pi 4 or Pi 5 only.
- MJPEG is decoded in software (libjpeg-turbo). The MS2130 must be in a **USB 3** port to deliver YUYV and avoid MJPEG ([729](https://github.com/awawa-dev/HyperHDR/discussions/729)).
- The author recommends the EZCOO EZ-SP12H2 splitter and notes that a scaler alone is not enough for an SDR grabber; the LUT does the HDR-to-SDR work ([884](https://github.com/awawa-dev/HyperHDR/discussions/884)).
- Sound capture is fixed at 22050 Hz mono from any ALSA capture device; the MS2130's USB audio qualifies.
