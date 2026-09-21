# 6. Troubleshooting and limits

## NO SIGNAL / black preview

| Cause | Check | Fix |
|---|---|---|
| Wrong `/dev/video` | `tools/list_devices.sh` | set `capture.device` |
| HDCP on the source | PS5 with HDCP on shows black or a "no signal" pattern on the capture output | disable HDCP on the console; for apps that force it, see docs/02 §1.5 |
| Splitter output 2 is 4K and the card only takes 1080p (MS2109) | card LED off or `cap.read()` fails | use a downscaling splitter, or set the source to 1080p |
| Card wants a format you did not ask for | `v4l2-ctl -d /dev/video0 --list-formats-ext` | set `capture.fourcc: MJPG` and a listed size |
| Permission denied | user not in `video` group | `sudo usermod -aG video $USER`, re-login |
| Card enumerates, no frames after sleep/wake of the source | `capture_error` in status shows reopen attempts | normal; the capture thread reopens automatically |

## Washed-out or grey colours

- HDR source. Either a downscaling splitter that converts HDR to SDR, or set the console/app to SDR, or raise `saturation` to 1.6 to 2 and `black_threshold` to 20 to 30. HyperHDR's LUT-based tone mapping is the proper fix.
- Capture card set to "limited range" while the source outputs full RGB. Try both range settings on the console.
- MJPEG chroma subsampling: use 720p instead of 360p so the colour resolution at the edges is higher.

## Flicker, sparkle, first LED wrong colour, strip freezes

Almost always electrical:

1. No common ground between controller and strip.
2. No level shifter, or a slow one. Use the 74AHCT125.
3. Missing 330 ohm data resistor or a data wire longer than 30 cm from controller to strip.
4. Power supply too small or voltage sag: measure 5 V at the far end of the strip at full white. Below 4.5 V, inject power.
5. Wi-Fi packet loss: `outputs.wled` error field in `/api/status`, or WLED's "Realtime" indicator dropping. Move the ESP32, use a 2.4 GHz-only SSID, disable Wi-Fi sleep in WLED, or switch to Adalight over USB.

Software-side: raise `spatial_smoothing` to 2 and `tau_down` slightly; raise `black_threshold` if dark scenes sparkle.

## Colours look right on the preview but wrong on the strip

- Colour order: `outputs.spi.color_order` or WLED's colour order setting (GRB for WS2812B, RGB for some WS2811, GRBW for SK6812).
- White balance: `color_correction` defaults to `[255,176,240]` (WS2812B looks blue-green otherwise). Set `[255,255,255]` if your strip is already calibrated.

## The strip lights the wrong edge / runs backwards

Use **Calibrate** mode and fix `leds.start`, `leds.direction`, `leds.offset`. Direction is as seen from the **front** of the TV.

## Latency too high in games

- Capture at 720p60 (`capture.width: 1280, height: 720, fps: 60`).
- Mode Game, intensity High or Extreme.
- Ethernet on the Pi; WLED Wi-Fi sleep off; or Adalight over USB.
- Set `target_fps: 60`.
- A Pi 5 or a USB 3 card (MS2130) shaves 10 to 20 ms compared with MS2109 on USB 2.

## Letterboxed films light up the black bars

Black-bar detection needs the bars to be symmetric, darker than luma 18 and stable for 15 frames. Check `content_rect` in `/api/status`. If the film has a dark scene *and* bars, detection may release; that is by design (a dark scene is not a bar). Lower `border` slightly so zones sit inside the picture more.

## Audio does not open

- `sounddevice` needs `libportaudio2` (`setup_pi.sh` installs it).
- `Invalid sample rate`: MS2109 on an older kernel. Use `samplerate: 96000, channels: 1, ms2109_fix: true`. Kernels 5.9+ present it as 48 kHz stereo directly.
- `Device unavailable`: something else (HyperHDR, PulseAudio) holds it. `fuser /dev/snd/*`.
- Music mode works but nothing happens in video modes: enable `audio.react_in_video`.

## Hue

- Pairing returns "link button not pressed": press the bridge button, then click Pair within 30 s.
- Streaming starts but lights do nothing: another app holds the Entertainment Area (Hue Sync app, HyperHDR). Stop it. The bridge allows one streamer.
- Lights update but map to wrong zones: the Hue app positions are wrong or all at height 0; use `channel_map`.
- `python-mbedtls` fails to install: on the Pi use `sudo apt install libmbedtls-dev` first, or pip's binary wheel for aarch64. On failure the Hue output is skipped with an error in the log; everything else keeps running.
- DTLS handshake timeout: firewall between Pi and bridge, or wrong `client_key` (it must be the 32-hex-character string, not the app key).

## CPU too high on a Pi Zero 2 W

`capture.width: 320, height: 180` (or 640x360 YUYV instead of MJPG), `sample_width: 128`, `target_fps: 20`, disable the web preview polling by closing the browser tab.

## Known limits (by design)

- **No smart-TV app capture.** Physics of HDMI: the TV does not output its own picture. Use an external streaming stick.
- **HDMI 2.1 features** (4K120, VRR, 48 Gbps Dolby Vision) need an HDMI 2.1 splitter and the capture branch still gets 1080p60 at most.
- **CEC** frequently misbehaves through splitters; keep the TV remote's device control expectations low.
- **Latency** of 60 to 120 ms is inherent to USB capture. The official box is not dramatically better, but a PC-side solution with a GPU capture (Prismatik, HyperHDR on the PC) can do 20 to 30 ms for PC gaming.
- **HDCP** is a licence, not a technology you can buy off the shelf. What cheap splitters do with it is on you.
- **Hue Entertainment** tops out at about 25 updates per second and about 20 channels per area, so the Hue lights will always look "softer" than the strip. That is fine: the strip is the fine detail, the Hue lights are the room.
