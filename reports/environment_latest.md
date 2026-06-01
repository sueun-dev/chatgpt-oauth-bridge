# OAuth Bridge Environment Probe

- Generated: `2026-06-01T17:48:37Z`

## Checks

| Check | OK | Evidence |
|---|---|---|
| Token source | `True` | `source=codex-cli; has_access_token=True; seconds_remaining=422558; error=None` |
| Codex model discovery | `False` | `http_status=None; model_count=None; error_type=ConnectError; error=[Errno 8] nodename nor servname provided, or not known` |
| Localhost bind | `False` | `host=127.0.0.1; port=0; error_type=PermissionError; error=[Errno 1] Operation not permitted` |

## Diagnostics

- DNS/network blocked: `True`
- Localhost socket denied: `True`
- Live environment OK: `False`

## Next Actions

- Run from a shell with DNS/network access to chatgpt.com, github.com, and api.openai.com.
- Run from a normal local shell; this sandbox denies socket bind for every localhost port.
