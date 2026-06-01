# OAuth Bridge Doctor

- Generated: `2026-06-01T17:48:39Z`
- Package health OK: `True`
- Local router OK: `True`
- Live environment OK: `False`
- Full goal complete: `False`
- Platform fallback enabled: `False`
- Bottom line: Package health checks pass, but the current environment cannot prove the full goal.

## Coverage

- Official paths: `172`

| Category | Paths |
|---|---:|
| `direct_official_oauth_verified` | 5 |
| `local_compat_or_chatgpt_backend_bridge` | 167 |

## Environment

| Check | OK | Error |
|---|---|---|
| Codex model discovery | `False` | `[Errno 8] nodename nor servname provided, or not known` |
| Localhost bind | `False` | `[Errno 1] Operation not permitted` |

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

## Warnings

- Full goal is not complete in this environment.
- Current environment cannot reach Codex model discovery.
- Current environment cannot bind localhost for live HTTP/SDK smoke.

## Next Actions

- Run python bridge.py live-check from a normal local shell that can bind localhost.
- Run from an environment with network access before relying on model-backed calls.
- Use python bridge.py migrate path/to/app --fail-on-boundary before switching an app to the bridge.
