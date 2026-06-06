# Usage Scanner Coverage

- Generated: `2026-06-06T12:44:15Z`
- OK: `True`
- Checked: `64`
- Official paths: `172`
- SDK-mapped paths: `172`

## Path Coverage

- Missing paths: `0`
- Extra paths: `0`

## Representative Cases

| Status | Token | Matched Path | Category |
|---|---|---|---|
| `pass` | `client.responses.create` | `/responses` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.models.list` | `/models` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.chatkit.sessions.create` | `/chatkit/sessions` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.containers.retrieve` | `/containers/{container_id}` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.containers.files.create` | `/containers/{container_id}/files` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.conversations.create` | `/conversations` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.conversations.items.retrieve` | `/conversations/{conversation_id}/items/{item_id}` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.audio.voices.list` | `/audio/voices` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.audio.voice_consents.create` | `/audio/voice_consents` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.audio.voiceConsents.retrieve` | `/audio/voice_consents/{consent_id}` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.audio.translations.create` | `/audio/translations` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.images.edit` | `/images/edits` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.images.variations.create` | `/images/variations` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.realtime.client_secrets.create` | `/realtime/client_secrets` | `direct_official_oauth_verified` |
| `pass` | `client.realtime.sessions.create` | `/realtime/sessions` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.realtime.transcription_sessions.create` | `/realtime/transcription_sessions` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.skills.versions.content.retrieve` | `/skills/{skill_id}/versions/{version}/content` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.videos.create` | `/videos` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.videos.retrieve` | `/videos/{video_id}` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.videos.content` | `/videos/{video_id}/content` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.videos.edits.create` | `/videos/edits` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.videos.extensions.create` | `/videos/extensions` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.videos.remix` | `/videos/{video_id}/remix` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.videos.characters.list` | `/videos/characters` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.videos.characters.retrieve` | `/videos/characters/{character_id}` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.organization.projects.list` | `/organization/projects` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.organization.projects.archive` | `/organization/projects/{project_id}/archive` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.organization.projects.api_keys.delete` | `/organization/projects/{project_id}/api_keys/{api_key_id}` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.organization.admin_api_keys.list` | `/organization/admin_api_keys` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.organization.costs.list` | `/organization/costs` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.organization.usage.completions.list` | `/organization/usage/completions` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.projects.roles.retrieve` | `/projects/{project_id}/roles/{role_id}` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.projects.users.roles.list` | `/projects/{project_id}/users/{user_id}/roles` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fine_tuning.alpha.graders.run` | `/fine_tuning/alpha/graders/run` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fine_tuning.alpha.graders.validate` | `/fine_tuning/alpha/graders/validate` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fine_tuning.jobs.create` | `/fine_tuning/jobs` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fine_tuning.jobs.list` | `/fine_tuning/jobs` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fine_tuning.jobs.retrieve` | `/fine_tuning/jobs/{fine_tuning_job_id}` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fine_tuning.jobs.cancel` | `/fine_tuning/jobs/{fine_tuning_job_id}/cancel` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fine_tuning.jobs.checkpoints.list` | `/fine_tuning/jobs/{fine_tuning_job_id}/checkpoints` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fine_tuning.jobs.events.list` | `/fine_tuning/jobs/{fine_tuning_job_id}/events` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fine_tuning.jobs.pause` | `/fine_tuning/jobs/{fine_tuning_job_id}/pause` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fine_tuning.jobs.resume` | `/fine_tuning/jobs/{fine_tuning_job_id}/resume` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fine_tuning.checkpoints.permissions.list` | `/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fine_tuning.checkpoints.permissions.delete` | `/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions/{permission_id}` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fineTuning.alpha.graders.run` | `/fine_tuning/alpha/graders/run` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fineTuning.alpha.graders.validate` | `/fine_tuning/alpha/graders/validate` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fineTuning.jobs.create` | `/fine_tuning/jobs` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fineTuning.jobs.list` | `/fine_tuning/jobs` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fineTuning.jobs.retrieve` | `/fine_tuning/jobs/{fine_tuning_job_id}` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fineTuning.jobs.cancel` | `/fine_tuning/jobs/{fine_tuning_job_id}/cancel` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fineTuning.jobs.checkpoints.list` | `/fine_tuning/jobs/{fine_tuning_job_id}/checkpoints` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fineTuning.jobs.events.list` | `/fine_tuning/jobs/{fine_tuning_job_id}/events` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fineTuning.jobs.pause` | `/fine_tuning/jobs/{fine_tuning_job_id}/pause` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fineTuning.jobs.resume` | `/fine_tuning/jobs/{fine_tuning_job_id}/resume` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fineTuning.checkpoints.permissions.list` | `/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.fineTuning.checkpoints.permissions.delete` | `/fine_tuning/checkpoints/{fine_tuned_model_checkpoint}/permissions/{permission_id}` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.realtime.transcriptionSessions.create` | `/realtime/transcription_sessions` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `client.vectorStores.fileBatches.files.list` | `/vector_stores/{vector_store_id}/file_batches/{batch_id}/files` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `/v1/oauth-boundary-playbook` | `/oauth-boundary-playbook` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `/v1/vector_stores/vs_123/items` | `/vector_stores/{vector_store_id}/items` | `local_compat_or_chatgpt_backend_bridge` |

## Alias Cases

| Status | Token | Matched Path | Category |
|---|---|---|---|
| `pass` | `openai_client.chatkit.sessions.create` | `/chatkit/sessions` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `async_ai.organization.projects.list` | `/organization/projects` | `local_compat_or_chatgpt_backend_bridge` |
| `pass` | `media.videos.edits.create` | `/videos/edits` | `local_compat_or_chatgpt_backend_bridge` |
