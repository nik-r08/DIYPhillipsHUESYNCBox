# 5. Appliance behaviour: nobody touches it after setup

Each behaviour lists the mechanism and its evidence label. Numbers marked **pending user measurement** have a test in docs/07.

| Requirement | Mechanism | Label / measurement |
|---|---|---|
| Boots to lights-following-screen, no monitor/keyboard/SSH, < 30 s | Pi OS Lite; HyperHDR and syncbox-ui are systemd services enabled at install; `boot_delay=0`, Bluetooth off, swap off, no wait-online. Pi 5 Lite stock boots to login in about 20 to 22 s, Pi 4 about 30 to 35 s ([Cytron measurement](https://www.cytron.io/tutorial/raspberry-pi-5-vs-raspberry-pi-4-boot-time)); HyperHDR starts within a couple of seconds after that. | COMM for the OS figure; **pending user measurement** (test T0, `tools/tests/boot_time.sh`). Pi 4 may miss 30 s; Pi 5 is the spec. |
| Survives power cuts | `overlayroot` read-only root (raspi-config's Overlay File System) with HyperHDR data bind-mounted from the writable FAT boot partition (`installer/persist.sh`); journald in RAM; hardware watchdog `bcm2835_wdt` with `RuntimeWatchdogSec=14` (15 s hardware max); every service `Restart=always/on-failure`. | COMM for overlayroot and watchdog ([RPi resilient FS whitepaper](https://pip.raspberrypi.com/categories/685-whitepapers-app-notes/documents/RP-003610-WP/Making-a-more-resilient-file-system.pdf), [systemd 27427](https://github.com/systemd/systemd/issues/27427)); UNT for the bind-mount trick. Known risk: Bookworm's overlay option had a reported Pi 5 bug ([bookworm-feedback 383](https://github.com/raspberrypi/bookworm-feedback/issues/383)); test T7 covers it. |
| Lights off / ambient when no HDMI signal; resume within 2 s | HyperHDR `autoSignalDetection` learns the grabber's no-signal frame; `sleepTime` 5 s, `wakeTime` 1 s defaults; `led_off_pause` idles the grabber. The wizard writes these defaults. Ambient colour: set a low-priority colour in HyperHDR (priority 254) and it shows whenever the grabber is muted. | COMM ([schema-videoGrabber](https://github.com/awawa-dev/HyperHDR/blob/master/sources/base/schema/schema-videoGrabber.json)); **pending user measurement** (T7c). Resume time is bounded by the splitter's re-sync (1 to 3 s) more than by software. |
| HDMI-CEC turns the strip on and off with the TV | `syncbox-cec` (cec-ctl monitor → power API). **Only works if the Pi's own HDMI output is plugged into a TV input**: CEC physical addresses come from the sink's EDID, otherwise the adapter stays at f.f.f.f and cannot transmit ([kernel CEC doc](https://docs.kernel.org/admin-guide/media/cec.html), [Arch wiki](https://wiki.archlinux.org/title/HDMI-CEC)). That costs one more HDMI cable and a TV port; the default one-box design does not include it and relies on signal detection instead (TV off → source sleeps → no signal → lights off). Pi 5 has an open CEC bug on Trixie/6.18 ([linux 7485](https://github.com/raspberrypi/linux/issues/7485)). | COMM for the mechanism; the service is UNT. |
| Sync follows whichever input is active | Done in hardware: the EZCOO or OREI unit auto-switches to the last active source; HyperHDR captures whatever comes out. No software step. With the 4x2 matrix the IR remote also selects inputs. | COMM (product behaviour) |
| `syncbox.local`, Wi-Fi reconnect, no internet, no cloud | avahi-daemon; NetworkManager with `autoconnect-retries-default=0` (retry forever) and Wi-Fi power save off; nothing phones home; the control page and HyperHDR are LAN only. Syncing itself needs no network at all. | COMM |
| Phone-sized UI with only the essentials; advanced page; first-boot wizard | `syncbox-ui` on port 80: power, Game/Video/Movie/Music, Subtle/Moderate/High/Extreme, brightness, status line. Matches the Hue app's sync controls (mode, intensity, brightness, on/off; Hue's "input" selector has no equivalent because switching is automatic). Advanced links to HyperHDR, diagnostics, update, rollback, reboot. | SYN: 5 tests against a fake HyperHDR (`tools/tests/test_ui.py`). The exact HyperHDR `setconfig` section names come from the v22 schema files; the first real run will tell. |
| One command to update, and rollback | `sudo syncbox-update` (apt HyperHDR + repo files, keeps the previous .deb); `sudo syncbox-rollback` (reinstalls it and holds the package). Both refuse to run while the card is read-only and say how to unlock. | UNT |
| Hue Bridge pairing and Entertainment Area alongside the strip | HyperHDR's built-in Philips Hue Entertainment API v2 output, as a second LED instance. Wizard step 4 opens it. | COMM for HyperHDR; **untested in this project until you confirm**. |
| Flashable image and one-line installer | `image/build.sh` (pi-gen stage) and `installer/install.sh`. | UNT |

## Why the LUT calibration is not optional

Every verified splitter sends 1080p **HDR** to the capture card (docs/02). The MS2130 then delivers washed-out BT.2020/PQ frames. HyperHDR's HDR-to-SDR LUT fixes that; since v21 it generates a default LUT itself, and the calibration wizard tunes it to your specific grabber firmware in about a minute using a test video played from the source ([wiki](https://github.com/awawa-dev/HyperHDR/wiki/LUT-calibration)). Do this once, with an HDR source active. With SDR-only sources (PS5 with HDR off) skip it.

## Status LED

GPIO17: solid = syncing; slow breathing = no HDMI signal; fast blink = engine offline; dim = lights switched off by the user.

## What still needs a person

- LUT calibration once, and again if you swap the capture dongle.
- Re-running `syncbox-persist disable` before any OS change, and `enable` after.
- Replacing the microSD card every few years (RAM-only journal and read-only root make this rare, not impossible).
