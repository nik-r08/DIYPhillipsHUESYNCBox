# 7. Acceptance tests: proving "as good as Philips"

Ground rule: measured beats estimated. Every row below is **pending user measurement** until a result with date, hardware and number is written into the Result column. Nothing in this repository has an HW result yet.

Targets and where they come from:

- Philips publishes **no latency or update-rate figure** for the Sync Box; reviews are qualitative ("no lag", TechRadar/Tom's Guide) and one rhythm-game player reported perceptible lag. The Hue Bridge forwards Entertainment data over Zigbee at about **25 Hz** for up to 10 channels; the Hue app streams at 50 to 60 Hz ([node-phea README](https://github.com/JakeBednard/node-phea), [Hyperion docs](https://docs.hyperion-project.org/user/leddevices/network/philipshue.html)). The Hue gradient strip has 7 zones.
- HyperHDR's author measured **~50 ms (1080p120) and ~66 ms (1080p60)** grabber-to-LED with an MS2130 ([499](https://github.com/awawa-dev/HyperHDR/discussions/499), [729](https://github.com/awawa-dev/HyperHDR/discussions/729)). A Pi-based Hue-Entertainment project reports 80 ms screen-to-light ([Harmonize](https://github.com/mcpcapital/harmonizeproject)).
- The ≤ 80 ms and ≥ 50 Hz targets therefore sit at the level the parts have already demonstrated in other people's hands, with margin.

## Pass / fail table

| # | Test | Target | Method / script | Result (date, hw, number) |
|---|---|---|---|---|
| T0 | Boot to sync | LEDs follow the screen ≤ 30 s after power-on, no peripherals | Stopwatch from plug-in to first colour change; `tools/tests/boot_time.sh` for the breakdown | pending |
| T1 | Screen-to-LED latency, Game mode | median ≤ 80 ms (stretch: ≤ 60 ms) | `gen_latency_video.py` on the source, phone at 240 fps, `latency_from_video.py` | pending |
| T2 | Sustained update rate | ≥ 50 updates/s for 8 h, zero gaps > 100 ms | `led_rate_monitor.py --hours 8` | pending |
| T3 | Passthrough integrity | TV reports identical resolution, HDR format, refresh, and the bar the same audio format, with and without the box | Checklist below | pending |
| T4 | Colour accuracy | Hue of wall glow within one named colour of the screen edge for R/G/B/C/M/Y; black stays black (no glow); no visible flicker over 2 min of solid colour | `gen_test_patterns.py`; phone photos, fixed exposure | pending |
| T5 | Black-bar detection | Letterbox and pillarbox bars ignored within 2 s; no misfire on the dark scene or the bright-object-on-black scene | `gen_test_patterns.py` sections 3 to 6; stopwatch | pending |
| T6 | Stability | 24 h loop, HyperHDR restarts = 0, `get_throttled` never non-zero, memory flat | `soak_logger.sh soak.csv 24` | pending |
| T7 | Recovery | a) power pulled mid-play, lights back ≤ 30 s unattended; b) Wi-Fi off 60 s, control page back ≤ 30 s after; c) source switched or woken, sync resumes ≤ 2 s | Manual with stopwatch; `journalctl -b -1` afterwards | pending |
| T8 | Thermal, closed box | 4 h, `get_throttled` = 0x0 throughout, CPU temp < 80 °C | `soak_logger.sh thermal.csv 4` with the lid on | pending |
| T9 | Power at the wall | Record W for: idle no signal, typical film, full white test frame. Expectation Build A: about 6 W / 15 to 25 W / 45 to 60 W | Plug-in power meter (Kill-A-Watt class) | pending |

## Per-test detail: what a fail looks like and the first thing to change

**T0 boot.** Fail: more than 30 s, or lights come up but stay on the ambient colour. First change: `systemd-analyze blame` and disable whatever is above HyperHDR; on a Pi 4 accept ~35 s or move to a Pi 5. If HyperHDR is up but the grabber is not, the MS2130 enumerated late: add `usbcore.autosuspend=-1` to `cmdline.txt`.

