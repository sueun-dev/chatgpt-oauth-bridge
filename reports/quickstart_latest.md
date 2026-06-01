# OAuth Bridge Quickstart

- Generated: `2026-06-01T16:15:22Z`
- Goal complete: `False`
- Bottom line: Not complete: the documented path surface is covered by direct OAuth or explicit local compatibility, but only 5 paths are direct hosted OAuth and this environment cannot prove live HTTP/SDK behavior.
- Base URL: `http://127.0.0.1:8787/v1`
- Placeholder API key: `oauth-local-proxy`

## Current Counts

| Metric | Count |
|---|---:|
| `official_paths` | 172 |
| `direct_official_oauth_verified` | 5 |
| `local_compat_or_chatgpt_backend_bridge` | 167 |
| `usable_without_platform_key` | 172 |
| `hosted_oauth_complete` | False |
| `local_bridge_surface_complete` | True |
| `api_key_or_admin_key_required` | 0 |
| `unfinished_or_resource_bound` | 0 |

## Route Policy

| Metric | Count |
|---|---:|
| `total_paths` | 172 |
| `direct_hosted_oauth_verified` | 5 |
| `local_bridge_compatibility` | 167 |
| `allow_local_bridge` | 172 |
| `deny_local_bridge` | 0 |
| `allow_oauth_only` | 5 |
| `deny_oauth_only` | 167 |
| `platform_fallback_candidates` | 0 |
| `resource_bound` | 0 |

## Publish State

| Metric | Value |
|---|---|
| Publish ready | `False` |
| Local tree ready | `True` |
| Branch | `main` |
| Upstream | `origin/main` |
| Head matches upstream | `False` |

## First Run

```bash
python bridge.py setup
python bridge.py quickstart
bash reports/openai_bridge_launch_gate.sh
python bridge.py serve --host 127.0.0.1 --port 8787
```

## App Environment

```bash
set -a; source reports/openai_bridge.env.example; set +a
```

## Scan Before Migrating

```bash
python bridge.py migrate path/to/your/app --fail-on-boundary
bash reports/openai_bridge_ci_gate.sh path/to/your/app
```

## Check Before Publishing

```bash
bash reports/openai_bridge_publish_gate.sh --push
python bridge.py finish --push
```

## Steps

- `python bridge.py setup`: OAuth source is present. If live model calls are unavailable, setup prints the missing network/token condition.
- `python bridge.py quickstart`: Writes env, CI gate, launch gate, quickstart, route policy, and goal audit reports.
- `python bridge.py serve --host 127.0.0.1 --port 8787`: Runs the local /v1 proxy when localhost binding is allowed.
- `set -a; source reports/openai_bridge.env.example; set +a`: OPENAI_BASE_URL points at the local bridge and OPENAI_API_KEY is the placeholder SDK value.
- `python bridge.py migrate path/to/your/app --fail-on-boundary`: Ready paths and any blocked/API-key boundary paths are separated before traffic moves.
- `bash reports/openai_bridge_ci_gate.sh path/to/your/app`: Fails when Platform-only routes are introduced into an OAuth-only app.
- `bash reports/openai_bridge_launch_gate.sh`: Runs environment, HTTP proxy smoke, SDK smoke, readiness, and strict doctor checks in one gate.
- `bash reports/openai_bridge_publish_gate.sh --push`: Runs preflight, pushes the current branch, then fails unless local HEAD matches the configured upstream branch.
- `python bridge.py finish --push`: Runs the publish gate first, then the live launch gate. It fails until GitHub, network, and localhost evidence all pass.
- `python bridge.py verdict --strict`: Exits non-zero until the full-goal verdict is complete.

## OAuth-Only Rules

- Strict hosted OAuth mode allows exactly 5 documented paths.
- Local bridge mode allows 172 documented paths through direct OAuth or local compatibility.
- Local bridge mode blocks 0 documented paths when the route policy reports a Platform/Admin boundary or missing live resource proof.
- Do not treat local compatibility routes as hosted OpenAI Platform OAuth proof.
- Do not use the placeholder oauth-local-proxy value as a Platform API credential.

## Fallback Rules

- Fallback is disabled by default.
- Set OAUTH_BRIDGE_ENABLE_PLATFORM_FALLBACK=1 only when the app intentionally uses official Platform/Admin credentials.
- Use OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=boundary for boundary-only forwarding.
- Use OAUTH_BRIDGE_PLATFORM_FALLBACK_MODE=prefer only when exact hosted OpenAI API behavior should override local compatibility.

## Why This Is Not Complete Yet

- The current environment cannot verify live model discovery or localhost HTTP/SDK smoke.
- GitHub publish state is not ready: local HEAD does not match origin/main.

## Generated Files

- `quickstart`: `reports/quickstart_latest.md`
- `client_config`: `reports/client_config_latest.md`
- `env_example`: `reports/openai_bridge.env.example`
- `ci_gate`: `reports/openai_bridge_ci_gate.sh`
- `launch_gate`: `reports/openai_bridge_launch_gate.sh`
- `publish_gate`: `reports/openai_bridge_publish_gate.sh`
- `finish_gate`: `reports/openai_bridge_finish_gate.sh`
- `route_policy`: `reports/openai_bridge_route_policy.md`
- `route_policy_json`: `reports/openai_bridge_route_policy.json`
- `route_policy_csv`: `reports/openai_bridge_route_policy.csv`
- `goal_audit`: `reports/goal_audit_latest.md`
- `publish_check`: `reports/publish_check_latest.md`
- `boundary_playbook`: `reports/boundary_playbook_latest.md`
