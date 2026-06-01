# OAuth Matrix Report

- Started: `2026-05-29T21:53:12Z`
- Finished: `2026-05-29T21:55:56Z`
- Runtime source: `codex-cli`
- Text model: `gpt-5.5`
- Image host model: `gpt-5.5`

| Status | Test | Category | Evidence |
|---|---|---|---|
| `pass` | `token_inventory` | `auth` |  |
| `pass` | `no_platform_api_key_env` | `auth` |  |
| `pass` | `codex_models` | `codex-oauth` | model_count=7 |
| `pass` | `codex_text_response` | `codex-oauth` | model=gpt-5.5; output_text=oauth text ok |
| `pass` | `codex_vision_input` | `codex-oauth` | model=gpt-5.5; output_text=Red |
| `pass` | `codex_image_generation` | `codex-oauth` | path=artifacts/codex_oauth_image.png; bytes=915181; width=1024; height=1024 |
| `pass` | `codex_drawing_generation` | `codex-oauth` | path=artifacts/codex_oauth_drawing.png; bytes=801640; width=1024; height=1024 |
| `expected_blocked` | `codex_audio_speech_route` | `codex-oauth` |  |
| `expected_blocked` | `official_api_models_list_with_oauth` | `official-api-oauth` | http_status=403; url=https://api.openai.com/v1/models |
| `expected_blocked` | `official_api_files_list_with_oauth` | `official-api-oauth` | http_status=401; url=https://api.openai.com/v1/files |
| `expected_blocked` | `official_api_chat_completions_with_oauth` | `official-api-oauth` | http_status=401; url=https://api.openai.com/v1/chat/completions |
| `expected_blocked` | `official_api_completions_legacy_with_oauth` | `official-api-oauth` | http_status=401; url=https://api.openai.com/v1/completions |
| `expected_blocked` | `official_api_responses_with_oauth` | `official-api-boundary` | http_status=401; url=https://api.openai.com/v1/responses |
| `expected_blocked` | `official_api_responses_web_search_with_oauth` | `official-api-boundary` | http_status=401; url=https://api.openai.com/v1/responses |
| `expected_blocked` | `official_api_responses_input_tokens_with_oauth` | `official-api-boundary` | http_status=401; url=https://api.openai.com/v1/responses/input_tokens |
| `expected_blocked` | `official_api_image_with_oauth` | `official-api-boundary` | http_status=401; url=https://api.openai.com/v1/images/generations |
| `expected_blocked` | `official_api_image_edit_with_oauth` | `official-api-boundary` | http_status=401; url=https://api.openai.com/v1/images/edits |
| `expected_blocked` | `official_api_image_variation_with_oauth` | `official-api-boundary` | http_status=404; url=https://api.openai.com/v1/images/variations |
| `expected_blocked` | `official_api_tts_with_oauth` | `official-api-boundary` | http_status=401; url=https://api.openai.com/v1/audio/speech |
| `pass` | `official_api_stt_with_oauth` | `official-api-boundary` | http_status=200; url=https://api.openai.com/v1/audio/transcriptions |
| `expected_blocked` | `official_api_translation_with_oauth` | `official-api-oauth` | http_status=401; url=https://api.openai.com/v1/audio/translations |
| `pass` | `official_api_realtime_with_oauth` | `official-api-boundary` | http_status=200; url=https://api.openai.com/v1/realtime/client_secrets |
| `pass` | `official_api_realtime_audio_websocket_with_oauth` | `official-api-oauth` | audio_path=artifacts/realtime_oauth_audio_response.pcm16; audio_bytes=127206; transcript=oauth realtime ok |
| `pass` | `official_api_realtime_transcription_with_oauth` | `official-api-oauth` | http_status=200; url=https://api.openai.com/v1/realtime/client_secrets |
| `not_available` | `official_api_realtime_sessions_with_oauth` | `official-api-oauth` | http_status=404; url=https://api.openai.com/v1/realtime/sessions |
| `not_available` | `official_api_realtime_transcription_sessions_legacy_shape_with_oauth` | `official-api-boundary` | http_status=404; url=https://api.openai.com/v1/realtime/transcription_sessions |
| `pass` | `official_api_realtime_translation_client_secret_with_oauth` | `official-api-oauth` | http_status=200; client_secret_present=True; translation_language=es; url=https://api.openai.com/v1/realtime/translations/client_secrets |
| `pass` | `official_api_realtime_calls_with_oauth` | `official-api-oauth` | http_status=201; answer_sdp_present=True; answer_sdp_line_count=40; answer_sdp_sha256_prefix=38aebd44f2d65754; location_header_present=True; location_path_shape=/realtime/calls/<call-id>; url=https://api.openai.com/v1/realtime/calls |
| `auth_accepted_request_invalid` | `official_api_realtime_calls_shape_probe_with_oauth` | `official-api-boundary` | http_status=400; url=https://api.openai.com/v1/realtime/calls |
| `pass` | `official_api_embeddings_with_oauth` | `official-api-boundary` | http_status=200; url=https://api.openai.com/v1/embeddings |
| `expected_blocked` | `official_api_moderation_with_oauth` | `official-api-boundary` | http_status=401; url=https://api.openai.com/v1/moderations |
| `expected_blocked` | `official_api_vector_stores_list_with_oauth` | `official-api-catalog` | http_status=401; url=https://api.openai.com/v1/vector_stores?limit=1 |
| `expected_blocked` | `official_api_batches_list_with_oauth` | `official-api-catalog` | http_status=401; url=https://api.openai.com/v1/batches?limit=1 |
| `expected_blocked` | `official_api_fine_tuning_jobs_list_with_oauth` | `official-api-catalog` | http_status=401; url=https://api.openai.com/v1/fine_tuning/jobs?limit=1 |
| `expected_blocked` | `official_api_evals_list_with_oauth` | `official-api-catalog` | http_status=401; url=https://api.openai.com/v1/evals?limit=1 |
| `expected_blocked` | `official_api_skills_list_with_oauth` | `official-api-catalog` | http_status=401; url=https://api.openai.com/v1/skills?limit=1 |
| `expected_blocked` | `official_api_containers_list_with_oauth` | `official-api-catalog` | http_status=401; url=https://api.openai.com/v1/containers?limit=1 |
| `expected_blocked` | `official_api_videos_list_with_oauth` | `official-api-catalog` | http_status=401; url=https://api.openai.com/v1/videos?limit=1 |
| `expected_blocked` | `official_api_videos_create_shape_with_oauth` | `official-api-catalog` | http_status=401; url=https://api.openai.com/v1/videos |
| `expected_blocked` | `official_api_upload_create_cancel_with_oauth` | `official-api-catalog` | http_status=401; url=https://api.openai.com/v1/uploads |
| `expected_blocked` | `official_api_assistants_list_with_oauth` | `official-api-catalog` | http_status=401; url=https://api.openai.com/v1/assistants?limit=1 |
| `auth_accepted_request_invalid` | `official_api_conversation_create_delete_with_oauth` | `official-api-catalog` | http_status=400; url=https://api.openai.com/v1/conversations |
| `expected_blocked` | `official_api_thread_create_delete_with_oauth` | `official-api-catalog` | http_status=401; url=https://api.openai.com/v1/threads |
| `expected_blocked` | `official_api_chatkit_session_with_oauth` | `official-api-catalog` | http_status=401; workflow_id_source=missing-env-placeholder; url=https://api.openai.com/v1/chatkit/sessions |
| `expected_blocked` | `official_api_chatkit_threads_list_with_oauth` | `official-api-catalog` | http_status=401; url=https://api.openai.com/v1/chatkit/threads?limit=1 |
| `expected_blocked` | `official_api_audio_voice_consents_list_with_oauth` | `official-api-catalog` | http_status=401; url=https://api.openai.com/v1/audio/voice_consents?limit=1 |
| `expected_blocked` | `official_api_audio_voices_create_shape_with_oauth` | `official-api-catalog` | http_status=401; url=https://api.openai.com/v1/audio/voices |
| `expected_blocked` | `official_api_admin_projects_list_with_oauth` | `admin-api-oauth` | http_status=401; url=https://api.openai.com/v1/organization/projects?limit=1 |
| `expected_blocked` | `official_api_admin_users_list_with_oauth` | `admin-api-oauth` | http_status=401; url=https://api.openai.com/v1/organization/users?limit=1 |
| `expected_blocked` | `official_api_admin_keys_list_with_oauth` | `admin-api-oauth` | http_status=401; url=https://api.openai.com/v1/organization/admin_api_keys?limit=1 |
| `expected_blocked` | `official_api_audit_logs_list_with_oauth` | `admin-api-oauth` | http_status=401; url=https://api.openai.com/v1/organization/audit_logs?limit=1 |
| `expected_blocked` | `official_api_usage_completions_with_oauth` | `admin-api-oauth` | http_status=401; url=https://api.openai.com/v1/organization/usage/completions?start_time=1780005356&limit=1 |
| `expected_blocked` | `official_api_costs_with_oauth` | `admin-api-oauth` | http_status=401; url=https://api.openai.com/v1/organization/costs?start_time=1780005356&limit=1 |

## Meaning

- `pass`: Codex/ChatGPT OAuth reached the surface and produced a usable result.
- `expected_blocked`: The endpoint rejected OAuth as expected or the Codex backend has no route for it.
- `auth_accepted_request_invalid`: OAuth reached the route, then the probe payload or missing object shape was rejected before any expensive job was started.
- `resource_required`: OAuth got far enough that a real workflow/resource ID is needed to continue.
- `not_available`: The route is documented or source-backed, but this deployment returned an invalid-url/not-routed response.
- `fail`: The test should have worked under the current OAuth path but did not.

No access tokens, refresh tokens, API keys, or Authorization headers are stored in this report.