**T1 latency.** Setup: Game mode, Extreme, grabber 640x480 YUYV 60 fps, smoothing time 30 ms. Film both the TV and the wall in one frame at 240 fps for 20 s. Fail: median > 80 ms. First change, in order: confirm YUYV not MJPEG in HyperHDR's grabber page (MJPEG on USB 2 costs ~50 ms); reduce smoothing to 0 to isolate the pipeline; use HyperHDR's built-in latency benchmark to split grabber time from the rest. If the grabber alone is over 60 ms the dongle firmware is the issue: flash the HyperHDR-tested MS2130 firmware from the wiki.

**T2 update rate.** Fail: seconds below 50 Hz or gaps > 100 ms. First change: set smoothing `updateFrequency` to 50 (the default) rather than 60; check the Pico link is at 2 Mbaud with `espHandshake` on; check `dmesg` for USB resets. On a Pi 4 with 4 sides at 96/m the serial link itself needs 332 x 3 x 10 bits x 50 Hz = 0.5 Mbit/s, well inside 2 Mbaud.

**T3 passthrough.** Checklist: PS5 → Settings → Screen and Video → Video Output → shows resolution, HDR, refresh and "HDMI device information" (what the TV/box advertises). TV → Insignia/Fire TV: press the info button or Settings → Display & Sounds → Display → shows input signal (e.g. 3840x2160p 60 Hz HDR10). Sound bar: its display or app shows the incoming format (PCM/Dolby). Record all three with the PS5 into the TV directly, then through the box. Fail: any difference other than Dolby Vision → HDR10 (a documented, accepted gap, docs/08). First change: EDID mode on the splitter (EZ-SP12H2 DIP switches: OUT 1 scaler OFF, OUT 2 scaler ON; EDID "copy TV" if the unit offers it).

**T4 colour.** Photograph the screen edge and the wall glow in the same frame with a fixed manual exposure. Fail: a primary shows as the wrong named colour (red as orange, blue as purple); black test shows visible glow; flicker visible on solid colour. First change: for hue errors run HyperHDR's LUT calibration (HDR source) or set the grabber's colour range; for glow raise the black threshold (HyperHDR *Colour calibration → black level*); for flicker enable the anti-flicker filter and check the strip's 5 V at the far end under full white (< 4.5 V means power injection).

**T5 black bars.** Fail: LEDs light the bar area, or a dark scene makes the picture "shrink" (bars detected where there are none). First change: threshold 5 → 10 → 16 % (users with tone mapping needed 16 %, [issue 116](https://github.com/awawa-dev/HyperHDR/issues/116)); mode `letterbox` if only horizontal bars ever occur.

**T6 stability.** Fail: any HyperHDR restart, growing memory, or throttle flag. First change: read the journal around the restart. If it is a USB disconnect of the MS2130, it is power: check the header voltage (T9 conditions) and `usb_max_current_enable`. If it is a HyperHDR crash, update (`syncbox-update`) and report upstream with the log.

**T7 recovery.** a) Pull the mains cord at the box mid-film, wait 10 s, plug in. Fail: no lights after 30 s, or the wizard reappears (config lost: persistence bind mount failed) or a filesystem check runs (overlay not active). First change: `sudo syncbox-persist status`; if inactive, enable it and reboot. b) Turn the router off 60 s. Fail: control page unreachable after 30 s. First change: `nmcli connection show` autoconnect and the retry setting from the installer. c) Put the PS5 in rest mode, wake it. Fail: lights stay ambient > 2 s after the picture returns. First change: HyperHDR signal detection `wakeTime` to 500 ms; if the splitter itself takes > 2 s to re-sync, that is hardware and is recorded as such.

**T8 thermal.** Fail: `get_throttled` shows 0x80000 (throttled) or 0x8 (currently throttled), or temp ≥ 80 °C. First change: enlarge lid slots; then a 40 mm fan; then Build B (supply outside).

**T9 power.** Fail: header voltage < 5.0 V at full white (measure with a meter at pins 2/6), `get_throttled` 0x50000 (under-voltage occurred). First change: trim the LRS to 5.15 V; shorten/thicken the Pi feed wire; check the polyfuse is not a 1 A part.

## How to record a result

Append to the table: `2026-10-05, Pi 5 2GB + MS2130 + EZ-SP12H2, 142 LEDs, median 58 ms (n=20)`, and change the row's label in `docs/00-status.md` to HW. Attach the CSV or the phone clip in `results/` if you want it in the repository.
