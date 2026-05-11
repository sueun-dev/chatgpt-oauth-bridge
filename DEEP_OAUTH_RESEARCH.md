# Deep OAuth Research

This is the extra pass over routes that are not part of the normal public
`api.openai.com/v1` table, but are used by Codex/ChatGPT clients.

Latest run:

- Command:
  `python src/run_deep_oauth_research.py`
- Time: `2026-05-11T22:47:10Z` to `2026-05-11T22:47:32Z`
- Report: `reports/deep_oauth_research_latest.md`
- Apps tools inventory: `reports/codex_apps_tools_latest.md`
- Auth: Codex CLI OAuth token from `~/.codex/auth.json`; Hermes token was
  expired and refresh returned `401`
- API keys: no `OPENAI_API_KEY`, no `OPENAI_ADMIN_KEY`, no `sk-...`
- Counts: `24` pass, `25` auth-accepted/request-invalid, `2`
  no-candidate probes, `1` workspace/account boundary, `6`
  source-backed side-effect routes not auto-run, `1` source-backed API-key proxy

## Newly Confirmed Working

| Function | Route | Result |
|---|---|---|
| ChatGPT/Codex usage | `GET /backend-api/wham/usage` | `200` |
| Cloud task list | `GET /backend-api/wham/tasks/list` | `200`, `0` tasks |
| Cloud task detail shape | `GET /backend-api/wham/tasks/{task_id}` | dummy ID returned `Invalid task ID` |
| Cloud sibling-turn shape | `GET /backend-api/wham/tasks/{task_id}/turns/{turn_id}/sibling_turns` | dummy ID returned `Invalid task ID` |
| Cloud environments | `GET /backend-api/wham/environments` | `200`, `5` environments |
| Real Codex file upload | `POST /backend-api/files` | `200` |
| File bytes upload | signed upload URL `PUT` | `201` |
| File finalize | `POST /backend-api/files/{file_id}/uploaded` | `success` |
| File download check | signed download URL `GET` | `200` |
| Plugin catalog | `GET /backend-api/plugins/list` | `121` items |
| Featured plugins | `GET /backend-api/plugins/featured?platform=codex` | `20` items |
| Featured Chat plugins | `GET /backend-api/plugins/featured?platform=chat` | `19` items |
| Connector directory | `GET /backend-api/connectors/directory/list` | `892` apps |
| Workspace connector directory | `GET /backend-api/connectors/directory/list_workspace` | `892` apps |
| Repo environment lookup | `GET /backend-api/wham/environments/by-repo/github/openai/codex` | `200`, `0` matches |
| Account shape | `GET /backend-api/accounts/check/v4-2023-04-27` | `200`, values redacted |
| User shape | `GET /backend-api/me` | `200`, values redacted |
| Browser Use site policy | `GET /backend-api/aura/site_status` | `200` for `https://example.com/` |
| Codex compaction | `POST /backend-api/codex/responses/compact` | `200` |
| Codex Apps MCP initialize | `POST /backend-api/wham/apps` | `200` |
| Codex Apps MCP tools | `tools/list` through `wham/apps` | `111` tools |
| Codex Apps MCP resources | `resources/list` through `wham/apps` | `0` resources |
| Codex Apps MCP prompts | `prompts/list` through `wham/apps` | `0` prompts |
| Codex Apps MCP GitHub search | `tools/call github_search_repositories` | `200`, `3` public repos |

The Apps MCP tool inventory is saved separately because listing all `111` tool
names makes the main report noisy. The inventory is metadata only; it did not
call personal-data tools or write-capable tools.

Current inventory split: `90` GitHub tools and `21` Gmail tools. Name-based
classification found `45` read-like and `66` mutation-capable tools. Gmail
message/profile tools were not called because that would inspect personal mail.

## Realtime Calls

`POST /v1/realtime/calls` is not dead. The deep run sent the official
`application/sdp` shape and the Codex multipart shape. The intentionally fake
SDP still returned `invalid_offer`, but the realistic multipart WebRTC offer
returned:

