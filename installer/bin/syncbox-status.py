#!/usr/bin/env python3
"""Front-panel status LED on GPIO17 (through 330 ohm).
solid = syncing (video source active) | slow breathe = no HDMI signal | fast blink = engine offline."""
import os
import sys
import time

sys.path.insert(0, "/opt/syncbox/ui")
import hyperhdr as H  # noqa: E402

try:
    from gpiozero import PWMLED
    led = PWMLED(int(os.environ.get("SYNCBOX_LED_GPIO", "17")))
except Exception as exc:  # no GPIO (dev box) -> log only
    print("no GPIO available:", exc, flush=True)
    led = None

state = None
while True:
    try:
        s = H.signal_state()
        new = "sync" if s.get("video_active") else "nosignal"
        if s.get("leds_enabled") is False:
            new = "off"
    except H.HyperHDRError:
        new = "offline"
    if new != state:
        state = new
        print("status:", state, flush=True)
        if led:
            if state == "sync":
                led.value = 1.0
            elif state == "nosignal":
                led.pulse(fade_in_time=1.5, fade_out_time=1.5)
            elif state == "off":
                led.value = 0.05
            else:
                led.blink(on_time=0.15, off_time=0.15)
    time.sleep(2)
