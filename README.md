# Xiaomi Mijia Smart Air Purifier MAX: local control

Local control of the Xiaomi Mijia Smart Air Purifier MAX (`xiaomi.airp.mb6`) over your home network,
without Mi Home or the Xiaomi cloud.

Tested on one unit with Wi-Fi firmware 1.0.3 and MCU firmware 0019.

I couldn't find anything about this model's local protocol online, so I mapped it myself.
The repo has:

- `FIELDS.md`: every property I found, including ones that are not in the official spec
  (direct motor RPM, raw formaldehyde reading, reboot cause, a hidden self-test service) and measured RPM values.
- `miio.py`: a small miIO client. Only needs `cryptography`. Finds the device on the LAN by itself.
- `watch.py`: logs every property that changes. Handy for figuring out what a button or app setting does.
- `boost.py`: speeds the fan up based on PM2.5 (for cooking) and goes back to Auto when the air is clean.
- `spec/`: MIoT spec files for this model and related ones, from [home.miot-spec.com](https://home.miot-spec.com).

## Device

| | |
|---|---|
| Model | `xiaomi.airp.mb6`, Mijia Smart Air Purifier MAX (global version) |
| Chinese version | `xiaomi.airp.mp6`, 米家空气净化器6双芯除醛 (MHCWB5G-B) |
| Wi-Fi chip | Bouffalo BL602 |
| CADR | particles 1006.5 m³/h, formaldehyde 240.5 m³/h |

Not the same device as `xiaomi.airp.sa6` (米家空气净化器 6 Max). That one is bigger, with two motors and VOC/CO2 sensors.

## Usage

```sh
python3 -m venv venv
venv/bin/pip install -r requirements.txt

venv/bin/python miio.py --token <TOKEN> miIO.info
venv/bin/python watch.py --token <TOKEN> --seconds 600
venv/bin/python boost.py --token <TOKEN>
```

Without `--ip` the scripts look for the device with a UDP broadcast. If that doesn't work on your network,
add `--subnet 192.168.1` or give the purifier a fixed IP in your router. You can also set `MIIO_TOKEN` and `MIIO_IP`.

This is what `watch.py` printed when I switched to sleep mode and then to favorite level 10
(`2.3` is the mode, `13.3` the target RPM, `13.4` the measured RPM):

```
18:03:37 2.3: 0 -> 3
18:03:37 13.3: 611 -> 300
18:03:37 13.4: 605 -> 475
18:03:41 2.3: 3 -> 5
18:03:41 13.3: 300 -> 1620
18:03:41 13.4: 475 -> 950
18:03:45 13.4: 950 -> 1320
```

From Python:

```python
import miio
d = miio.Dev("192.168.1.50", "<TOKEN>")
print(d.get([(3, 4), (3, 6), (13, 4)]))   # PM2.5, formaldehyde, motor RPM
d.set(2, 3, 5)                             # favorite mode
d.set(9, 1, 6)                             # favorite level 6, about 1040 rpm
```

### Token

You need the device token from the Xiaomi cloud. I used
[Xiaomi-cloud-tokens-extractor](https://github.com/PiotrMachowski/Xiaomi-cloud-tokens-extractor).
Log in with the account that owns the device, a shared account won't get the token.
Its output file works directly with `--tokens tokens.json`. The token changes whenever the device is paired again.

Don't share your token. Anyone on your network who has it can control the purifier.

## Interesting findings

`13.9` sets the motor RPM directly. The motor follows it even in Auto mode, until you actually change the mode.
The app tops out at 1620 rpm (favorite level 10), but the firmware doesn't stop there.

### Self-test from the Chinese version

The Chinese version (`xiaomi.airp.mp6`) has a self-test service (service 14) in its spec. It can test the motor,
the formaldehyde, particle and temperature sensors, the lid sensor and each button. The global spec for this
model doesn't mention it at all, but the device still answers on service 14 and the properties match the
Chinese spec exactly. So the feature seems to be in the firmware, just hidden. I haven't started a test yet
because I don't know what the device does during it.

### Filter counter and filter tag

Service 11 is meant for a filter tag (serial, factory, type, date, batch). On my unit every field is zero,
and it stayed zero after I took the filter out and put it back. So at least here the purifier doesn't seem
to read anything from the filter, and filter life looks like a plain hour counter.

There are also two write-only properties, `10.1` (filter hours used) and `10.2` (filter percent used).
In theory they would let you set the counter yourself. I haven't tried writing them.

Details, measurements and open questions are in `FIELDS.md`.

## Home Assistant

This repo is not a Home Assistant integration. If you use
[hass-xiaomi-miot](https://github.com/al-one/hass-xiaomi-miot), the standard properties come from the official
spec and should work. The hidden ones like `13.9` are not in the spec, so they won't show up on their own.
You can use the addresses in `FIELDS.md` to call them yourself.

## Be careful

This is not an official Xiaomi project. Use it at your own risk.

- Above 1620 rpm you're outside what Xiaomi allows. I ran 1700 for 11 seconds and it reached at least 1660 rpm
  with no error, but I don't know what long runs do to the motor. The extra airflow is only about 5%. I don't recommend it.
- Don't write to `13.11`, it is the region code.
- Read and note the old value before writing to any undocumented property.

## Contributing

If you have this purifier, measurements from your unit are welcome, especially about the open questions in
`FIELDS.md`. Please leave your token, device id, MAC and account id out of issues.

## License

MIT. See [LICENSE](LICENSE). The files in `spec/` are Xiaomi's public MIoT specs.
