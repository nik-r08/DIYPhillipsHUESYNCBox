# 4. Setup guide

Assumes the hardware from docs/01 is on your desk and the strip is wired per docs/02.

## Step 1: Raspberry Pi OS

1. Raspberry Pi Imager → Raspberry Pi OS **Lite (64-bit)**, Bookworm or newer. In the Imager's settings set hostname `syncbox`, enable SSH, set your user and Wi-Fi (or use Ethernet, preferred).
2. Boot, SSH in: `ssh pi@syncbox.local`.
3. `sudo apt update && sudo apt full-upgrade -y && sudo reboot`.

## Step 2: Install the software

```bash
sudo apt install -y git
git clone https://github.com/nik-r08/DIYPhillipsHUESYNCBox.git
cd DIYPhillipsHUESYNCBox/pi
./setup_pi.sh          # apt deps, venv, requirements, config.yaml
```

Log out and in again so the group changes (video, audio, spi, dialout) apply.

## Step 3: Check the capture card

```bash
../tools/list_devices.sh
```

You should see something like `USB Video: USB Video (usb-0000:01:00.0-1.3)` with `/dev/video0` and formats `MJPG` at 1920x1080 / 1280x720 / 640x480 and `YUYV`. If it lists only `/dev/video1`, set `capture.device: /dev/video1`.

Recommended capture settings:

| Card | Game mode | Movie/Video mode |
|---|---|---|
| MS2130 | 1280x720 MJPG 60 fps | 640x360 or 1280x720 MJPG 30 fps |
| MS2109 | 1280x720 MJPG 60 fps (USB 2 can sustain it) | 640x480 MJPG 30 fps |

Set them in `config.yaml` under `capture`. The card may only honour a few sizes; the software resizes whatever it gets.

Quick test without the LEDs:

```bash
./venv/bin/python -m syncbox --config config.yaml --no-audio -v
```

Open `http://syncbox.local:8080`. The preview panel should show the edges of whatever is on the TV. If it says NO SIGNAL, see docs/06.

## Step 4: Flash WLED on the ESP32

1. Plug the ESP32 into your computer, open <https://install.wled.me> in Chrome or Edge, click Install, pick the serial port. Enter Wi-Fi credentials when asked.
2. Open the WLED web UI (it prints its IP; `http://wled.local` usually works).
3. Config > LED Preferences: LED type WS281x, colour order GRB, count = your total LEDs, GPIO = 16 (or whatever you wired), enable the automatic brightness limiter, maximum current = 80 % of your supply in mA.
4. Config > Sync Interfaces: leave "Receive UDP realtime" on, set "Realtime timeout" to 2500 ms and, if you like, set a preset to return to. DDP is on by default.
5. Config > Wi-Fi: disable Wi-Fi sleep for lower latency.
6. Pick any effect from the main page and confirm the whole strip lights up. If the far end is dim or the colours are wrong, revisit docs/02 (power injection, colour order).

Or, to use the firmware in `esp32/`: install PlatformIO (`pip install platformio`), copy `esp32/src/secrets.h.example` to `secrets.h`, set your Wi-Fi, adjust `NUM_LEDS` and `DATA_PIN` in `platformio.ini`, then `pio run -e esp32dev -t upload`. It listens on DDP 4048 and on the serial port at 500000 baud. Note: the firmware in this repository could not be compile-checked in the environment it was written in (no access to the PlatformIO package registry). It is short and standard FastLED/WiFiUDP code, but treat the first build as yours to verify.

## Step 5: Point the Pi at the strip

In `config.yaml` (or the web UI, Outputs card):

```yaml
outputs:
  wled:
    enabled: true
    host: wled.local        # or the IP
    leds: 0                 # 0 = same as the layout below
leds:
  top: 83
  right: 46
  bottom: 83
  left: 46
  start: bottom-left
  direction: clockwise
```

Start the program and click **Calibrate** in the web UI. The strip should show: top edge red, right green, bottom blue, left yellow, and the first three LEDs white.

- White LEDs not at the corner you expected → change `start`.
- Colours run the wrong way round → flip `direction`.
- Colours start a few LEDs past the corner → set `offset`.
- Top and bottom counts look swapped → you are counting from behind the TV; `direction` is defined from the *front*.

## Step 6: Tune the picture

Play something colourful (a nature documentary, a bright game). In the web UI:

1. Mode **Video**, intensity **High** as a baseline.
2. **Saturation** 1.2 to 1.6 until the wall colour matches the screen edge.
3. **Black threshold** up until dark scenes go fully dark instead of dim grey.
4. **Border**: 0.06 to 0.10. Smaller follows the extreme edge of the picture; larger averages more and flickers less.
5. **Smoothing**: Game mode for controllers, Movie mode for films. Adjust attack/release per mode.
6. **Spatial smoothing** 1 or 2 hides MJPEG blockiness.
7. **Scene-adaptive brightness** on for films, off for a constant-brightness gaming setup.

## Step 7: Philips Hue

1. Hue app → Settings → Entertainment areas → create one containing the lights near the TV. Place each light on the map where it physically sits (this is what the mapping uses).
2. In the web UI enter the bridge IP (or leave blank for discovery), **press the physical button on the bridge**, click **Pair** within 30 seconds.
3. Click **List entertainment areas**, choose yours, tick **Hue enabled**.

Or from the command line: `python3 tools/hue_pair.py` prints the keys and areas to paste into `config.yaml`.

Notes:

- The Hue Bridge v2 (square) is required. Entertainment streaming does not exist on the round v1 bridge.
- Only one app can stream to a bridge at a time. Stop the Hue Sync desktop/mobile app first.
- The mapping uses the light's position: x for left/right, z (height) for up/down, or y if all heights are zero. To hand-assign, set `outputs.hue.channel_map: {"0": 120, "1": 40}` (channel id → LED index).
- Rate is limited to `max_rate` (25 Hz) as Philips recommends.
- The bridge presents a self-signed certificate; the code does not verify it. If you want to, download Philips' root CA and pass it as `verify=` in `hue_entertainment.py` and `hue_pairing.py`.

## Step 8: Audio

1. `../tools/list_devices.sh` shows the audio inputs. The capture card is usually `hw:1,0`; sounddevice lists an index.
2. `config.yaml`:

```yaml
audio:
  enabled: true
  device: 1           # index from sounddevice, or a name substring like "USB Video"
  samplerate: 48000
  channels: 2
```

3. If the stream fails to open with "Invalid sample rate", the card is an MS2109 on an older kernel: set `samplerate: 96000, channels: 1, ms2109_fix: true`.
4. Try mode **Music** with something rhythmic. Adjust `sensitivity`. Then go back to Video and enable **React in video modes**.

## Step 9: Autostart

```bash
sudo cp syncbox.service /etc/systemd/system/
# edit the paths in the unit if your user or clone location differs
sudo systemctl daemon-reload
sudo systemctl enable --now syncbox
journalctl -u syncbox -f
```

## Step 10: Optional extras

- **Home Assistant**: a `rest_command` to `/api/mode` and `/api/config` gives you mode buttons and a brightness slider on your dashboard. WLED itself has a native HA integration for on/off and presets.
- **TV power sync**: WLED's realtime timeout already blanks or resets the strip when the Pi stops sending. To turn the strip off when the TV is off, set `fallback.when_no_signal: off` (the splitter stops the capture signal when the source sleeps).
- **Remote control**: the web UI works on a phone; add it to the home screen.
