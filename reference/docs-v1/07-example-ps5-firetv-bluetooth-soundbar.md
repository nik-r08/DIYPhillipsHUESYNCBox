# 7. Worked example: PS5 + Insignia 55" Fire TV + Bluetooth sound bar

One source, a smart TV, a wireless sound bar. This is the simplest possible chain: no HDMI switch, no audio cable.

## Before

```
 PS5 [HDMI OUT] ═══ HDMI ═══► TV [HDMI 1]
 TV ~~~ Bluetooth ~~~► sound bar
```

## After

```
 PS5 [HDMI OUT] ═══ HDMI #1 ═══► [IN] HDMI 1x2 SPLITTER (4K60, USB powered)
                                      ├─ [OUT 1] ═══ HDMI #2 ═══► TV [HDMI 1]           (4K HDR, unchanged)
                                      └─ [OUT 2] ═══ HDMI #3 ═══► USB HDMI CAPTURE DONGLE
                                                                        └─ USB ──► RASPBERRY PI [USB 3]
                                                                                     ├─ Ethernet/Wi-Fi ──► router
                                                                                     └─ Wi-Fi ──► ESP32 ─► level shifter ─► LED STRIP
                                                                        5V/10A PSU ─────────────────────────────► LED STRIP + ESP32 VIN/GND
 TV ~~~ Bluetooth ~~~► sound bar   (unchanged)
 phone ── Wi-Fi ──► http://syncbox.local:8080
```

| # | From | To | Cable |
|---|---|---|---|
| 1 | PS5 HDMI OUT | Splitter IN | existing HDMI |
| 2 | Splitter OUT 1 | TV HDMI 1 | short HDMI |
| 3 | Splitter OUT 2 | Capture dongle IN | short HDMI |
| 4 | Capture dongle | Pi blue USB 3 port | built in |
| 5 | Splitter power | wall or TV USB port | included micro-USB/USB-C |
| 6 | Pi | wall | official USB-C supply |
| 7 | LED PSU 5V/GND | strip 5V/GND via fuse, capacitor at strip | 18 AWG |
| 8 | LED PSU 5V/GND | ESP32 VIN/GND | 22 AWG |
| 9 | ESP32 GPIO16 | 74AHCT125 in; out via 330 ohm to strip DIN | 22 AWG, short |
| 10 | Pi to ESP32 | Wi-Fi (optional USB cable for Adalight) | |

## Notes for this setup

- Audio reactivity uses the HDMI audio captured by the dongle. The Bluetooth sound bar needs no wiring, and its Bluetooth delay does not affect the lights.
- Fire TV built-in apps do not pass through the splitter and cannot be synced. Use the PS5's streaming apps, or later add a Fire TV Stick into a small HDMI switch in front of the splitter.
- PS5: Settings > System > HDMI > Enable HDCP off for games.
- The TV is 4K60 without HDMI 2.1, so a basic 4K60 splitter loses nothing.
- Splitter, dongle, Pi and ESP32 all sit behind the TV.
