/*
 * DIY Hue Sync Box - ESP32 LED receiver
 *
 * Receives per-LED colours from the Raspberry Pi over either
 *   - Wi-Fi: DDP packets on UDP port 4048 (same protocol WLED uses), or
 *   - USB serial: Adalight frames ("Ada" + hi + lo + chk + RGB...),
 * and pushes them to a WS2812B strip with FastLED.
 *
 * When no frame has arrived for REALTIME_TIMEOUT_MS the strip shows a
 * fallback colour, so the room does not go dark when the Pi stops.
 */
#include <Arduino.h>
#include <FastLED.h>

#if __has_include("secrets.h")
#include "secrets.h"
#else
#define USE_WIFI 0
#endif

#if USE_WIFI
#if defined(ESP8266)
#include <ESP8266WiFi.h>
#else
#include <WiFi.h>
#endif
#include <WiFiUdp.h>
#endif

#ifndef NUM_LEDS
#define NUM_LEDS 224
#endif
#ifndef DATA_PIN
#define DATA_PIN 16
#endif
#ifndef MAX_MILLIAMPS
#define MAX_MILLIAMPS 8000
#endif
#ifndef SERIAL_BAUD
#define SERIAL_BAUD 500000
#endif

static const uint16_t DDP_PORT = 4048;
static const uint32_t REALTIME_TIMEOUT_MS = 2500;
static const CRGB FALLBACK_COLOR(40, 20, 80);

CRGB leds[NUM_LEDS];
uint32_t lastFrameMs = 0;
bool showingFallback = false;

#if USE_WIFI
WiFiUDP udp;
uint8_t packet[1500];

void connectWifi() {
  WiFi.mode(WIFI_STA);
#if !defined(ESP8266)
  WiFi.setSleep(false);            // lower latency, avoids dropped UDP bursts
#endif
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.print("wifi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(250);
    Serial.print('.');
  }
  Serial.print(" connected, ip=");
  Serial.println(WiFi.localIP());
  udp.begin(DDP_PORT);
}

// DDP header: flags | seq | type | dest | offset(4, BE) | length(2, BE) | data
void handleDDP() {
  int len = udp.parsePacket();
  if (len < 10) return;
  int n = udp.read(packet, sizeof(packet));
  if (n < 10) return;
  const uint8_t flags = packet[0];
  const uint32_t offset = ((uint32_t)packet[4] << 24) | ((uint32_t)packet[5] << 16) | ((uint32_t)packet[6] << 8) | packet[7];
  uint32_t dlen = ((uint32_t)packet[8] << 8) | packet[9];
  if (dlen > (uint32_t)(n - 10)) dlen = n - 10;
  const uint32_t maxBytes = (uint32_t)NUM_LEDS * 3;
  if (offset < maxBytes) {
    const uint32_t count = min(dlen, maxBytes - offset);
    memcpy(((uint8_t*)leds) + offset, packet + 10, count);   // CRGB is r,g,b in memory
  }
  if (flags & 0x01) {                // PUSH: frame complete
    FastLED.show();
    lastFrameMs = millis();
    showingFallback = false;
  }
}
#endif

// Adalight state machine (works with the Pi's adalight output and with
// Hyperion/HyperHDR/Prismatik).
enum AdaState { A_WAIT_A, A_WAIT_D, A_WAIT_A2, A_HI, A_LO, A_CHK, A_DATA };
AdaState adaState = A_WAIT_A;
uint8_t adaHi = 0, adaLo = 0;
uint32_t adaBytes = 0, adaIndex = 0;

void handleSerial() {
  while (Serial.available()) {
    const uint8_t c = Serial.read();
    switch (adaState) {
      case A_WAIT_A:  adaState = (c == 'A') ? A_WAIT_D : A_WAIT_A; break;
      case A_WAIT_D:  adaState = (c == 'd') ? A_WAIT_A2 : A_WAIT_A; break;
      case A_WAIT_A2: adaState = (c == 'a') ? A_HI : A_WAIT_A; break;
      case A_HI:      adaHi = c; adaState = A_LO; break;
      case A_LO:      adaLo = c; adaState = A_CHK; break;
      case A_CHK:
        if (c == (adaHi ^ adaLo ^ 0x55)) {
          adaBytes = (((uint32_t)adaHi << 8) | adaLo) + 1;
          adaBytes *= 3;
          adaIndex = 0;
          adaState = A_DATA;
        } else {
          adaState = A_WAIT_A;
        }
        break;
      case A_DATA:
        if (adaIndex < (uint32_t)NUM_LEDS * 3) ((uint8_t*)leds)[adaIndex] = c;
        adaIndex++;
        if (adaIndex >= adaBytes) {
          FastLED.show();
          lastFrameMs = millis();
          showingFallback = false;
          adaState = A_WAIT_A;
        }
        break;
    }
  }
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  FastLED.addLeds<WS2812B, DATA_PIN, GRB>(leds, NUM_LEDS);
  FastLED.setCorrection(TypicalLEDStrip);
  FastLED.setMaxPowerInVoltsAndMilliamps(5, MAX_MILLIAMPS);
  fill_solid(leds, NUM_LEDS, FALLBACK_COLOR);
  FastLED.show();
  showingFallback = true;
#if USE_WIFI
  connectWifi();
#endif
  Serial.print("Ada\n");   // Adalight "ready" banner
}

void loop() {
#if USE_WIFI
  if (WiFi.status() != WL_CONNECTED) connectWifi();
  handleDDP();
#endif
  handleSerial();
  if (!showingFallback && millis() - lastFrameMs > REALTIME_TIMEOUT_MS) {
    fill_solid(leds, NUM_LEDS, FALLBACK_COLOR);
    FastLED.show();
    showingFallback = true;
  }
}
