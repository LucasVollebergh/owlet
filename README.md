# Owlet Smart Sock for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![hacs][hacsbadge]][hacs]
[![License][license-shield]][license]

A Home Assistant custom integration for the Owlet Smart Sock 2, Smart Sock 3 and Dream Sock, using the Owlet cloud.

This is the maintained continuation of [ryanbdclark/owlet](https://github.com/ryanbdclark/owlet), which was archived in July 2026. Many thanks to Ryan Clark for the original work.

> [!WARNING]
> **This is not a medical device.** Data reaches Home Assistant by polling the Owlet cloud, which can be delayed, stop without warning or break when Owlet changes its private API. Never rely on this integration for alarms. Keep the Owlet base station and the official Owlet app as your primary alert.

## Requirements

- Home Assistant 2025.12 or newer, any installation type (OS, Supervised, Container, Core)
- [HACS](https://hacs.xyz/)
- An Owlet account with at least one Smart Sock 2, Smart Sock 3 or Dream Sock

## Installation

1. In HACS, open the menu (three dots) and choose **Custom repositories**.
2. Add `https://github.com/lucasvollebergh/owlet` with type **Integration**.
3. Search for **Owlet Smart Sock** in HACS and download it.
4. Restart Home Assistant.
5. [![Add Integration][add-integration-badge]][add-integration] or go to **Settings > Devices & services > Add integration** and search for **Owlet Smart Sock**.
6. Pick your region (Europe for accounts created in the EU or UK, World otherwise) and log in with your Owlet app credentials.

## Migrating from ryanbdclark/owlet

The domain (`owlet`) and all unique ids are unchanged, so existing entities, dashboards and automations keep working.

1. In HACS, open the old Owlet repository and choose **Remove** (this does not delete your config entry).
2. Add this repository as a custom repository and download it, see above.
3. Restart Home Assistant.

If the options dialog failed to open before (a known issue on Home Assistant 2025.12 and later), it works again after migrating.

## Entities

Per sock:

| Type | Entities |
| --- | --- |
| Sensor | Heart rate, O2 saturation, O2 saturation 10 minute average, skin temperature, sleep state, battery percentage, battery remaining, signal strength, last reading, movement and movement bucket (disabled by default) |
| Binary sensor | Charging, awake, sock off, high/low heart rate alert, high/low/critical oxygen alert, low/critical battery alert, lost power alert, sock disconnected alert, data stale |
| Switch | Base station on |

Which entities appear depends on what your sock reports. Vitals are unavailable while the sock is charging.

### Stale data detection

Users have reported values that stop changing while the Owlet app still shows live data. When the Owlet cloud keeps returning an old reading, a heart rate looks "frozen". The integration compares the timestamp of the latest reading with the current time:

- **Data stale** (binary sensor) turns on when no new reading arrived within the threshold while the sock is not charging and the base station is on.
- Vitals become unavailable at the same moment, so a frozen value is never shown as a live one.
- **Last reading** (sensor) shows when the cloud last received data.

## Options

**Settings > Devices & services > Owlet Smart Sock > Configure**

| Option | Default | Description |
| --- | --- | --- |
| Polling interval | 10 s | Seconds between requests to the Owlet cloud, minimum 5. Every poll costs several API calls per sock, a lower value raises the risk of rate limiting. |
| Stale data threshold | 5 min | Minutes without a new reading before the data is treated as stale. Set to 0 to disable. |

The integration also supports **Reconfigure** (change region or log in again) and asks you to log in again automatically when the Owlet session expires.

## Troubleshooting

- **"Invalid handler specified"** when adding the integration: an incompatible `pyowletapi` version was installed by an older release. Install the latest release of this repository and restart.
- **Values stop changing**: check the Data stale and Last reading entities. If the Owlet app shows fresh data but Home Assistant does not, download diagnostics (device page > three dots > Download diagnostics) and open an issue. Diagnostics redact tokens, email, serial numbers, MAC addresses and baby details.
- Enable debug logging:

  ```yaml
  logger:
    logs:
      custom_components.owlet: debug
      pyowletapi: debug
  ```

## Known limitations

- Owlet has no public API. This integration uses the same private endpoints as the Owlet app, which Owlet can change or block at any time.
- The Owlet Cam is not supported.
- Only one Owlet account per Home Assistant config entry, add another entry for a second account.

## Contributing

Issues and pull requests are welcome. Run the checks locally with:

```bash
pip install -r requirements_test.txt
ruff check . && ruff format --check .
pytest
```

---

[hacs]: https://github.com/hacs/integration
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
[license]: LICENSE
[license-shield]: https://img.shields.io/github/license/lucasvollebergh/owlet.svg?style=for-the-badge
[releases-shield]: https://img.shields.io/github/release/lucasvollebergh/owlet.svg?style=for-the-badge
[releases]: https://github.com/lucasvollebergh/owlet/releases
[add-integration]: https://my.home-assistant.io/redirect/config_flow_start?domain=owlet
[add-integration-badge]: https://my.home-assistant.io/badges/config_flow_start.svg
