# Deep OAuth Research Report

- Started: `2026-05-11T23:52:58Z`
- Finished: `2026-05-11T23:53:25Z`
- Runtime source: `codex-cli`
- Text model: `gpt-5.5`
- openai/codex source HEAD checked this run: `4859d80ffeec76cc59c95fd274157c6b5560b4d2`

| Status | Probe | Evidence |
|---|---|---|
| `pass` | `chatgpt_backend_usage` | http_status=200; url=https://chatgpt.com/backend-api/wham/usage; has_rate_limit=True; has_credits=True |
| `pass` | `codex_backend_models_direct` | http_status=200; url=https://chatgpt.com/backend-api/codex/models; models_count=7 |
| `pass` | `codex_backend_responses_text_direct` | http_status=200; url=https://chatgpt.com/backend-api/codex/responses |
| `auth_accepted_request_invalid` | `chatgpt_backend_requirements` | http_status=400; url=https://chatgpt.com/backend-api/wham/config/requirements |
| `pass` | `chatgpt_backend_agent_identities_jwks` | http_status=200; url=https://chatgpt.com/backend-api/wham/agent-identities/jwks; jwks_keys_count=1 |
| `pass` | `chatgpt_backend_accounts_check_shape` | http_status=200; url=https://chatgpt.com/backend-api/accounts/check/v4-2023-04-27; accounts_count=2; account_ordering_count=1 |
| `pass` | `chatgpt_backend_me_shape` | http_status=200; url=https://chatgpt.com/backend-api/me; object=user; has_id=True; has_email=True |
| `pass` | `chatgpt_backend_aura_site_status_example` | http_status=200; url=https://chatgpt.com/backend-api/aura/site_status; enabled=True; feature_status_keys=['agent', 'analytics', 'cursor_chat', 'page_content', 'page_view', 'side_chat', 'user_site_settings_toggle'] |
| `auth_accepted_request_invalid` | `chatgpt_codex_api_usage_path` | http_status=404; url=https://chatgpt.com/backend-api/api/codex/usage |
| `auth_accepted_request_invalid` | `chatgpt_api_codex_usage_path` | http_status=404; url=https://chatgpt.com/api/codex/usage |
| `auth_accepted_request_invalid` | `chatgpt_api_codex_models_path` | http_status=404; url=https://chatgpt.com/api/codex/models |
| `auth_accepted_request_invalid` | `chatgpt_api_codex_tasks_list` | http_status=404; url=https://chatgpt.com/api/codex/tasks/list |
| `pass` | `chatgpt_wham_tasks_list` | http_status=200; url=https://chatgpt.com/backend-api/wham/tasks/list; items_count=0 |
| `auth_accepted_request_invalid` | `chatgpt_wham_task_detail_missing_id_shape` | http_status=404; url=https://chatgpt.com/backend-api/wham/tasks/task_000000000000000000000000 |
| `auth_accepted_request_invalid` | `chatgpt_api_codex_task_detail_missing_id_shape` | http_status=404; url=https://chatgpt.com/api/codex/tasks/task_000000000000000000000000 |
| `auth_accepted_request_invalid` | `chatgpt_wham_task_sibling_turns_missing_id_shape` | http_status=404; url=https://chatgpt.com/backend-api/wham/tasks/task_000000000000000000000000/turns/turn_000000000000000000000000/sibling_turns |
| `auth_accepted_request_invalid` | `chatgpt_api_codex_task_sibling_turns_missing_id_shape` | http_status=404; url=https://chatgpt.com/api/codex/tasks/task_000000000000000000000000/turns/turn_000000000000000000000000/sibling_turns |
| `auth_accepted_request_invalid` | `chatgpt_api_codex_environments` | http_status=404; url=https://chatgpt.com/api/codex/environments |
| `pass` | `chatgpt_wham_environments` | http_status=200; url=https://chatgpt.com/backend-api/wham/environments; items_count=5 |
| `auth_accepted_request_invalid` | `chatgpt_api_codex_config_requirements` | http_status=404; url=https://chatgpt.com/api/codex/config/requirements |
| `auth_accepted_request_invalid` | `chatgpt_api_codex_apps_mcp_initialize` | http_status=302; url=https://chatgpt.com/api/codex/apps |
| `auth_accepted_request_invalid` | `chatgpt_api_codex_responses_text` | http_status=302; url=https://chatgpt.com/api/codex/responses |
| `pass` | `chatgpt_backend_file_upload` | http_status=200; url=https://chatgpt.com/backend-api/files; file_id_prefix=file_0000000; uri=sediment://file_00000000c6ac71fba7f66c31d3aefa92; upload_http_status=201; finalize_status=success; download_url_present=True; download_url_host=sdmntprwestcentralus.oaiusercontent.com; download_probe_http_status=200; download_probe_sha256_prefix=4580327da363bb74 |
| `pass` | `chatgpt_backend_curated_plugins_export` | http_status=200; url=https://chatgpt.com/backend-api/plugins/export/curated; download_url_present=True; download_url_host=files.openai.com; download_probe_http_status=200 |
| `auth_accepted_request_invalid` | `chatgpt_backend_ps_plugins_list_global` | http_status=404; url=https://chatgpt.com/backend-api/ps/plugins/list |
| `auth_accepted_request_invalid` | `chatgpt_backend_ps_plugins_installed_global` | http_status=404; url=https://chatgpt.com/backend-api/ps/plugins/installed |
| `auth_accepted_request_invalid` | `chatgpt_backend_ps_plugins_workspace_shared` | http_status=404; url=https://chatgpt.com/backend-api/ps/plugins/workspace/shared |
| `not_run_no_candidate` | `chatgpt_backend_ps_plugins_first_global_detail` | url=https://chatgpt.com/backend-api/ps/plugins/<plugin-id>; reason=no global plugin id returned by list |
| `not_run_no_candidate` | `chatgpt_backend_ps_plugins_first_skill_detail` | url=https://chatgpt.com/backend-api/ps/plugins/<plugin-id>/skills/<skill-name>; reason=no global plugin id returned by list |
| `pass` | `chatgpt_backend_plugins_list_legacy` | http_status=200; url=https://chatgpt.com/backend-api/plugins/list; items_count=121 |
| `pass` | `chatgpt_backend_plugins_featured` | http_status=200; url=https://chatgpt.com/backend-api/plugins/featured; items_count=21 |
| `pass` | `chatgpt_backend_plugins_featured_chat` | http_status=200; url=https://chatgpt.com/backend-api/plugins/featured; items_count=19 |
| `pass` | `chatgpt_backend_connectors_directory_list` | http_status=200; url=https://chatgpt.com/backend-api/connectors/directory/list; apps_count=1004; pages_fetched=1 |
| `pass` | `chatgpt_backend_connectors_directory_workspace` | http_status=200; url=https://chatgpt.com/backend-api/connectors/directory/list_workspace; apps_count=1004 |
| `pass` | `chatgpt_backend_environments_by_repo_openai_codex` | http_status=200; url=https://chatgpt.com/backend-api/wham/environments/by-repo/github/openai/codex; items_count=0 |
| `auth_accepted_request_invalid` | `chatgpt_backend_workspace_plugin_shares_created` | http_status=404; url=https://chatgpt.com/backend-api/ps/plugins/workspace/created |
| `auth_accepted_request_invalid` | `chatgpt_backend_ps_plugins_list_workspace` | http_status=404; url=https://chatgpt.com/backend-api/ps/plugins/list |
| `auth_accepted_request_invalid` | `chatgpt_backend_ps_plugins_installed_workspace` | http_status=404; url=https://chatgpt.com/backend-api/ps/plugins/installed |
| `expected_blocked` | `chatgpt_backend_account_settings` | http_status=401; url=https://chatgpt.com/backend-api/accounts/<account-id>/settings |
| `pass` | `codex_backend_compact` | http_status=200; url=https://chatgpt.com/backend-api/codex/responses/compact; output_count=2 |
| `auth_accepted_request_invalid` | `codex_backend_memories_trace_summarize` | http_status=404; url=https://chatgpt.com/backend-api/codex/memories/trace_summarize |
| `auth_accepted_request_invalid` | `codex_backend_v1_memories_trace_summarize` | http_status=404; url=https://chatgpt.com/backend-api/codex/v1/memories/trace_summarize |
| `auth_accepted_request_invalid` | `codex_backend_realtime_call_json_shape` | http_status=404; url=https://chatgpt.com/backend-api/codex/realtime/calls |
| `auth_accepted_request_invalid` | `openai_realtime_calls_application_sdp_shape` | http_status=400; url=https://api.openai.com/v1/realtime/calls |
| `auth_accepted_request_invalid` | `openai_realtime_calls_multipart_shape` | http_status=400; url=https://api.openai.com/v1/realtime/calls |
| `pass` | `openai_realtime_calls_multipart_valid_sdp` | http_status=201; url=https://api.openai.com/v1/realtime/calls; answer_sdp_present=True; answer_sdp_line_count=40; answer_sdp_sha256_prefix=7521c2f908a0a4f2; location_header_present=True; location_path_shape=/v1/realtime/calls/calls/<call-id> |
| `pass` | `chatgpt_apps_mcp_initialize_probe` | http_status=200; url=https://chatgpt.com/backend-api/wham/apps |
| `pass` | `chatgpt_apps_mcp_tools_list` | http_status=200; url=https://chatgpt.com/backend-api/wham/apps; tools_count=111; initialize_http_status=200 |
| `pass` | `chatgpt_apps_mcp_resources_list` | http_status=200; url=https://chatgpt.com/backend-api/wham/apps; resources_count=0 |
| `pass` | `chatgpt_apps_mcp_prompts_list` | http_status=200; url=https://chatgpt.com/backend-api/wham/apps; prompts_count=0 |
| `pass` | `chatgpt_apps_mcp_github_search_repositories_call` | http_status=200; url=https://chatgpt.com/backend-api/wham/apps; repositories_count=3 |
| `auth_accepted_request_invalid` | `chatgpt_backend_github_repositories_search_route_shape` | http_status=400; url=https://chatgpt.com/backend-api/wham/github/repositories/search |
| `not_run_side_effect` | `source_route_chatgpt_task_create_not_run` | source_route=POST /backend-api/wham/tasks; reason=creates a real Codex cloud task; source-backed but not auto-probed; source_file=openai/codex codex-rs/backend-client/src/client.rs |
| `not_run_side_effect` | `source_route_chatgpt_remote_control_not_run` | source_route=POST /backend-api/wham/remote/control/server/enroll; WSS /backend-api/wham/remote/control/server; reason=enrolls and controls an app-server environment; source-backed but not auto-probed; source_file=openai/codex codex-rs/app-server-transport/src/transport/remote_control |
| `not_run_side_effect` | `source_route_chatgpt_workspace_plugin_share_not_run` | source_route=POST /backend-api/public/plugins/workspace/upload-url; POST /backend-api/public/plugins/workspace; POST /backend-api/public/plugins/workspace/{remote_plugin_id}; PUT /backend-api/ps/plugins/{remote_plugin_id}/shares; DELETE /backend-api/public/plugins/workspace/{remote_plugin_id}; reason=can publish/update/delete a workspace plugin share; source-backed but not auto-probed; source_file=openai/codex codex-rs/core-plugins/src/remote/share.rs |
| `not_run_side_effect` | `source_route_chatgpt_plugin_install_not_run` | source_route=POST /backend-api/ps/plugins/{plugin_id}/install; POST /backend-api/plugins/{plugin_id}/uninstall; reason=changes installed plugin state; source-backed but not auto-probed; source_file=openai/codex codex-rs/core-plugins/src/remote.rs |
| `not_run_side_effect` | `source_route_codex_add_credits_nudge_not_run` | source_route=POST /backend-api/wham/accounts/send_add_credits_nudge_email; POST /api/codex/accounts/send_add_credits_nudge_email; reason=sends a real account email/nudge; source-backed but not auto-probed; source_file=openai/codex codex-rs/backend-client/src/client.rs |
| `not_run_side_effect` | `source_route_codex_analytics_events_not_run` | source_route=POST /backend-api/codex/analytics-events/events; reason=telemetry write path, not an app feature workaround; source_file=openai/codex codex-rs/analytics/src/client.rs |
| `not_oauth_api_key_proxy` | `source_route_codex_responses_api_proxy_not_oauth` | source_route=POST /v1/responses via codex-responses-api-proxy; reason=official Codex proxy is source-backed, but it reads OPENAI_API_KEY from stdin and is not an OAuth-only path; source_file=openai/codex codex-rs/responses-api-proxy/README.md |

No access tokens, refresh tokens, Authorization headers, signed upload URLs, or raw SAS query strings are stored in this report.
