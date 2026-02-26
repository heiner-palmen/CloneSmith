# How it works — CloneSmith sync overview

This document explains how the two applications in this project work together to let a drum player (Clone Hero) and a guitar player (Rocksmith) play the same song in sync.

## Components
- Drum Server: runs on the drum player's machine. Hosts a socket server that receives a start trigger and starts the song for the drum player.
- Guitar Client: runs on the guitar player's machine. Sends the trigger to start the song on both machines and provides the UI to add songs and timing measurements.
- Time Measure: standalone helper app used by each player to measure the time from the local start action to the agreed "first note".

## High-level flow
1. Both players ensure the same song files (or equivalents) are available on both platforms.
2. Each player runs `time measure` and performs a measurement for that song:
   - Player presses the measurement key (`a`) to start the song and the timer.
   - When the agreed first note occurs, the player presses `q` to stop and record the elapsed time.
3. The players share their two measured times (drum time and guitar time).
4. The guitar player opens the `guitar client` UI and adds the song, entering both measured times.
5. When both want to play, the guitar player selects the song and presses the configured hotkey; the guitar client sends the start trigger so each machine begins playback (using the stored offsets) such that the first notes align.

## What the measurements represent
- Drum measurement (D): the time in milliseconds from the local song-start action to the first note on the drum player's machine.
- Guitar measurement (G): the time in milliseconds from the local song-start action to the first note on the guitar player's machine.
- Static communication offset (C): a roughly constant delay introduced by the communication / streaming setup between machines (for example the drum player's screen streaming to the guitar player). This is independent of the per-machine internal timings — it describes how much later the guitar player will see the drum player's visual feed (or how the network path shifts perceived timing).

These three numbers are used together to compute how to align the songs so first notes happen simultaneously in real time.

## Interpreting values — what does a "high" number mean?
- If the drum measurement `D` is large: the drum machine (or the drum player's configuration) produces the first note later after the local start. Causes could include song file lead-in length, Clone Hero timing/latency settings, or the drum player's local audio/video pipeline.
- If the guitar measurement `G` is large: the guitar machine produces the first note later after its local start. Causes could include Rocksmith lead-in, audio buffering, or input/audio device latency on the guitar machine.
- If the static communication offset `C` is non-zero: it means that one player sees the other player's screen/audio with a consistent delay. In the current setup (drum player's screen shown in the guitar player's stream and sound coming only from the guitar player), this typically manifests as the guitar player receiving the drum player's visuals with some delay; that delay must be considered when aligning perceived first notes.

Practical meaning:
- Large `D` relative to `G`: the drum side's first note happens later; to align, the guitar start should be moved later (or drum earlier) by approximately (D - G) plus any network offset.
- Large `G` relative to `D`: the guitar's first note happens later; to align, delay the drum start (or start guitar earlier) by approximately (G - D) plus network offset.

## Simple sync formula (conceptual)
Let `D` be drum measured time, `G` be guitar measured time, and `C` be the static comm offset from drum→guitar (positive when the guitar sees the drum visuals later). A single simple adjustment to make first notes align when both machines start the song at the same trigger time is:

delta = D - G + C

- If `delta > 0`: the drum first note will occur `delta` ms later than the guitar first note when both start simultaneously — so delay the guitar start by `delta` ms (or start the drum `delta` ms earlier) to compensate.
- If `delta < 0`: the guitar first note will occur `|delta|` ms later — adjust symmetrically.

Example: `D = 1200 ms`, `G = 800 ms`, `C = 0 ms` → `delta = 400 ms`. The drum is 400 ms slower; start the guitar 400 ms later (or the drum 400 ms earlier) so first notes align.

Notes about the formula:
- The formula above is intentionally simple and practical; your implementation in `guitar client` may apply the offset by delaying the local playback start for one machine or by storing the computed per-song offset and applying it when sending the trigger.
- Exactly how the offset is applied depends on where the adjustment is easier to implement: either the guitar client instructs one machine to delay its local start, or the guitar client schedules the simultaneous trigger and pre-applies a per-machine lead/lag.

## How to add a new song (recommended workflow)
1. Both players load the same song and prepare to measure.
2. Each runs `time measure`, performs the measurement, and records their value.
3. The guitar player opens the `guitar client` → Add Song UI and enters both numeric times (drum and guitar) and the song metadata.
4. Press `Add`. The client stores the per-song timing data and computes the sync offset used later when sending the start trigger.

## Playing together
- The guitar player selects the song and presses the configured hotkey to trigger start.
- The guitar client sends the trigger to both machines and applies the stored offsets so the players' first notes are aligned in real time.

## Troubleshooting and tips
- Always re-run `time measure` when either player changes audio or streaming settings, or when network conditions change significantly.
- Keep the static communication offset `C` measured and stable; if streaming software or encoder settings change, re-measure.
- If synchronization drifts over time, verify both machines' framerate/audio buffer settings and ensure no dynamic framerate/frame-dropping is occurring.
- For easiest results, try adjusting the side with the larger jitter or variable latency (often the streaming/visual path) rather than changing the game logic.

## Remote access (port forwarding & dynamic DNS)
- Exposing the drum server so it can be reached from outside your local network requires two router-level steps:
   - Port forwarding: forward incoming TCP port `12345` on your router/public IP to the LAN IP of the drum machine (the host running `drums_server.py`).
   - Stable host name: if your ISP assigns a dynamic public IP, configure Dynamic DNS (DDNS) on the router (or use a service like DuckDNS/No-IP) so you have a stable hostname (e.g. `mydrums.ddns.example`) that resolves to your public IP.

- Host/OS firewall: allow inbound TCP connections on port `12345` on the drum machine (or restrict to specific source IP ranges if your router supports this).

- Local IP reservation: assign a static LAN IP for the drum machine or use a DHCP reservation in the router so the forwarded address doesn't change.

- Security considerations:
   - Directly exposing `drums_server.py` to the Internet carries risk because the protocol is unauthenticated by default. Prefer using a VPN (WireGuard, OpenVPN) or SSH tunnel to avoid opening ports publicly.
   - If you must open the port, restrict access with router firewall rules, use strong router admin credentials, and monitor logs for unexpected connections.

- Testing: after forwarding the port and setting up DDNS, test from a machine outside your LAN (mobile data or a remote site) by connecting to `your-ddns-hostname:12345` and confirm the drum server receives and handles actions.

Notes:
- The forwarded port must match the port used by the client (`12345`). The guitar client uses the `server` value from `guitar_client_config.json` to reach the drum server (you can set this to the DDNS hostname).
- For maximum safety and reliability use a VPN or SSH port forwarding instead of exposing `12345` to the public internet.

## Example config (copy example to enable guitar client)

- There is an example configuration file at `windows/example_guitar_client_config.json` intended as a template for local setups.
- To enable the guitar client with your local settings, copy or rename the example file to the actual config filename the client looks for: `windows/guitar_client_config.json` (the client checks the script directory first, then the parent directory). Example command on Windows PowerShell:

```powershell
cd D:\projects\outofthebox\CloneSmith\windows
Copy-Item example_guitar_client_config.json guitar_client_config.json
```

- Required keys in `guitar_client_config.json`:
   - `server`: hostname or IP address of the drum server (used to connect on port `12345`).
   - `static_offset`: integer milliseconds to add at trigger time to account for the static communication delay.

- Example content:

```json
{
   "server": "192.168.1.42",
   "static_offset": 250
}
```

- Note: `windows/guitar_client_config.json` is listed in `.gitignore` so machine-specific config remains local and is not committed to the repository.

## Summary
Synchronization requires three pieces of information: the drum measurement, the guitar measurement, and the static communication offset. Entering both measured times into the `guitar client` enables computation of a per-song adjustment so both players hear/see their first note at the same real time and enjoy playing together.

If you want, I can also: (1) add a small inline calculator script into `guitar client` to compute `delta` automatically, or (2) add a short checklist UI to the `time measure` app to guide measurements.
