# OAuth Bridge Doctor

- Generated: `2026-06-06T13:20:39Z`
- Package health OK: `True`
- Local router OK: `True`
- Live environment OK: `True`
- Full goal complete: `True`
- Platform fallback enabled: `False`
- Bottom line: Package health checks pass and the full goal is complete.

## Coverage

- Official paths: `172`

| Category | Paths |
|---|---:|
| `direct_official_oauth_verified` | 5 |
| `local_compat_or_chatgpt_backend_bridge` | 167 |

## Environment

| Check | OK | Error |
|---|---|---|
| Codex model discovery | `True` | `None` |
| Localhost bind | `True` | `None` |

## Platform Fallback

| Check | Value |
|---|---|
| Enabled | `False` |
| Mode | `boundary` |
| API key present | `False` |
| Access token present | `False` |
| Admin key present | `False` |

## Checks

| Status | Check | Return Code |
|---|---|---:|
| `pass` | `setup_no_smoke` | 0 |
| `pass` | `environment_probe` | 0 |
| `pass` | `offline_router_smoke` | 0 |
| `pass` | `route_manifest` | 0 |
| `pass` | `status_report` | 0 |
| `pass` | `readiness_report` | 0 |
| `pass` | `git_diff_check` | 0 |

## Next Actions

- Use python bridge.py migrate path/to/app --fail-on-boundary before switching an app to the bridge.