- HTTP `201`
- answer SDP body
- `Location` shape `/v1/realtime/calls/calls/<call-id>`

That means OAuth gets past the route auth gate and can create a Realtime WebRTC
call session here. A production browser path should still pass the SDP generated
by `RTCPeerConnection.createOffer()`, matching the official WebRTC docs and the
Codex app-server docs.

## Source-Backed But Not Auto-Run

These routes are in the latest official `openai/codex` source, but the runner
does not execute them because they mutate real workspace/account state:

- `POST /backend-api/wham/tasks`: creates a Codex cloud task
- `POST /backend-api/wham/remote/control/server/enroll` and
  `WSS /backend-api/wham/remote/control/server`: enroll/control remote
  app-server environment
- `POST /backend-api/public/plugins/workspace/upload-url` and
  `POST /backend-api/public/plugins/workspace`: publish workspace plugin share
- `POST /backend-api/public/plugins/workspace/{remote_plugin_id}`,
  `PUT /backend-api/ps/plugins/{remote_plugin_id}/shares`, and
  `DELETE /backend-api/public/plugins/workspace/{remote_plugin_id}`:
  update/delete workspace plugin share
- `POST /backend-api/ps/plugins/{plugin_id}/install` and
  `POST /backend-api/plugins/{plugin_id}/uninstall`: change plugin install
  state
- `POST /backend-api/wham/accounts/send_add_credits_nudge_email` and
  `POST /api/codex/accounts/send_add_credits_nudge_email`: sends a real account
  nudge email
- `POST /backend-api/codex/analytics-events/events`: telemetry write path

Also source-backed but not OAuth: `codex-responses-api-proxy` forwards
`POST /v1/responses`, but it reads `OPENAI_API_KEY` from stdin. It is not an
OAuth-only path.

## Still Not Working Here

- `https://chatgpt.com/api/codex/usage`: HTML `404`
- `https://chatgpt.com/api/codex/models`: HTML `404`
- `https://chatgpt.com/api/codex/tasks/list`: HTML `404`
- `https://chatgpt.com/api/codex/environments`: HTML `404`
- `https://chatgpt.com/api/codex/config/requirements`: HTML `404`
- `https://chatgpt.com/api/codex/apps`: `302`
- `https://chatgpt.com/api/codex/responses`: `302`
- `GET /backend-api/ps/plugins/list`: `404`
- `GET /backend-api/ps/plugins/installed`: `404`
- `GET /backend-api/ps/plugins/workspace/shared`: `404`
- `GET /backend-api/ps/plugins/workspace/created`: `404`
- `GET /backend-api/ps/plugins/{plugin_id}` and
  `/skills/{skill_name}`: not run because the list endpoint returned no
  candidate plugin id on this deployment
- `GET /backend-api/accounts/<account-id>/settings`: `401`, workspace account
  boundary
- `POST /backend-api/codex/memories/trace_summarize`: `404`
- `POST /backend-api/codex/v1/memories/trace_summarize`: `404`
- `POST /backend-api/codex/realtime/calls`: `404`

## Source Trail

The route search used the official `openai/codex` repo cloned at:

```text
/tmp/openai-codex-oauth-research-latest
commit 4859d80ffeec76cc59c95fd274157c6b5560b4d2
```

Key source files:

- `codex-rs/codex-api/src/files.rs`
- `codex-rs/core/src/mcp_openai_file.rs`
- `codex-rs/codex-api/src/endpoint/realtime_call.rs`
- `codex-rs/codex-mcp/src/mcp/mod.rs`
- `codex-rs/core-plugins/src/remote_legacy.rs`
- `codex-rs/backend-client/src/client.rs`
- `codex-rs/cloud-tasks/src/env_detect.rs`
- `codex-rs/app-server-transport/src/transport/remote_control`
- `codex-rs/core-plugins/src/remote/share.rs`
- `codex-rs/core-plugins/src/remote.rs`
- `codex-rs/responses-api-proxy/README.md`
