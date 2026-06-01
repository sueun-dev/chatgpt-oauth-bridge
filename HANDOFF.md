# Handoff: ChatGPT OAuth Bridge

Last updated: 2026-06-01, America/New_York.

This repo is the local project at:

```bash
/Users/sueuncho/Documents/openao-oauth-access
```

GitHub remote:

```bash
https://github.com/sueun-dev/chatgpt-oauth-bridge.git
```

At the implementation checkpoint before adding this handoff file:

```bash
branch=main
implementation_commit=6b896ad8f95c1ef3ca66655f31ba8da8e26cc746
previous_remote_commit=f32d458ec25d110ceb784ae64858e2440824b7d3
```

That implementation commit was pushed to `origin/main` with:

```bash
bash reports/openai_bridge_publish_gate.sh --push
```

After this handoff file is committed, use this as the authoritative state:

```bash
git log -1 --oneline
git status --short --branch
git rev-parse HEAD
git rev-parse origin/main
```

## What this repo now does

This repo is a local compatibility bridge around ChatGPT/Codex OAuth-style access. It is not claiming that ChatGPT OAuth is a general OpenAI Platform API credential.

The current boundary is:

- `5` routes are classified as direct official OAuth-verified coverage.
- `167` routes are classified as local compatibility or ChatGPT backend bridge coverage.
- API/Admin-key-only behavior must stay separate from OAuth/local compatibility claims.
- Launch-ready claims require live environment checks, not only source reading or offline smoke tests.

The main user-facing entry point is:

```bash
python3 bridge.py
```

Important commands now available include:

```bash
python3 bridge.py preflight --no-write
python3 bridge.py offline-smoke --no-write
python3 bridge.py publish-check --no-write --strict
python3 bridge.py publish-api --dry-run --no-write
python3 bridge.py env
python3 bridge.py live-check --no-write
python3 bridge.py status
python3 bridge.py doctor
python3 bridge.py verdict --strict
```

## What was implemented

The repo now has a broader CLI surface for setup, auditing, publishing, and launch readiness:

- `serve`
- `smoke`
- `sdk-smoke`
- `offline-smoke`
- `readiness`
- `env`
- `guide`
- `config`
- `quickstart`
- `coverage`
- `fallback`
- `policy`
- `boundaries`
- `status`
- `verdict`
- `check`
- `migrate`
- `audit`
- `preflight`
- `publish-check`
- `publish-api`
- `live-check`
- `finish`
- `doctor`

The report-style commands were made compatible with `--no-write` where needed, especially for preflight and publish workflows.

Generated evidence and guide files were added under `reports/`, including:

- `reports/openai_surface_audit_latest.md`
- `reports/compatibility_guide_latest.md`
- `reports/coverage_map_latest.md`
- `reports/coverage_map_latest.csv`
- `reports/openai_bridge_route_policy.md`
- `reports/openai_bridge_route_policy.csv`
- `reports/boundary_playbook_latest.md`
- `reports/client_config_latest.md`
- `reports/quickstart_latest.md`
- `reports/readiness_latest.md`
- `reports/goal_audit_latest.md`
- `reports/status_latest.md`
- `reports/publish_check_latest.md`
- `reports/live_check_latest.md`
- `reports/environment_latest.md`
- `reports/doctor_latest.md`
- `reports/router_offline_smoke_latest.md`

Operational helper scripts were added:

- `reports/openai_bridge_ci_gate.sh`
- `reports/openai_bridge_publish_gate.sh`
- `reports/openai_bridge_finish_gate.sh`
- `reports/openai_bridge_launch_gate.sh`
- `reports/openai_bridge.env.example`

GitHub API fallback publishing was added in:

```bash
src/github_api_publish.py
```

It supports:

