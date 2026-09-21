# 5. The fast path: HyperHDR + WLED, no code

If you want the result rather than the project, the same hardware runs **HyperHDR** on the Pi with **WLED** on the ESP32. It covers every feature in the requirements list and has years of tuning behind it.

| Requirement | HyperHDR feature |
|---|---|
| Real-time colour extraction from HDMI | USB grabber support (MS2109/MS2130 tested by the project), hardware-accelerated MJPEG decoding, black-bar detection |
| Smoothing | Smoothing with configurable time, "anti-flickering" filters |
| Audio reactivity | "Sound capture" effects: spectrum, VU meter, bass pulse, from any ALSA input (the capture card or a USB sound card) |
| Brightness by content | Colour calibration, gamma, brightness compensation, and an HDR tone-mapping LUT that fixes washed-out HDR captures |
| Multiple modes | Presets for smoothing and instance settings; switchable via its JSON API |
| Web/mobile config | Full web UI on port 8090 |
| Static fallback | Effects and colours with priority; a static colour at low priority shows whenever the grabber has no signal |
| Hue integration | Philips Hue Entertainment API v2 output, with per-light placement |
| Addressable LEDs | WLED (UDP), Adalight serial, and dozens of others |

## Steps

1. Flash WLED on the ESP32 exactly as in docs/04 step 4.
2. On the Pi: download the `.deb` for Raspberry Pi OS from <https://github.com/awawa-dev/HyperHDR/releases> and `sudo apt install ./HyperHDR-*.deb`, then `sudo systemctl enable --now hyperhdr@pi`.
3. Open `http://syncbox.local:8090`.
4. **LED Hardware**: controller type "wled", target `wled.local`, LED count. Use the LED layout wizard to enter counts per edge and the start corner.
5. **Capturing Hardware**: pick the USB grabber, MJPEG, 1280x720 at 30 or 60 fps. Turn on "HDR to SDR tone mapping" if you feed it HDR.
6. **Image Processing**: smoothing 100 to 200 ms for films, 30 ms for games. Black border detection on.
7. **Effects > Sound capture**: choose the audio device; try "Music: Pulse". Assign to a priority above the grabber to make a music mode.
8. Hue: **LED Hardware > controller type "philipshue"**, pair with the bridge button, select the Entertainment Area, enable "Use Hue Entertainment API".

## Alternative: diyHue

[diyHue](https://diyhue.org) emulates a Hue Bridge. Register your WLED strip in it and the **official Hue apps**, the Hue Sync desktop app, and even a real Hue Sync Box will treat the WLED strip as a Hue gradient light. Useful if you already have the official box and only want cheaper lights.

## Why this repository exists anyway

- To explain what the box actually does, in a few hundred lines you can read in an afternoon.
- To be hackable: custom effects, unusual layouts, integration with your own home automation, or a Python project to learn on.
- HyperHDR is the better product. This is the better textbook. Use whichever you need, and the hardware is the same.
