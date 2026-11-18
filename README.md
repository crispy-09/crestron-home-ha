# Crestron Home for Home Assistant

Local control of a **Crestron Home** processor (e.g. MC4-R, CP4-R) through its built-in REST API (`https://<processor>/cws/api`). No bridge, no SIMPL program, no cloud.

## What you get

| Crestron | Home Assistant | Notes |
|---|---|---|
| Lights (dimmers, switches) | `light` | Brightness and transition for dimmers. Unavailable when Crestron reports the device offline. |
| Door locks | `lock` | Lock/unlock. A blank Crestron status (e.g. a jammed bolt) shows as **unknown**, never as locked. |
| Media rooms | `media_player` | Power, source selection (e.g. Apple TV / Xbox / Blu-ray), and volume/mute where Crestron controls them. |
| Scenes | `scene` | One HA device per Crestron room. The `active` attribute mirrors Crestron's scene status. |
| Scene activations | `crestron_home_scene_activated` event | Fired when a scene goes inactive → active, whether from a keypad, the Crestron app, or a schedule. |

Rooms become HA areas automatically (suggested area on each device).

Not included yet: shades, thermostats, and security. Shades and thermostats are easy to add if you have them.

## Setup

1. In the Crestron Home setup app: **Installer Settings → System Control Options → Web API Settings**. Enable it and copy the **REST API token**.
2. Install with HACS: **HACS → ⋮ → Custom repositories**, add this repo's URL as an *Integration*, install **Crestron Home**, and restart Home Assistant.
   (Or copy `custom_components/crestron_home` into `/config/custom_components/` by hand.)
3. **Settings → Devices & services → Add integration → Crestron Home**, then enter the processor IP and token.

**Configure** on the integration lets you change:

- **Polling interval** (default 5 s).
- **Media room volume scale**: how your processor expects volume to be *set*. Crestron's API docs say 0–100 percent, but processors like the MC4-R take 0–65535 (the scale they report). The default is 0–65535. If volume up jumps to silent, switch it.

**Firmware updates can reset the token.** If that happens, HA will prompt you to re-authenticate with the new token.

## Use keypad presses as triggers

Crestron Home doesn't expose raw keypad button presses, but a button that runs a scene does show up as that scene becoming active:

```yaml
automation:
  - alias: "Kitchen Evening button → also dim Hue strip"
    triggers:
      - trigger: event
        event_type: crestron_home_scene_activated
        event_data:
          name: Kitchen Evening
    actions:
      - action: light.turn_on
        target: { entity_id: light.kitchen_strip }
        data: { brightness_pct: 30 }
```

Event data: `scene_id`, `name`, `room`, `type`.