- `python3 bridge.py publish-api --dry-run`
- `python3 bridge.py publish-api --branch main`
- token discovery through `GITHUB_TOKEN` or `GH_TOKEN`
- local tracking fallback during dry-runs when shell DNS is blocked
- ignored local publish-plan outputs:
  - `reports/github_api_publish_plan_latest.md`
  - `reports/github_api_publish_plan_latest.json`

## Verified so far

The following checks passed during the implementation checkpoint:

```bash
python3 bridge.py preflight --no-write
python3 bridge.py offline-smoke --no-write
python3 bridge.py publish-api --dry-run --no-write
PYTHONPYCACHEPREFIX=/private/tmp/chatgpt-oauth-bridge-pycache python3 -m compileall bridge.py setup_oauth.py src
git diff --check
git diff --cached --check
```

The publish gate also passed and pushed the implementation commit:

```bash
bash reports/openai_bridge_publish_gate.sh --push
```

Observed result:

```text
Release preflight: pass
OAuth bridge publish check: ready
Published tree matches the configured upstream branch.
```

After the handoff commit, a fresh environment probe passed:

```bash
python3 bridge.py env
```

Observed result:

```text
token_source: ok=True source=codex-cli
codex_model_discovery: ok=True status=200 model_count=7
localhost_bind: ok=True
diagnostics: dns_or_network_blocked=False localhost_socket_denied=False live_environment_ok=True
```

A fresh live launch check still failed:

```bash
python3 bridge.py live-check --no-write
```

Observed result:

```text
OAuth bridge live launch check: fail
pass: environment_probe
fail: http_proxy_smoke
fail: openai_python_sdk_smoke
pass: readiness_report
fail: doctor_strict
```

So the current blocker is no longer basic network or localhost access in this shell. The remaining blocker is functional live/package smoke behavior.

## Known limits

Do not claim any of these until they are actually true on the machine being used:

- Do not claim the bridge is launch-ready unless `python3 bridge.py live-check --no-write` passes.
- Do not claim every OpenAI API endpoint has direct hosted OAuth support.
- Do not merge API-key/Admin-key-only behavior into the OAuth claim.
- Do not treat offline smoke results as live server proof.

During earlier local checks, the Codex shell had environment blockers:

- DNS/network failures for some remote hosts.
- localhost socket bind denied with `PermissionError: [Errno 1] Operation not permitted`.
- no usable `GITHUB_TOKEN` or `GH_TOKEN` at that time.
- `gh auth status` reported an invalid local GitHub token.

The GitHub push later succeeded from this environment, so re-check the current machine directly instead of assuming the older DNS/GitHub blocker still applies.

## Continue on another computer

Clone the repo:

```bash
git clone https://github.com/sueun-dev/chatgpt-oauth-bridge.git
cd chatgpt-oauth-bridge
git log -1 --oneline
git status --short --branch
```

Run the local verification gates:

```bash
python3 bridge.py preflight --no-write
python3 bridge.py publish-check --no-write --strict
python3 bridge.py publish-api --dry-run --no-write
python3 bridge.py env
python3 bridge.py live-check --no-write
```

If the machine allows localhost binding, test the real local bridge path:

```bash
python3 bridge.py serve --port 8787
```

In another terminal:

```bash
python3 bridge.py smoke --base-url http://127.0.0.1:8787 --no-write
python3 bridge.py sdk-smoke --base-url http://127.0.0.1:8787 --no-write
```

For publishing future local changes:

```bash
bash reports/openai_bridge_publish_gate.sh --push
```

If normal git push is blocked but GitHub API access works:

```bash
GITHUB_TOKEN=YOUR_TOKEN python3 bridge.py publish-api --branch main
python3 bridge.py publish-check --no-write --strict
```

## Best next work

1. Re-run `live-check` on the other computer.
2. Run the actual `serve` plus `smoke` and `sdk-smoke` path if localhost binding works.
3. Refresh official OpenAI API coverage before making public claims, because API surfaces can change.
4. Only after live checks pass, update the README wording from local-ready to launch-ready if that is still accurate.
