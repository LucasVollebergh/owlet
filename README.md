# Owlet Smart Sock for Home Assistant

[![GitHub Release][releases-shield]][releases]
[![hacs][hacsbadge]][hacs]
[![License][license-shield]][license]

A Home Assistant custom integration for the Owlet Smart Sock 2, Smart Sock 3 and Dream Sock, using the Owlet cloud.

> [!NOTE]
> This is the maintained continuation of [ryanbdclark/owlet](https://github.com/ryanbdclark/owlet) by [Ryan Clark (@ryanbdclark)](https://github.com/ryanbdclark), which was archived in July 2026. A big thank you to Ryan for building this integration and the [pyowletapi](https://github.com/ryanbdclark/pyowletapi) library it relies on, and for keeping it running for years. We are happy to take it over and keep maintaining it from here, see [Credits](#credits).

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

### Repairs

When the data stays stale for more than an hour while the sock should be sending readings, a warning appears under **Settings > System > Repairs** with the time of the last reading. It disappears by itself once fresh readings arrive, and never appears when the stale data threshold is set to 0.

## Blueprints

Ready-made automations, import them with one click (requires the Home Assistant Companion app for notifications):

| Blueprint | What it does | Import |
| --- | --- | --- |
| Owlet alert notification | Notification when one of the selected Owlet alerts turns on, optionally as a critical notification that sounds on silent/do not disturb. | [![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Flucasvollebergh%2Fowlet%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fowlet%2Fowlet_alert_notification.yaml) |
| Owlet stale data notification | Notification when the Data stale sensor turns on (after an optional extra delay), and optionally when readings are back. | [![Import blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2Flucasvollebergh%2Fowlet%2Fblob%2Fmain%2Fblueprints%2Fautomation%2Fowlet%2Fowlet_stale_data_notification.yaml) |

These notifications depend on Home Assistant polling the Owlet cloud and can be delayed. They do not replace the Owlet base station and app.

## Dashboard

[`dashboards/owlet.yaml`](dashboards/owlet.yaml) is a ready-made dashboard that only uses built-in cards, so no custom cards need to be installed. It shows:

- **Now:** heart rate and O2 gauges, O2 10 minute average, skin temperature, sleep state, sock off, charging and the base station switch, plus a warning when the data is stale.
- **Owlet alerts:** only the alerts Owlet currently reports as active.
- **Last 12 hours:** heart rate, O2 saturation and a sleep timeline (awake, light sleep, deep sleep, sock off, data stale).
- **Trends:** daily minimum, mean and maximum of heart rate, O2 saturation and skin temperature over 30 days, from the long-term statistics Home Assistant keeps.
- **Device:** battery, battery remaining, signal strength and last reading.

To add it:

1. Go to **Settings > Dashboards > Add dashboard > New dashboard from scratch** and open it.
2. Choose the pencil (Edit dashboard), then the three dots > **Raw configuration editor**.
3. Paste the contents of `dashboards/owlet.yaml`.
4. Replace every `owlet_sock_serial_number` with the entity id prefix of your sock. You find it on the device page of your sock, for example `sensor.owlet_sock_ab12cd34_heart_rate` has the prefix `owlet_sock_ab12cd34`.

With more than one sock, duplicate the view and use the prefix of the other sock. Trends fill up over time: the daily statistics start from the moment the integration is installed.

The gauge ranges are for display only and have no medical meaning. Alerts come from Owlet itself.

## Options

**Settings > Devices & services > Owlet Smart Sock > Configure**

| Option | Default | Description |
| --- | --- | --- |
| Polling interval | 10 s | Seconds between requests to the Owlet cloud, minimum 5. Every poll costs several API calls per sock, a lower value raises the risk of rate limiting. |
| Stale data threshold | 5 min | Minutes without a new reading before the data is treated as stale. Set to 0 to disable. |

The integration also supports **Reconfigure** (change region or log in again) and asks you to log in again automatically when the Owlet session expires.

## Troubleshooting

- **"Invalid handler specified"** when adding the integration: this came from an incompatible external `pyowletapi` version in older releases. The Owlet API client now ships inside the integration, install the latest release of this repository and restart.
- **Values stop changing**: check the Data stale and Last reading entities. If the Owlet app shows fresh data but Home Assistant does not, download diagnostics (device page > three dots > Download diagnostics) and open an issue. Diagnostics redact tokens, email, serial numbers, MAC addresses and baby details.
- Enable debug logging:

  ```yaml
  logger:
    logs:
      custom_components.owlet: debug
      custom_components.owlet.owletapi: debug
  ```

## Known limitations

- Owlet has no public API. This integration uses the same private endpoints as the Owlet app, which Owlet can change or block at any time.
- The Owlet Cam is not supported.
- Only one Owlet account per Home Assistant config entry, add another entry for a second account.

## Credits

- **Original author:** [Ryan Clark (@ryanbdclark)](https://github.com/ryanbdclark) created this integration in [ryanbdclark/owlet](https://github.com/ryanbdclark/owlet) and the [pyowletapi](https://github.com/ryanbdclark/pyowletapi) library that talks to the Owlet cloud. Everything here builds on that work. Thank you, Ryan.
- **Contributors to the original repository:** everyone who sent fixes and translations upstream, including [@MarjovanLier](https://github.com/MarjovanLier) (multiple devices), [@Julien80](https://github.com/Julien80) (French translation) and [@coreywillwhat](https://github.com/coreywillwhat) (10 minute oxygen average filtering).
- **Owlet API client:** the integration ships its own copy of [lucasvollebergh/pyowletapi](https://github.com/lucasvollebergh/pyowletapi) (pyowletapi-ng), the maintained continuation of Ryan's library, in `custom_components/owlet/owletapi`, so Home Assistant does not need to install anything from PyPI.
- **Maintainer of this fork:** [@lucasvollebergh](https://github.com/lucasvollebergh). Issues and pull requests go to [this repository](https://github.com/lucasvollebergh/owlet/issues).

The original license (Apache 2.0) still applies, see [LICENSE](LICENSE) and [NOTICE](NOTICE).

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
