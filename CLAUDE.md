# ha-ps5-remoteplay

Home Assistant custom integration, installed through HACS. It creates one power switch per PS5 (wake, standby, status). Domain `ps5_remoteplay`, GitHub `iharosi/ha-ps5-remoteplay`. The protocol work is done by the `ps5-remoteplay` library, pinned exactly in `manifest.json`.

## Related repos

- `~/Sites/other/ps5-remoteplay`: the protocol library. Its CLAUDE.md documents the console's session behaviour; read it before debugging wake or standby failures.
- `~/Sites/other/playactor`: TypeScript reference implementation.

## Commands

```sh
source .venv/bin/activate
pytest -q          # uses pytest-homeassistant-custom-component
```

- Keep the `ps5-remoteplay` pin in `requirements-test.txt` equal to the one in `manifest.json`.

## Layout (`custom_components/ps5_remoteplay/`)

- `coordinator.py`: status polling and last-known-state handling
- `switch.py`: the power switch entity
- `config_flow.py`, `strings.json`, `translations/en.json`: setup UI
- `const.py`: timing values
- `brand/`: the user's own outline-controller icons. Black `icon.png`/`icon@2x.png`, white `dark_icon.png`/`dark_icon@2x.png`. The user rejected a blue variant and an earlier design, so don't redesign them.

## Behaviour (timing values chosen by the user)

- Status poll every 3 s (`SCAN_INTERVAL`), for fast pickup when the console is switched on with the controller.
- The switch keeps its last state for 30 s of silence, then shows `unavailable` (`UNAVAILABLE_AFTER`). The console goes quiet for 10–20 s while changing power state.
- After a command, the switch shows the requested state for up to 60 s (`PENDING_STATE_SECONDS`).
- Default entity icon: `mdi:sony-playstation`.

## Release routine

1. If a new library version is needed, publish it to PyPI first and confirm `pip install --no-cache-dir ps5-remoteplay==X` works. v0.1.7 once shipped pinning an unpublished library, and Home Assistant failed to load it.
2. Bump `version` in `manifest.json` (and the library pin in both `manifest.json` and `requirements-test.txt` if it changed), commit and push.
3. Wait for the Validate workflow (HACS + hassfest) to pass.
4. Create the GitHub release. The new tag triggers another validation run.

hassfest can also run locally without Docker:
1. Sparse-clone `home-assistant/core` at the installed HA version and run `git sparse-checkout set script`.
2. Install `ruff` and `infrared-protocols`.
3. Run `python -m script.hassfest --action validate --integration-path <path>`.

It caught a URL inside `strings.json` that Home Assistant rejects.

## HACS

- Submitted to the HACS default list on 2026-09-16 as **hacs/default PR #11033**. All checks pass. Review takes months; never request reviewers. The fork `iharosi/default` exists only for that PR and can be deleted once the PR is merged or closed.
- HACS shows a placeholder instead of our icon. **Nothing to fix on our side.** HACS loads icons from `brands.home-assistant.io/_/{domain}/icon.png`, and the brands repo stopped accepting custom integrations when HA 2026.3 added local `brand/` folders. This is a known, still-open HACS bug (hacs/integration #5171, #5179, #5223, #5402). Home Assistant's own device page shows the icon correctly.

## GitHub Actions security (verified 2026-09-16)

- The default workflow token is read-only, and Actions can't approve PRs.
- Workflows from first-time contributors' forks need approval.
- No repository secrets and no `pull_request_target` triggers.
- `validate.yml` uses `permissions: {}`.

Local environment details (console, network, working preferences) are in `CLAUDE.local.md`, which is not committed.
