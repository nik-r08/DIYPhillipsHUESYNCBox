# 0. Status audit: what is actually verified

Date of audit: 2026-09-21. Every feature and claim in this repository is labelled with one of four evidence levels:

| Label | Meaning |
|---|---|
| **HW** | Tested on real hardware by the repository author or by you. **Nothing in this repo has this label yet.** |
| **SYN** | Tested only in this repository's unit tests or with the synthetic/file video source on a Linux x86 container. Proves the logic, not the hardware. |
| **COMM** | Not tested here, but the same thing is done routinely by a named community project on the same hardware, with a link. |
| **UNT** | Untested or assumed. Written from documentation or memory. Treat as a hypothesis. |

Blunt summary: **the entire capture path, every LED output, and the Hue output have never run on a Raspberry Pi, a capture card, an ESP32 or a Hue Bridge in this project.** What has been proven is the maths and the plumbing in between.

## Python application (`pi/syncbox`)

| Feature | Level | Evidence |
|---|---|---|
| LED layout geometry (counts, start corner, direction, offset) | SYN | `tests/test_zones.py` |
| Zone mean-colour extraction (summed-area table) | SYN | matches brute force in `test_zones.py` |
| Black-bar detection (symmetric, hold-off, dark-scene rejection) | SYN | `test_processor.py` on synthetic luma arrays only. Never fed a real letterboxed capture |
| Asymmetric temporal smoothing, spatial blur, saturation, black threshold, gamma | SYN | `test_processor.py` |
| Scene-adaptive brightness | SYN | runs in the end-to-end synthetic test; no perceptual tuning on a wall |
| Intensity presets (subtle/moderate/high/extreme) | UNT | numbers chosen by judgement, never compared with the Hue app |
| Game/Video/Movie time constants | UNT | never watched on a real strip |
| V4L2 capture via OpenCV (`capture.py`, `open_v4l2`) | UNT | OpenCV `CAP_V4L2` + MJPG is standard, but this code path was never executed: the container has no `/dev/video*`. Only the `synthetic` and `file:` sources ran |
| Capture reopen after failures | UNT | logic exists, never triggered by a real device |
| No-signal detection (stale frame / long black) | SYN | `test_fallback_when_no_signal` uses a zero timeout, not a real dongle losing sync |
| Audio FFT bands, AGC, beat detection | SYN | `test_audio.py` with pure sine waves. Never run on real audio or a real ALSA device |
| `sounddevice` stream open / device selection / `ms2109_fix` | UNT | PortAudio present in the container but no input device; `AudioAnalyzer.start()` never returned True anywhere |
| Music visualiser | SYN | shape and range only |
| Engine loop, mode switching, fallback, hot config reload | SYN | `test_engine_and_web.py`, plus a 6 s CLI run with the web server |
| Web UI page and JSON API | SYN | Flask test client and curl; the HTML was never opened in a browser |
| Live LED preview canvas in the UI | UNT | JavaScript never executed |
| Hue pairing (`/api/hue/pair`, `tools/hue_pair.py`) | UNT | written to the CLIP v1 `POST /api` + `generateclientkey` contract; no bridge available |
| Hue Entertainment streaming (DTLS-PSK, v2 message format, channel-to-zone mapping) | UNT for the network path, SYN for the byte layout | `test_outputs.py` checks the serialised message. The python-mbedtls handshake code was written from the library README and never executed. Rate limiting, reconnection and `action: stop` untested |
| WLED DDP packet format | SYN + COMM | `test_outputs.py` checks header bytes; format matches WLED's `udp.cpp` (`DDP_TYPE_RGB24 = 0x0B`, 480 px per packet) |
| Sending DDP to a real WLED | UNT | socket `sendto` executed against 127.0.0.1 with nothing listening |
| Adalight framing | SYN + COMM | header checked in tests; the protocol is the one WLED and Hyperion use |
| Pi SPI WS2812B encoding (3 bits per bit at 2.4 MHz) | SYN + COMM | encoding checked in tests; same scheme Hyperion's `ws2812spi` device and many DIY drivers use |
| Pi SPI on a real Pi (`spidev`, bufsiz, Pi 5) | UNT | spidev not installed in the container |
| `setup_pi.sh` | UNT | never run on Pi OS; apt package names from memory |
| `syncbox.service` | UNT | never installed |
| Performance claim "about 3 ms per frame on a Pi 4" | UNT | measured on x86 in the container at roughly 1 ms; Pi 4 figure is extrapolated |
| Latency budget table in docs/03 | UNT | all figures are estimates from general knowledge, none measured |

## ESP32 firmware (`esp32/`)

| Feature | Level | Evidence |
|---|---|---|
| Compiles | UNT | PlatformIO registry was blocked in the build environment. Passed `g++ -fsyntax-only` against mock Arduino/FastLED headers, which catches typos but not API misuse |
| DDP receive, Adalight receive, fallback colour | UNT | never flashed |
| Recommendation to use WLED instead | COMM | WLED is a mature project; DDP and Adalight support are documented features |

## Hardware and documentation claims

| Claim | Level | Evidence |
|---|---|---|
| MS2109 / MS2130 dongles work as UVC devices on Linux and with ambilight software | COMM | HyperHDR wiki and Hyperion forums document both chips; not tested here |
| Cheap 4K splitters give an unencrypted second output | COMM (anecdotal) | widely reported in r/Hyperion and HyperHDR discussions; model-specific and unverified here |
| Splitter with downscaler gives 1080p on port 2 | UNT | product-category claim; no specific model verified in the original docs. Phase 2 replaces this with verified models |
| 74AHCT125 level shifting, 330 ohm resistor, 1000 uF capacitor, power injection every ~2.5 m | COMM | standard Adafruit NeoPixel Uberguide guidance |
| LED counts per TV size at 60/m | UNT | arithmetic on typical panel dimensions, not measured on your 55" Insignia |
| Power supply sizing (60 mA per LED, 20 to 30 % average) | COMM | Adafruit / WLED documentation |
| Prices in docs/01 | UNT | typical values from memory, not searched. Phase 5 replaces them with dated, searched prices |
| "Pi 4 handles 1080p30 MJPEG + processing at 30 fps" | COMM for HyperHDR, UNT for this code | HyperHDR publishes Pi 4 performance; this Python pipeline was never profiled on ARM |
| Pi Zero 2 W "15 to 20 fps at 320x180" | UNT | guess |
| PS5 HDCP toggle location | COMM | Sony support pages |
| HDMI 2.0 splitters cap PS5 at 4K60; Dolby Vision often breaks | COMM (partial) | widely reported; model-specific verification pending in Phase 2 |
| HyperHDR feature list in docs/05 | COMM, to be re-verified | written from memory of the HyperHDR wiki; Phase 1 re-checks each item with sources |
| Hue Entertainment 25 Hz recommendation, ~20 channels per area | UNT | from memory of the Hue developer docs; to be re-verified in Phase 4 |

## What this means for the product

- Nothing here should be sold as working until the acceptance tests in `docs/07-acceptance-tests.md` have been run on real hardware and recorded.
- The Python pipeline is a correct implementation of the algorithms, but "correct on x86 with a synthetic source" is a long way from "runs for months behind a TV". That gap is the reason Phase 1 chooses the engine on evidence, not on authorship.
- Every future claim in this repo carries one of the four labels above, and `HW` requires a recorded test result (date, hardware, method, number).
