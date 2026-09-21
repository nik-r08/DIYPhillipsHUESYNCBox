# 3. Enclosure

Two ways to house Build A (internal Mean Well supply) or Build B (external brick):

1. **3D-printed case** from `hardware/enclosure.scad` (OpenSCAD, parametric). Print base and lid in PETG or ASA (PLA softens near a 30 W supply in a warm cabinet). About 300 g of filament.
2. **Off-the-shelf ABS box**, Hammond 1591XXFBK, 221 x 150 x 63.5 mm, $14.53 at [Digi-Key](https://www.digikey.com/en/products/detail/hammond-manufacturing/1591XXFBK/2094786) (observed 2026-09-21), using the drilling template in 3.3. It is 29 mm shorter than the printed case, so Build A only fits if the EZ-SP12H2 is stood on edge or moved to the lid. Build B fits easily.

Label: the SCAD model is geometry only (UNT). It has not been printed. Two component sizes are estimates marked MEASURE in the file: the EZCOO splitter and the MS2130 dongle. Measure yours and edit the two vectors before printing.

## 3.1 Dimensioned drawing (printed case, Build A)

Top view, lid removed. Internal 250 x 170 x 46 mm, walls 2.5 mm, outer 255 x 175 x 48.5 mm.

```
      0        50       100       150       200       250  (mm, X)
   0  ┌─────────┬─────────┬─────────┬─────────┬─────────┐
      │ Pico    │ MS2130  │         │ EZCOO EZ-SP12H2   │   FRONT  (panel face, y = 0)
      │ 51x21   │ 65x25   │         │ 100x65 (MEASURE)  │
  35  │ 74AHCT  ├─────────┘         │ scaler DIP: OUT2 ON│
      │ 30x20   │                   └───────────────────┤
  65  ├─────────┴──────────────────┐                    │
      │  Mean Well LRS-100-5       │                    │
      │  129 x 97 x 30             │   ┌────────────────┤
 100  │  V-adj -> 5.15 V           │   │ Raspberry Pi 5 │
      │  terminal cover fitted     │   │ 85 x 56        │ ports ->  right wall opening 60 x 18
      │                            │   │ Active Cooler  │
 156  │                            │   └────────────────┤
 162  └────────────────────────────┴────────────────────┘
      │◄──────── 129 ────────────►│  │◄───── 85 ─────►│                         REAR (vents)

 Front face, seen from the front (X across, Z up), all items centred at Z = 25.5 mm:

      ┌───────────────────────────────────────────────────────────────────────────┐
  48  │   AC           IN 1        IN 2        OUT         LED   ●               │
      │ ┌──────┐     ┌─────┐     ┌─────┐     ┌─────┐      ( )   o                │
      │ │ IEC  │     │HDMI │     │HDMI │     │HDMI │     GX16  5mm               │
      │ └──────┘     └─────┘     └─────┘     └─────┘                              │
   0  └───────────────────────────────────────────────────────────────────────────┘
        x=30          95          135         175         215   240
      IEC C14 fused: 47.5 x 27.5 opening, M3 x 40 mm pitch
      HDMI panel cable: 25 x 13 opening, M3 x 30 mm pitch (MEASURE your cable's flange)
      GX16-4: 16.2 mm hole.  Status LED: 5.2 mm hole.
```

Heights: LRS-100-5 30 mm on 4 mm standoffs = 34 mm; Pi 5 with Active Cooler about 22 mm on 5 mm standoffs = 27 mm; EZ-SP12H2 about 22 mm. Internal height 46 mm leaves 12 mm over the supply for its terminal cover and for airflow.

## 3.2 Internal wiring

```
 IEC inlet L/N/E ──14 AWG──► LRS-100-5  L / N / FG(earth)
 LRS +V ──18 AWG──┬─► 10 A blade fuse ──► GX16 pin 1+2 (5 V to strip)
                  ├─► 3 A polyfuse ──► Pi 5 header pin 2 (5 V)
                  ├─► 74AHCT125 pin 14 (VCC)
                  └─► EZ-SP12H2 USB power lead (cut its wall adapter, or USB-A from the Pi)
 LRS -V ──18 AWG──┬─► GX16 pin 3 (GND)
                  ├─► Pi 5 header pin 6 (GND)
                  ├─► 74AHCT125 pin 7 and pin 1 (GND, OE low)
                  └─► Pico GND (also shared through the USB lead)
 Pi 5 USB 3 (blue) ──► MS2130
 Pi 5 USB 2 ──10 cm micro-USB──► Pico
 Pico GP (HyperSerialPico default data pin, see its README) ──► 74AHCT125 pin 2 ──► pin 3 ──► 330 Ω ──► GX16 pin 4 (DATA)
 Pi 5 GPIO17 ──330 Ω──► status LED anode; cathode ──► GND
 EZ-SP12H2 OUT 1 ──panel HDMI cable──► [OUT]      EZ-SP12H2 IN ◄──panel HDMI cable── [IN 1]
 EZ-SP12H2 OUT 2 ──15 cm HDMI──► MS2130
```

Mains section: keep the IEC inlet, its wiring and the LRS terminal block in the left rear corner, at least 10 mm from any 5 V wiring, and fit the LRS's clear terminal cover. Use a fused IEC inlet (2 A slow-blow). Earth the LRS FG terminal to the inlet earth pin. If any of that sentence is unfamiliar, build B instead.

## 3.3 Drilling template for the Hammond 1591XXFBK (Build B)

Front long face (221 mm wide, 63.5 mm high), all centres at height 32 mm from the base edge:

| Item | X from left edge | Opening |
|---|---|---|
| DC jack 5.5 x 2.1 mm, 10 A rated | 20 mm | 12 mm hole (check your jack) |
| HDMI IN 1 | 65 mm | 25 x 13 mm rectangle + 2 x M3 at 30 mm pitch |
| HDMI IN 2 (optional) | 105 mm | same |
| HDMI OUT | 145 mm | same |
| LED GX16-4 | 185 mm | 16.2 mm hole |
| Status LED | 208 mm | 5.2 mm hole |

Right short face: 60 x 18 mm rectangular opening for the Pi's USB/Ethernet (bottom edge 8 mm up). Lid: two fields of 2 mm slots over the Pi and over the supply, 4 mm pitch. Print `hardware/enclosure.scad` with `part="lid"` if you want the label engraving and slot pattern to transfer to a paper template first.

## 3.4 Status LED behaviour

Driven by `syncbox-status` (docs/05): solid = syncing, slow breathing = no HDMI signal (lights in ambient/off state), fast blink = HyperHDR not running, off = box off.

## 3.5 Thermal

The Pi 5 Active Cooler exhausts sideways; the lid slots sit directly above it and the floor slots below. The LRS-100-5 is rated for convection cooling in free air at up to 70 percent load at 50 °C ambient (Mean Well derating curve); at 3.6 A typical it runs at 20 percent load. Acceptance test T8 in docs/07 measures the closed-box result; if the Pi reports throttling, the fix order is: enlarge lid slots to 2.5 x 30 mm, add a 40 mm 5 V fan on the right wall, then move the supply outside (Build B).
