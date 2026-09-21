# 1. Hardware and bill of materials

## Design decisions in one paragraph

Video capture is the hard part, so it gets a Raspberry Pi. LED timing is fiddly, so it gets an ESP32 (or the Pi's SPI peripheral, which is a hardware shift register and therefore also timing-exact). Everything talks over plain UDP, serial or the Hue API, so any part can be swapped. The HDMI chain uses off-the-shelf boxes because building an HDMI receiver is not a DIY-scale job.

## Full parts list

### Compute

| Part | Notes | Approx. |
|---|---|---|
| **Raspberry Pi 4 Model B, 2 GB** (recommended) | Enough for 1080p30 MJPEG decode + processing at 30 fps with CPU to spare. USB 3 ports for the MS2130 card. Wired Ethernet keeps Wi-Fi free for the LEDs | $45 |
| Raspberry Pi 5, 4 GB | Faster, more expensive, needs the 27 W supply and active cooler. Only worth it if you also want to run other things | $60 + $12 cooler + $12 supply |
| Raspberry Pi Zero 2 W | Budget option. Expect 15 to 20 fps at 320x180; fine for Movie mode, borderline for Game mode. USB 2 only, needs a micro-USB OTG adapter | $15 |
| microSD card, 32 GB, A1 class | | $8 |
| Official Pi power supply | Cheap phone chargers cause under-voltage throttling | $8 to $12 |
| Optional: Pi case with fan | The Pi runs at 30 to 50 % CPU continuously | $8 |

### HDMI chain

| Part | Notes | Approx. |
|---|---|---|
| **USB HDMI capture dongle, MacroSilicon MS2130** | 1080p60 MJPEG or YUYV over USB 3.0, standard UVC (no drivers on Linux, Windows or macOS). Search "USB 3.0 HDMI video capture 1080p60 MS2130". Usually sold as a small stick with a female HDMI input | $20 to $30 |
| USB HDMI capture dongle, MacroSilicon MS2109 | The famous $10 stick. Labelled "USB 3.0", actually USB 2.0: 1080p30 or 720p60 MJPEG. Perfectly usable, slightly higher latency. Audio quirk: older kernels see it as 96 kHz mono (see docs/06) | $10 to $15 |
| **HDMI 1x2 splitter, 4K60 HDR, with downscaler** | Look for "1 in 2 out, 4K@60Hz, HDR, scaler" or "one output 4K one output 1080p". The downscaler means the TV gets the full 4K HDR signal while the capture card gets clean 1080p SDR. Most units in this class pass HDR10 and 5.1 audio, most break Dolby Vision | $25 to $40 |
| HDMI 1x2 splitter, 4K60, no scaler | Works if your capture card accepts 4K input (MS2130 does, and scales it internally). Cheaper | $15 to $25 |
| HDMI switch 3x1 or 4x1, 4K60, auto-switch | Only if you have more sources than you want to plug and unplug. Auto-switch models select whichever source is powered on | $15 to $30 |
| HDMI 2.1 splitter (8K/4K120) | Only needed for PS5/Xbox 4K120 or VRR. Same reason the official box comes in an "8K" version | $60 to $120 |
| Short HDMI 2.0 cables x3 | 0.5 m to 1 m. Certified "Premium High Speed" | $5 each |

### LEDs and power

| Part | Notes | Approx. |
|---|---|---|
| **WS2812B strip, 5 V, 60 LEDs/m, 5 m, IP30 (bare)** | The default. 5 m = 300 LEDs, enough for a 75" TV. IP30 (no silicone) is easier to cut and glue. Black PCB looks better behind a TV | $18 to $25 |
| WS2812B 30 LEDs/m | Half the LEDs, half the current, coarser colour resolution. Fine for a 55" TV | $12 |
| SK6812 RGBW | Adds a white channel for a nicer neutral white in Static mode. WLED supports it; this repo's SPI output does not | $25 |
| WS2815, 12 V | Same protocol, 12 V supply so far less voltage drop over 5 m and no power injection needed. Has a backup data line. Needs a 12 V supply and a 12 V to 5 V buck for the ESP32 | $25 |
| COB strip (WS2811/WS2812 COB, 5 V) | Diffused, dot-free light. Draws 2 to 3x the current | $30 |
| **5 V 10 A switching supply** (50 W) | Sizing: 300 LEDs x 60 mA = 18 A worst case at full white. Ambilight content averages 20 to 30 % of that, and both WLED and this firmware have a current limiter. 10 A is comfortable with the limiter set to 8 A; buy 20 A if you refuse to limit | $12 to $18 |
| **74AHCT125** quad level shifter, DIP-14 | Shifts the 3.3 V data from the ESP32 or Pi to 5 V. Cheap, fast, the classic choice. SN74HCT245 also works. Do not use the slow bidirectional I2C-style shifters (BSS138 boards) | $1 to $3 |
| 1000 uF, 6.3 V or higher electrolytic capacitor | Across the strip's 5 V and GND at the input end, absorbs the inrush | $0.50 |
| 330 to 470 ohm resistor | In series with the data line, right at the strip | $0.10 |
| 18 AWG (0.8 mm2) silicone wire, red/black, 3 m | Power runs. 22 AWG for the data line | $6 |
| 3-pin JST-SM connectors, 5 pairs | Strip segments at the corners | $4 |
| Inline blade-fuse holder + 10 A fuse | On the supply's 5 V output | $3 |
| 5.5x2.1 mm DC barrel jack with screw terminals | If your supply has a barrel plug | $1 |
| **ESP32 DevKit (ESP32-WROOM-32)** | Any 30- or 38-pin DevKit. ESP32-S3 boards also work with WLED. Avoid the ESP32-C3 for large strips | $5 to $8 |
| Optional: 12 V to 5 V buck converter (3 A) | Only for WS2815 builds | $3 |
| Aluminium LED channel with frosted diffuser, 1 m x 5 | Optional but the difference is visible: even glow instead of dots on the wall | $15 to $25 |
| 3M VHB tape / cable clips | | $5 |

### Audio (optional)

The HDMI capture card already exposes the HDMI audio as a USB microphone, so **you need nothing extra** for audio reactivity. Buy one of these only if you want the sound bar's own output (for example a Bluetooth source playing through the sound bar):

| Part | Notes | Approx. |
|---|---|---|
| USB sound card with 3.5 mm line/mic input | Any "USB audio adapter" with a pink input. Feed it from the sound bar's headphone or line-out | $8 |
| TOSLINK optical to 3.5 mm analog DAC | For sound bars with only an optical out. Then into the USB sound card above | $10 to $15 |
| I2S MEMS microphone (INMP441) on the ESP32 | Not used by this repo, but WLED's audio-reactive usermod supports it if you want the ESP32 to do the audio itself | $3 |

### Tools

Soldering iron, wire strippers, heat-shrink, a multimeter. If you do not solder, buy strips with pre-attached JST connectors and use screw-terminal adapters.

## Where to buy

- **Pi and official accessories**: rpilocator.com finds stock; The Pi Hut, Pimoroni, Adafruit, PiShop, CanaKit, Reichelt, Berrybase.
- **Capture cards, splitters, switches**: Amazon, AliExpress. Search by chip name (MS2130, MS2109) rather than brand; the brands change weekly, the chips do not.
- **LEDs, ESP32, level shifters, power supplies**: AliExpress (BTF-Lighting store is well regarded for WS2812B), Amazon (BTF-Lighting, ALITOVE), Adafruit (74AHCT125 breakout, NeoPixel strips at a premium), Digi-Key / Mouser for the 74AHCT125 DIP and capacitors.

## Budget tiers

| | Budget | Recommended | Deluxe |
|---|---|---|---|
| Compute | Pi Zero 2 W ($15) + SD + supply ($16) | Pi 4 2 GB ($45) + SD + supply ($18) | Pi 5 4 GB + cooler + supply ($84) |
| Capture | MS2109 ($12) | MS2130 ($25) | MS2130 ($25) |
| Splitter | basic 4K 1x2 ($18) | 4K with downscaler ($30) | HDMI 2.1 4K120 splitter ($90) |
| LED driver | none, strip on Pi SPI ($0) | ESP32 ($6) | ESP32 ($6) |
| Strip | WS2812B 5 m 30/m ($12) | WS2812B 5 m 60/m ($22) | WS2815 12 V 5 m + buck ($28) |
| Power | 5 V 10 A ($14) | 5 V 10 A ($14) | 12 V 5 A ($15) |
| Misc | shifter, cap, wire, fuse ($10) | + connectors, channel ($30) | + channel, case ($40) |
| Cables | ($10) | ($15) | ($15) |
| **Total** | **about $107** | **about $165** | **about $303** |

The Deluxe tier is only there to show that even with an HDMI 2.1 splitter for 4K120 you land near the price of the official box alone, with the lights included.
