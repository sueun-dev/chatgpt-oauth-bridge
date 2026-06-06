# OAuth Compatibility Quick Guide

- Generated: `2026-06-06T13:20:39Z`
- Compatibility map complete: `True`
- Hosted OpenAI OAuth complete: `False`
- Bottom line: Complete as a compatibility map: every documented path has either direct OAuth evidence or a named local bridge path. Only 5 paths are direct hosted OAuth; 167 paths are local or ChatGPT-backend compatibility.
- OpenAPI source: `https://app.stainless.com/api/spec/documented/openai/openapi.documented.yml`
- Official paths: `172`

## What To Do

| Category | Paths | User decision |
|---|---:|---|
| `direct_official_oauth_verified` | 5 | Can call the official OpenAI path with the tested Codex/ChatGPT OAuth token evidence. Re-run the matrix before relying on it for a different account or date. |
| `local_compat_or_chatgpt_backend_bridge` | 167 | Use the local OpenAI-shaped proxy at http://127.0.0.1:8787/v1 or the Python wrapper. This is compatibility, not hosted OpenAI Platform OAuth support. |

## Full Path Guide

| Path | Category | Decision | Evidence |
|---|---|---|---|
| `/audio/transcriptions` | `direct_official_oauth_verified` | Official OAuth verified | `official_api_stt_with_oauth=pass` |
| `/embeddings` | `direct_official_oauth_verified` | Official OAuth verified | `official_api_embeddings_with_oauth=pass` |
| `/realtime/calls` | `direct_official_oauth_verified` | Official OAuth verified | `official_api_realtime_calls_with_oauth=not_available` |
| `/realtime/client_secrets` | `direct_official_oauth_verified` | Official OAuth verified | `official_api_realtime_with_oauth=pass` |
| `/realtime/translations/client_secrets` | `direct_official_oauth_verified` | Official OAuth verified | `official_api_realtime_translation_client_secret_with_oauth=pass` |
| `/assistants` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:assistant_thread_run=pass; offline:thread_run_steps=pass` |
| `/assistants/{assistant_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:assistant_thread_run=pass; offline:thread_run_steps=pass` |
| `/audio/speech` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_tts_with_oauth=expected_blocked` |
| `/audio/translations` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:audio_translations_create=pass` |
| `/audio/voice_consents` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:audio_voice_catalog=pass` |
| `/audio/voice_consents/{consent_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:audio_voice_catalog=pass` |
| `/audio/voices` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:audio_voice_catalog=pass` |
| `/batches` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_batches_list_with_oauth=expected_blocked` |
| `/batches/{batch_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_batches_list_with_oauth=expected_blocked` |
| `/batches/{batch_id}/cancel` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_batches_list_with_oauth=expected_blocked` |
| `/chat/completions` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `codex_text_response=pass` |
| `/chat/completions/{completion_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_chat_completions_with_oauth=expected_blocked` |
| `/chat/completions/{completion_id}/messages` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_chat_completions_with_oauth=expected_blocked` |
| `/chatkit/sessions` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:chatkit_sessions_threads=pass` |
| `/chatkit/sessions/{session_id}/cancel` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:chatkit_sessions_threads=pass` |
| `/chatkit/threads` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:chatkit_sessions_threads=pass` |
| `/chatkit/threads/{thread_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:chatkit_sessions_threads=pass` |
| `/chatkit/threads/{thread_id}/items` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:chatkit_sessions_threads=pass` |
| `/completions` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:completions_create=pass` |
| `/containers` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:containers_files=pass` |
| `/containers/{container_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:containers_files=pass` |
| `/containers/{container_id}/files` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:containers_files=pass` |
| `/containers/{container_id}/files/{file_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:containers_files=pass` |
| `/containers/{container_id}/files/{file_id}/content` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:containers_files=pass` |
| `/conversations` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:conversations_items=pass` |
| `/conversations/{conversation_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:conversations_items=pass` |
| `/conversations/{conversation_id}/items` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:conversations_items=pass` |
| `/conversations/{conversation_id}/items/{item_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:conversations_items=pass` |
| `/evals` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_evals_list_with_oauth=expected_blocked` |
| `/evals/{eval_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_evals_list_with_oauth=expected_blocked` |
| `/evals/{eval_id}/runs` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_evals_list_with_oauth=expected_blocked` |
| `/evals/{eval_id}/runs/{run_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_evals_list_with_oauth=expected_blocked` |
| `/evals/{eval_id}/runs/{run_id}/output_items` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_evals_list_with_oauth=expected_blocked` |
| `/evals/{eval_id}/runs/{run_id}/output_items/{output_item_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_evals_list_with_oauth=expected_blocked` |
| `/files` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_files_list_with_oauth=expected_blocked` |
| `/files/{file_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_files_list_with_oauth=expected_blocked` |
| `/files/{file_id}/content` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_files_list_with_oauth=expected_blocked` |
| `/fine_tuning/alpha/graders/run` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:fine_tuning_graders=pass` |
| `/fine_tuning/alpha/graders/validate` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:fine_tuning_graders=pass` |
| `/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:fine_tuning_jobs=pass` |
| `/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions/{permission_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:fine_tuning_jobs=pass` |
| `/fine_tuning/jobs` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:fine_tuning_jobs=pass` |
| `/fine_tuning/jobs/{fine_tuning_job_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:fine_tuning_jobs=pass` |
| `/fine_tuning/jobs/{fine_tuning_job_id}/cancel` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:fine_tuning_jobs=pass` |
| `/fine_tuning/jobs/{fine_tuning_job_id}/checkpoints` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:fine_tuning_jobs=pass` |
| `/fine_tuning/jobs/{fine_tuning_job_id}/events` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:fine_tuning_jobs=pass` |
| `/fine_tuning/jobs/{fine_tuning_job_id}/pause` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:fine_tuning_jobs=pass` |
| `/fine_tuning/jobs/{fine_tuning_job_id}/resume` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:fine_tuning_jobs=pass` |
| `/images/edits` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:images_edit=pass` |
| `/images/generations` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `codex_image_generation=pass` |
| `/images/variations` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:images_variation=pass` |
| `/models` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `codex_models=pass` |
| `/models/{model}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_models_list_with_oauth=expected_blocked` |
| `/moderations` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_moderation_with_oauth=expected_blocked` |
| `/organization/admin_api_keys` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/admin_api_keys/{key_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/audit_logs` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/certificates` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/certificates/activate` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/certificates/deactivate` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/certificates/{certificate_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/costs` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/data_retention` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/groups` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/groups/{group_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/groups/{group_id}/roles` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/groups/{group_id}/roles/{role_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/groups/{group_id}/users` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/groups/{group_id}/users/{user_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/invites` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/invites/{invite_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/api_keys` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/api_keys/{api_key_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/archive` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/certificates` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/certificates/activate` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/certificates/deactivate` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/data_retention` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/groups` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/groups/{group_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/hosted_tool_permissions` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/model_permissions` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/rate_limits` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/rate_limits/{rate_limit_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/service_accounts` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/service_accounts/{service_account_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/spend_alerts` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/spend_alerts/{alert_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/users` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/projects/{project_id}/users/{user_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/roles` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/roles/{role_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/spend_alerts` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/spend_alerts/{alert_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/usage/audio_speeches` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/usage/audio_transcriptions` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/usage/code_interpreter_sessions` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/usage/completions` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/usage/embeddings` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/usage/file_search_calls` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/usage/images` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/usage/moderations` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/usage/vector_stores` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/usage/web_search_calls` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/users` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/users/{user_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/users/{user_id}/roles` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/organization/users/{user_id}/roles/{role_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/projects/{project_id}/groups/{group_id}/roles` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/projects/{project_id}/groups/{group_id}/roles/{role_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/projects/{project_id}/roles` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/projects/{project_id}/roles/{role_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/projects/{project_id}/users/{user_id}/roles` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/projects/{project_id}/users/{user_id}/roles/{role_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:organization_project_sandbox=pass` |
| `/realtime/calls/{call_id}/accept` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:realtime_call_lifecycle=pass` |
| `/realtime/calls/{call_id}/hangup` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:realtime_call_lifecycle=pass` |
| `/realtime/calls/{call_id}/refer` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:realtime_call_lifecycle=pass` |
| `/realtime/calls/{call_id}/reject` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:realtime_call_lifecycle=pass` |
| `/realtime/sessions` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:realtime_sessions_aliases=pass` |
| `/realtime/transcription_sessions` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:realtime_sessions_aliases=pass` |
| `/responses` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `codex_text_response=pass` |
| `/responses/compact` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:responses_compact=pass` |
| `/responses/input_tokens` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:responses_input_tokens_estimate=pass` |
| `/responses/{response_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_responses_with_oauth=expected_blocked` |
| `/responses/{response_id}/cancel` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_responses_with_oauth=expected_blocked` |
| `/responses/{response_id}/input_items` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_responses_with_oauth=expected_blocked` |
| `/skills` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:skills_registry=pass` |
| `/skills/{skill_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:skills_registry=pass` |
| `/skills/{skill_id}/content` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:skills_registry=pass` |
| `/skills/{skill_id}/versions` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:skills_registry=pass` |
| `/skills/{skill_id}/versions/{version}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:skills_registry=pass` |
| `/skills/{skill_id}/versions/{version}/content` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:skills_registry=pass` |
| `/threads` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:assistant_thread_run=pass; offline:thread_run_steps=pass; offline:thread_message_delete=pass` |
| `/threads/runs` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:assistant_thread_run=pass; offline:thread_run_steps=pass; offline:thread_message_delete=pass` |
| `/threads/{thread_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:assistant_thread_run=pass; offline:thread_run_steps=pass; offline:thread_message_delete=pass` |
| `/threads/{thread_id}/messages` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:assistant_thread_run=pass; offline:thread_run_steps=pass; offline:thread_message_delete=pass` |
| `/threads/{thread_id}/messages/{message_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:assistant_thread_run=pass; offline:thread_run_steps=pass; offline:thread_message_delete=pass` |
| `/threads/{thread_id}/runs` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:assistant_thread_run=pass; offline:thread_run_steps=pass; offline:thread_message_delete=pass` |
| `/threads/{thread_id}/runs/{run_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:assistant_thread_run=pass; offline:thread_run_steps=pass; offline:thread_message_delete=pass` |
| `/threads/{thread_id}/runs/{run_id}/cancel` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:assistant_thread_run=pass; offline:thread_run_steps=pass; offline:thread_message_delete=pass` |
| `/threads/{thread_id}/runs/{run_id}/steps` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:assistant_thread_run=pass; offline:thread_run_steps=pass; offline:thread_message_delete=pass` |
| `/threads/{thread_id}/runs/{run_id}/steps/{step_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:assistant_thread_run=pass; offline:thread_run_steps=pass; offline:thread_message_delete=pass` |
| `/threads/{thread_id}/runs/{run_id}/submit_tool_outputs` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:assistant_thread_run=pass; offline:thread_run_steps=pass; offline:thread_message_delete=pass` |
| `/uploads` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_upload_create_cancel_with_oauth=expected_blocked` |
| `/uploads/{upload_id}/cancel` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_upload_create_cancel_with_oauth=expected_blocked` |
| `/uploads/{upload_id}/complete` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_upload_create_cancel_with_oauth=expected_blocked` |
| `/uploads/{upload_id}/parts` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_upload_create_cancel_with_oauth=expected_blocked` |
| `/vector_stores` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_vector_stores_list_with_oauth=expected_blocked` |
| `/vector_stores/{vector_store_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_vector_stores_list_with_oauth=expected_blocked` |
| `/vector_stores/{vector_store_id}/file_batches` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_vector_stores_list_with_oauth=expected_blocked` |
| `/vector_stores/{vector_store_id}/file_batches/{batch_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_vector_stores_list_with_oauth=expected_blocked` |
| `/vector_stores/{vector_store_id}/file_batches/{batch_id}/cancel` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_vector_stores_list_with_oauth=expected_blocked` |
| `/vector_stores/{vector_store_id}/file_batches/{batch_id}/files` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_vector_stores_list_with_oauth=expected_blocked` |
| `/vector_stores/{vector_store_id}/files` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_vector_stores_list_with_oauth=expected_blocked` |
| `/vector_stores/{vector_store_id}/files/{file_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_vector_stores_list_with_oauth=expected_blocked` |
| `/vector_stores/{vector_store_id}/files/{file_id}/content` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_vector_stores_list_with_oauth=expected_blocked` |
| `/vector_stores/{vector_store_id}/search` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `official_api_vector_stores_list_with_oauth=expected_blocked` |
| `/videos` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:videos_storyboard_sandbox=pass` |
| `/videos/characters` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:videos_storyboard_sandbox=pass` |
| `/videos/characters/{character_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:videos_storyboard_sandbox=pass` |
| `/videos/edits` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:videos_storyboard_sandbox=pass` |
| `/videos/extensions` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:videos_storyboard_sandbox=pass` |
| `/videos/{video_id}` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:videos_storyboard_sandbox=pass` |
| `/videos/{video_id}/content` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:videos_storyboard_sandbox=pass` |
| `/videos/{video_id}/remix` | `local_compat_or_chatgpt_backend_bridge` | Use local bridge | `offline:videos_storyboard_sandbox=pass` |
