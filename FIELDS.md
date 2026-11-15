# Property map: xiaomi.airp.mb6

Addresses are `siid.piid`. Sources: `spec/spec.json` (official spec of this model), `spec/ml.json`
(multi-language names; the Chinese descriptions reveal internal names), the Chinese twin `xiaomi.airp.mp6`
(`spec/mp6-2.json`), and a scan of the device itself (siid 1-25 × piid 1-30). Measurements are from one unit,
Wi-Fi firmware 1.0.3, MCU 0019.

## Standard properties

| Address | Meaning |
|---|---|
| `2.1` | Power (bool) |
| `2.2` | Fault: 0 none, 1 PM sensor, 2 temp/humidity sensor, 3 HCHO sensor, 5 motor stuck |
| `2.3` | Mode: 0 auto, 3 sleep, 5 favorite, 6 manual level |
| `2.4` | Manual level: 0 → 640 rpm, 1 → 940 rpm, 2 → not measured |
| `2.6` | UV lamp (turns on/off together with power) |
| `3.1` `3.2` | Humidity %, temperature °C |
| `3.3` | Air quality 0 excellent to 5 hazardous |
| `3.4` `3.5` `3.9` | PM2.5, PM10, PM1 (µg/m³) |
| `3.6` | Formaldehyde (mg/m³). Reads 0.0 for ~100 s after power-on (warm-up) |
| `4.1` `4.2` `4.3` | Filter life %, hours left, hours used |
| `6.1` `6.2` | Display on, brightness (0/1/2) |
| `7.1` | Button beep on/off (no tone or volume setting exists) |
| `8.1` | Child lock |
| `9.1` | Favorite level 0-10 |

Actions: `2.1` toggle, `4.1` reset filter, `13.1` cycle mode, `13.2` cycle manual level.
Events (cloud only): `13.3` lid opened, `13.4` filter exhausted, `8.1` child lock triggered.

### Measured RPM

| Setting | RPM |
|---|---|
| Sleep | 300 |
| Favorite 0 / 3 / 6 / 10 | 300 / 740 / 1040 / 1620 |
| Manual 0 / 1 | 640 / 940 |
| Auto, clean air | 300 |
| Auto, PM2.5 ≈ 18 | 840 |

## Undocumented / hidden properties

| Address | Internal name | Notes |
|---|---|---|
| `10.1` (write) | filter-used-time | Filter hours used. Not tested |
| `10.2` (write) | filter-used-life | Filter % used. Not tested |
| `11.1`-`11.5` | filter-tag | Tag serial, factory, type, date, batch. All zeros on my unit, unchanged after removing and reinserting the filter |
| `12.1` (read/write) | update-heartbeat | Environment data sync interval, 300. Write not tested |
| `13.1` | favorite-square | Recommended room area (m²) per favorite level: `6~10,16~28,19~33,23~41,28~49,32~55,38~66,42~73,51~87,55~95,63~108` |
| `13.2` | reboot-cause | 1 power, 2 external pin, 3 software, 4 IWDG, 5 unknown |
| `13.3` | motor-rpm-set | Target RPM |
| `13.4` | motor-rpm-feedback | Measured RPM (steps of 5) |
| `13.5` | hcho-tag | HCHO sensor serial, e.g. `1-2535` |
| `13.6` | iic-error-cnt | Sensor bus error counter |
| `13.7` | hcho-original | Raw HCHO reading |
| `13.8` | common-property | Free-form status text: `run 840`, `hcho 1-0`, `hcho 0-0`, once `run 16` (meaning unknown) |
| `13.9` (write) | motor-rpm-debug | Direct RPM control, works. See below. Always reads 0 |
| `13.10` (read/write) | particle-abnormal-on | "Smoke anomaly alarm" switch (name from the `mp6` spec). False on my unit. Write not tested |
| `13.11` (read/write) | country-code | 2 = EU on my unit. Do not write. (On `mp6` the same address is a key-press report) |
| `14.x` | self-check | Hidden self-test service, see below |

Scan notes: `-4001` = service exists but property doesn't; `-4003` = service not readable (siid 5, 10, 15-25).
Write-only undocumented properties cannot be found this way.

### `13.9` motor-rpm-debug

- Writing an RPM sets `13.3` and the motor follows (611 held stable for 3 min). It also overrides Auto mode.
- It is sticky: rewriting the same mode (`2.3`) or the same favorite level (`9.1`) does not clear it.
  Only a real mode change clears it. To undo, write the RPM you want, or change mode.
- No firmware cap at 1620 rpm:

  | Test | Target `13.3` | Measured `13.4` | Result |
  |---|---|---|---|
  | `13.9` = 1621 for 42 s | 1621 | 1615-1620 | Accepted, not clipped |
  | `13.9` = 1700 for 11.3 s (from 1620) | 1700 | 1610 → 1625 → 1655 → 1660 | Still rising when stopped, fault 0 |

  The real ceiling is unknown. Long runs above 1620 were not tested and are not recommended.

For comparison (other models, not this one): Air Purifier 3/3H motor range 200-2000; 3C clips favorite RPM at 2200
(Home Assistant issue #59580); 4 Lite reports 0-2500 read-only.

### Self-test service (siid 14)

Not in this model's spec, but the device answers `14.2` and `14.3`, matching the `mp6` spec exactly.

| Address | Name | Notes |
|---|---|---|
| `14.1` (parameter only) | self-check-items | 0 all, 1 motor, 2 HCHO sensor, 3 particle sensor, 4 temperature sensor, 5 lid sensor, 6 power key, 7 mode key, 8 display key, 9 LED key |
| `14.2` (read) | self-check-results | Empty string (never run) |
| `14.3` (read/write) | manual-check-results | 0 normal, 1 abnormal, 2 ignore |
| action `14.1` | start-check | Start self-test |
| action `14.2` | stop-check | Stop |
| action `14.3` | sync-manual-check | Sync manual check results |
| event `14.1` | self-check-complete | Done (to cloud) |

The action's parameter format and what the device does during the test are unknown. Not run yet.

## Differences from related models

- `xiaomi.airp.mp6` (Chinese twin): nearly identical spec. Documents the self-test service and smoke alarm;
  `13.11` is a key-press report there; v2 adds `15.1` button-track (siid 15 returns `-4003` on mb6); PM1 range 0-600.
- `xiaomi.airp.sa6` (米家空气净化器 6 Max): a different, larger device (two motors 0-2500 rpm each, three filters,
  VOC and CO2, 12 favorite levels).
- `ma6`, `mc6`: smaller models of the series; `mc6` has no HCHO sensor and no `13.9`.

## Other observations

- No open TCP ports. `miIO.get_ota_state` → `idle`.
- Lid safety switch works: opening the lid powers the device off.
- Match test: PM2.5 went from 3 to ~500 and back to 12 within a few minutes; Auto mode ramped to 840 rpm.
- Display content cannot be changed; only `6.1` on/off and `6.2` brightness.
- Persistent automations cannot be stored on the device; use Mi Home automations or an always-on host.

## Open questions

1. Meaning of `13.8` values like `run 16`.
2. Parameter format and behaviour of the siid 14 self-test.
3. Why the filter tag (siid 11) is all zeros; whether the counter resets on its own with a new filter.
4. Real RPM ceiling of `13.9`.
5. Effect of writing `10.1`, `10.2`, `12.1`, `13.10`.
