# Router Offline Smoke Report

- Finished: `2026-06-06T13:20:38Z`
- Network: not used; Codex text and embeddings are stubbed
- Socket: not used

| Status | Test | Evidence |
|---|---|---|
| `pass` | `responses_create` | object=oauth_compat.response; route=codex_text; output_text_len=22 |
| `pass` | `responses_input_tokens_estimate` | object=response.input_tokens.estimate; route=local_input_token_estimate |
| `pass` | `responses_compact` | object=oauth_compat.response.compaction; route=local_responses_compact_plus_codex_text |
| `pass` | `audio_translations_create` | object=audio.translation; route=official_audio_transcriptions_plus_codex_translation |
| `pass` | `audio_voice_catalog` |  |
| `pass` | `realtime_sessions_aliases` |  |
| `pass` | `realtime_call_lifecycle` |  |
| `pass` | `images_edit` | object=oauth_compat.image.edit; route=codex_vision_plus_image_generation_edit |
| `pass` | `images_variation` | object=oauth_compat.image.variation; route=codex_vision_plus_image_generation_variation |
| `pass` | `containers_files` |  |
| `pass` | `chatkit_sessions_threads` |  |
| `pass` | `skills_registry` |  |
| `pass` | `conversations_items` |  |
| `pass` | `completions_create` | object=oauth_compat.completion; route=codex_text |
| `pass` | `chat_create` | object=oauth_compat.chat.completion; route=codex_text; message_len=22 |
| `pass` | `assistant_thread_run` | id=run_local_969b36ee73b042e68b5227e53c4ad013; object=thread.run; oauth_compat_route=local_assistant_thread_run_plus_codex_text |
| `pass` | `thread_run_steps` | object=list; route=local_assistant_thread_run_plus_codex_text; data_count=1; first_id=step_local_04f4c97e1bff425ca72da639c1d81e87 |
| `pass` | `thread_message_delete` | id=msg_local_2842893c432a4f7ab6c1f425d25431cf; object=thread.message.deleted; deleted=True |
| `pass` | `moderations` | id=modr-local-3079999eaf604450b70ec81ae1ab594d; route=local_heuristic_moderation |
| `pass` | `client_config_report` |  |
| `pass` | `coverage_map_report` |  |
| `pass` | `status_report` |  |
| `pass` | `template_local_classification` | matched_path=/videos/{video_id}/remix |
| `pass` | `fine_tuning_graders` |  |
| `pass` | `fine_tuning_jobs` | object=oauth_compat.fine_tuning.jobs.smoke; route=local_fine_tuning_job_store |
| `pass` | `organization_project_sandbox` | object=oauth_compat.organization_project_sandbox.smoke; route=local_organization_project_sandbox |
| `pass` | `videos_storyboard_sandbox` | object=oauth_compat.videos.storyboard.smoke; route=local_video_storyboard_sandbox |
| `pass` | `platform_fallback_disabled` | category=api_key_or_admin_key_required; fallback_can_forward=False; fallback_credential_env=OPENAI_API_KEY; fallback_credential_present=False |
| `pass` | `platform_fallback_enabled_api_key` | category=api_key_or_admin_key_required; fallback_can_forward=True; fallback_credential_env=OPENAI_API_KEY; fallback_credential_present=True |
| `pass` | `platform_fallback_enabled_admin_key` | category=api_key_or_admin_key_required; fallback_can_forward=True; fallback_credential_env=OPENAI_ADMIN_KEY; fallback_credential_present=True |
| `pass` | `platform_fallback_enabled_access_token` | category=api_key_or_admin_key_required; fallback_can_forward=True; fallback_credential_env=OPENAI_ACCESS_TOKEN; fallback_credential_present=True |
| `pass` | `platform_fallback_prefer_mode` | category=local_compat_or_chatgpt_backend_bridge; fallback_can_forward=True; fallback_credential_env=OPENAI_API_KEY; fallback_credential_present=True |
| `pass` | `vector_stores_add_text` | id=vsi-local-f93ed38fbc444646a52d2a78daba7f95; object=oauth_compat.vector_store.item; route=local_vector_store_plus_oauth_embeddings |
| `pass` | `vector_stores_search` | object=oauth_compat.vector_store.search_results; route=local_vector_store_plus_oauth_embeddings; data_count=1; first_id=vsi-local-f93ed38fbc444646a52d2a78daba7f95 |
| `pass` | `eval_runs_create` | id=evalrun-local-7af68ef51c034a27aa32c5656f692b51; object=eval.run; route=local_eval_plus_codex_text |
| `pass` | `eval_output_items_list` | object=oauth_compat.list; route=local_eval_plus_codex_text; data_count=1; first_id=evaloi-local-d2e6d2161bc444de85b58bdac22c415d |
