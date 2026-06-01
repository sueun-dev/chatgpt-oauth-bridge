# OAuth Bridge Environment Probe

- Generated: `2026-06-01T18:07:40Z`

## Checks

| Check | OK | Evidence |
|---|---|---|
| Token source | `True` | `source=codex-cli; has_access_token=True; seconds_remaining=421416; error=None` |
| Codex model discovery | `True` | `http_status=200; model_count=7; error_type=None; error=None` |
| Localhost bind | `True` | `host=127.0.0.1; port=51228; error_type=None; error=None` |

## Diagnostics

- DNS/network blocked: `False`
- Localhost socket denied: `False`
- Live environment OK: `True`

## Next Actions

- No environment blocker detected by this probe.
