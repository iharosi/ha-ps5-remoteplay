# PS5 Remote Play for Home Assistant

Turn a PlayStation 5 on and off from Home Assistant, and use its power state in automations.

Adds one **power switch** per console:

| Console | Switch |
|---|---|
| Awake | `on` |
| Rest mode (standby) | `off` |
| Unplugged or off the network | `unavailable` |

Turning the switch on wakes the PS5; turning it off puts it into rest mode. Everything runs on
your local network through the console's Remote Play interface, using the
[ps5-remoteplay](https://github.com/iharosi/ps5-remoteplay) library.

## Requirements

- Home Assistant 2026.7 or newer, on the same network (subnet) as the PS5
- On the PS5: **Settings > System > Remote Play > Enable Remote Play** turned on
- For waking from rest mode: **Settings > System > Power Saving > Features Available in Rest Mode >
  Stay Connected to the Internet** and **Enable Turning On PS5 from Network** turned on
- A fixed IP address for the PS5 (set a DHCP reservation in your router)
- If you run Home Assistant in Docker, the container needs `network_mode: host`

## Installation (HACS)

1. In HACS, open the **⋮** menu > **Custom repositories**
2. Add `https://github.com/iharosi/ha-ps5-remoteplay` with type **Integration**
3. Find **PS5 Remote Play** in HACS, download it, and restart Home Assistant

## Setup

Turn the PS5 on fully (not rest mode), then in Home Assistant go to
**Settings > Devices & services > Add integration > PS5 Remote Play**:

1. Enter the PS5's IP address
2. Sign in to PlayStation Network through the link shown, and paste the "redirect" address back
3. On the PS5, open **Settings > System > Remote Play > Link Device** and enter the PIN it shows

If your PS5 user has a passcode, set it under the integration's **Configure** button; it is needed
to put the console into standby.

## License

AGPL-3.0-only. Protocol implementation based on [playactor](https://github.com/dhleong/playactor)
and [chiaki](https://git.sr.ht/~thestr4ng3r/chiaki).
