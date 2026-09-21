# 4. Install

Two ways in. Both end with the box booting straight into sync and the setup wizard at `http://syncbox.local/`.

## A. Flash the image (recommended once an image has been built and tested)

1. Build or download `syncbox-*.img.xz` (see `image/README.md`; no pre-built image is published yet, label UNT).
2. Raspberry Pi Imager → Use custom → pick the image → gear icon: set Wi-Fi (or use Ethernet), keep user `pi`.
3. Insert the card, power the box, wait about 25 s, open `http://syncbox.local/` on your phone.

## B. One-line installer on Raspberry Pi OS Lite 64-bit (Bookworm or Trixie)

```bash
curl -fsSL https://raw.githubusercontent.com/nik-r08/DIYPhillipsHUESYNCBox/main/installer/install.sh | sudo bash
sudo reboot
```

Label UNT: written against the documented HyperHDR apt repository and Pi OS conventions, not yet run on a Pi. It is idempotent and logs to `/var/log/syncbox-install.log`. What it does is listed at the top of the script.

Then, on the phone:

1. **Wizard step 1**: TV size and sides. It suggests LED counts for 60/m; correct them to what you mounted.
2. **Step 2**: counts, start corner, direction. "Send layout" writes the HyperHDR LED geometry and the grabber, smoothing, black-bar and LED-driver defaults from `installer/hyperhdr-defaults.json`.
3. **Step 3**: calibration colours. Then open HyperHDR (port 8090) once: *LED Hardware* to confirm the `hyperserial` device found the Pico, *Video capturing* to confirm the MS2130 at 640x480 YUYV 60 fps, and run the **LUT calibration** wizard with an HDR source (docs/05 explains why).
4. **Step 4**: Hue, optional, in HyperHDR's own UI. Untested here.
5. **Finish**. Use it for a few days. Then lock the card: Advanced → or `sudo syncbox-persist enable && sudo reboot`.

## Flashing the LED driver (Pico)

1. Download `HyperSerialPico` firmware from the HyperHDR author's repository (https://github.com/awawa-dev/HyperSerialPico), the variant for WS2812B.
2. Hold BOOTSEL, plug the Pico into a PC, copy the `.uf2` onto the `RPI-RP2` drive.
3. The default data GPIO and LED count are set in the firmware's README; match `NUM_LEDS` to your total. Wire that GPIO to the level shifter.

Label COMM: this is the author's supported path; not performed here.

## WLED alternative (strip far from the box)

If the Pi cannot sit behind the TV, flash WLED on an ESP32 near the strip and set HyperHDR's LED device to `wled` (UDP) or `ddp` pointing at `wled.local`. The Pico and level shifter move out of the box. Everything else stays the same.
