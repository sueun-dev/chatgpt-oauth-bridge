# OpenAI SDK Proxy Smoke Report

- Finished: `2026-05-29T23:39:02Z`
- SDK base URL: `http://127.0.0.1:64575/v1`
- Include speech: `True`
- Include images: `True`

| Status | Test | Evidence |
|---|---|---|
| `pass` | `sdk_models_list` | object=list; data_count=7; first_model=gpt-5.5 |
| `pass` | `sdk_models_retrieve` | object=model; id=gpt-5.5 |
| `pass` | `sdk_responses_create` | object=response; id=resp_oauth_710c25b95b5f460d91f4547e05295edd; output_text_len=16; output_count=1 |
| `pass` | `sdk_responses_retrieve` | object=response; id=resp_oauth_710c25b95b5f460d91f4547e05295edd; resource_status=completed; output_text_len=16 |
| `pass` | `sdk_response_input_items_list` | object=list; data_count=1; first_type=message |
| `pass` | `sdk_responses_cancel` | object=response; id=resp_oauth_710c25b95b5f460d91f4547e05295edd; resource_status=cancelled |
| `pass` | `sdk_responses_delete` | deleted_none=True |
| `pass` | `sdk_responses_stream` | event_count=8; delta_text_len=23; completed=True |
| `pass` | `sdk_chat_completions_create` | object=chat.completion; id=chatcmpl_oauth_393d7a70263f4321b00434829b0b18f1; choices_count=1; message_len=11 |
| `pass` | `sdk_chat_completions_retrieve` | object=chat.completion; id=chatcmpl_oauth_393d7a70263f4321b00434829b0b18f1; choices_count=1 |
| `pass` | `sdk_chat_completions_list` | object=list; data_count=3 |
| `pass` | `sdk_chat_completions_update` | object=chat.completion; id=chatcmpl_oauth_393d7a70263f4321b00434829b0b18f1 |
| `pass` | `sdk_chat_completion_messages` | object=list; data_count=1; first_role=assistant |
| `pass` | `sdk_chat_completions_delete` | object=chat.completion.deleted; id=chatcmpl_oauth_393d7a70263f4321b00434829b0b18f1; deleted=True |
| `pass` | `sdk_chat_completions_stream` | chunk_count=3; delta_text_len=18 |
| `pass` | `sdk_embeddings_create` | object=list; data_count=1; embedding_dims=1536 |
| `pass` | `sdk_moderations_create` | id=modr-local-ec5bb1043cc1487d9ca4aff5e623e10a; model=local-heuristic-moderation; results_count=1; flagged=False |
| `pass` | `sdk_batch_input_file_create` | object=file; id=file_00000000639871f8bed98223093b7be6; filename=compat_upload_62c3cee3d303491b9b1100858e1db967_sdk_proxy_batch_input.jsonl; bytes=132 |
| `pass` | `sdk_batches_create` | object=batch; id=batch-local-3d768f055c1c46aeae49ddddcd419f39; endpoint=/v1/moderations; input_file_id=file_00000000639871f8bed98223093b7be6; resource_status=completed; request_counts_total=1; output_file_id=file-local-eda6acedb7f9405f92f63ef220a8498b |
| `pass` | `sdk_batches_list` | object=list; data_count=11 |
| `pass` | `sdk_batches_retrieve` | object=batch; id=batch-local-3d768f055c1c46aeae49ddddcd419f39; endpoint=/v1/moderations; resource_status=completed |
| `pass` | `sdk_batches_output_file_content` | bytes=1445 |
| `pass` | `sdk_batches_output_file_delete` | id=file-local-eda6acedb7f9405f92f63ef220a8498b; object=file; deleted=True |
| `pass` | `sdk_batches_cancel_create` | object=batch; id=batch-local-376a2f56a3324461bc9d0b84355ebf22; endpoint=/v1/moderations; input_file_id=file_00000000639871f8bed98223093b7be6; resource_status=in_progress; request_counts_total=0 |
| `pass` | `sdk_batches_cancel` | object=batch; id=batch-local-376a2f56a3324461bc9d0b84355ebf22; resource_status=cancelled |
| `pass` | `sdk_batch_input_file_delete` | id=file_00000000639871f8bed98223093b7be6; object=file; deleted=True |
| `pass` | `sdk_uploads_create` | object=upload; id=upload-local-ac5acc5708974e828ce6c7014ac17f04; bytes=43; filename=sdk_proxy_upload_probe.txt; resource_status=pending |
| `pass` | `sdk_upload_parts_create` | object=upload.part; id=uploadpart-local-2583a117f3df442099fe6857cb2b0d25; upload_id=upload-local-ac5acc5708974e828ce6c7014ac17f04 |
| `pass` | `sdk_uploads_complete` | object=upload; id=upload-local-ac5acc5708974e828ce6c7014ac17f04; resource_status=completed; file_id=file_0000000032e871fd8e3f59e58cc86b53; file_object=file |
| `pass` | `sdk_uploads_completed_file_delete` | id=file_0000000032e871fd8e3f59e58cc86b53; object=file; deleted=True |
| `pass` | `sdk_uploads_cancel_create` | object=upload; id=upload-local-0949c0fc8e794991ac41ec65b80361ee; bytes=43; filename=sdk_proxy_upload_probe.txt; resource_status=pending |
| `pass` | `sdk_uploads_cancel` | object=upload; id=upload-local-0949c0fc8e794991ac41ec65b80361ee; resource_status=cancelled |
| `pass` | `sdk_evals_create` | object=eval; id=eval-local-496adba3cb094c47bc6455afb7919439; resource_name=sdk-local-eval |
| `pass` | `sdk_evals_list` | object=list; data_count=1 |
| `pass` | `sdk_evals_retrieve` | object=eval; id=eval-local-496adba3cb094c47bc6455afb7919439; resource_name=sdk-local-eval |
| `pass` | `sdk_evals_update` | object=eval; id=eval-local-496adba3cb094c47bc6455afb7919439; resource_name=sdk-local-eval-updated |
| `pass` | `sdk_eval_runs_create` | object=eval.run; id=evalrun-local-0553813762d344089db5390f87e12235; eval_id=eval-local-496adba3cb094c47bc6455afb7919439; resource_status=completed; result_counts_total=1 |
| `pass` | `sdk_eval_runs_list` | object=list; data_count=1 |
| `pass` | `sdk_eval_runs_retrieve` | object=eval.run; id=evalrun-local-0553813762d344089db5390f87e12235; eval_id=eval-local-496adba3cb094c47bc6455afb7919439; resource_status=completed |
| `pass` | `sdk_eval_output_items_list` | object=list; data_count=1; first_id=evaloi-local-59307bb50fd84ae49535a40d519b43ba |
| `pass` | `sdk_eval_output_items_retrieve` | object=eval.run.output_item; id=evaloi-local-59307bb50fd84ae49535a40d519b43ba; eval_id=eval-local-496adba3cb094c47bc6455afb7919439; run_id=evalrun-local-0553813762d344089db5390f87e12235; resource_status=pass |
| `pass` | `sdk_eval_runs_cancel` | object=eval.run; id=evalrun-local-0553813762d344089db5390f87e12235; eval_id=eval-local-496adba3cb094c47bc6455afb7919439; resource_status=canceled |
| `pass` | `sdk_eval_runs_delete` | object=eval.run.deleted; id=evalrun-local-0553813762d344089db5390f87e12235; deleted=True |
| `pass` | `sdk_evals_delete` | object=eval.deleted; id=eval-local-496adba3cb094c47bc6455afb7919439; deleted=True |
| `pass` | `sdk_files_create` | object=file; id=file_00000000398071fd82f85248532957b7; filename=compat_upload_b53bbf4d4fae4317a97c2853ea5db8ac_sdk_proxy_upload_probe.txt; bytes=43 |
| `pass` | `sdk_files_retrieve` | object=file; id=file_00000000398071fd82f85248532957b7; filename=compat_upload_b53bbf4d4fae4317a97c2853ea5db8ac_sdk_proxy_upload_probe.txt; bytes=43 |
| `pass` | `sdk_files_content` | bytes=43 |
| `pass` | `sdk_files_list` | object=list; data_count=10 |
| `pass` | `sdk_vector_stores_create` | object=vector_store; id=vs-local-bb6f271644cf4f8fb578d752dd301da5 |
| `pass` | `sdk_vector_store_files_create` | object=vector_store.file; id=file_00000000398071fd82f85248532957b7; vector_store_id=vs-local-bb6f271644cf4f8fb578d752dd301da5 |
| `pass` | `sdk_vector_store_files_list` | object=list; data_count=1 |
| `pass` | `sdk_vector_store_files_retrieve` | object=vector_store.file; id=file_00000000398071fd82f85248532957b7; vector_store_id=vs-local-bb6f271644cf4f8fb578d752dd301da5 |
| `pass` | `sdk_vector_store_files_content` | object=list; data_count=1 |
| `pass` | `sdk_vector_store_file_batches_create` | object=vector_store.file_batch; id=vsfb-local-609c2c9ed26f422e929966a0fd8e3c35; vector_store_id=vs-local-bb6f271644cf4f8fb578d752dd301da5; resource_status=completed; file_counts_total=1 |
| `pass` | `sdk_vector_store_file_batches_retrieve` | object=vector_store.file_batch; id=vsfb-local-609c2c9ed26f422e929966a0fd8e3c35; vector_store_id=vs-local-bb6f271644cf4f8fb578d752dd301da5; resource_status=completed; file_counts_total=1 |
| `pass` | `sdk_vector_store_file_batches_files` | object=list; data_count=1 |
| `pass` | `sdk_vector_store_file_batches_cancel` | object=vector_store.file_batch; id=vsfb-local-609c2c9ed26f422e929966a0fd8e3c35; vector_store_id=vs-local-bb6f271644cf4f8fb578d752dd301da5; resource_status=cancelled; file_counts_total=1 |
| `pass` | `sdk_vector_stores_list` | object=list; data_count=10 |
| `pass` | `sdk_vector_stores_retrieve` | object=vector_store; id=vs-local-bb6f271644cf4f8fb578d752dd301da5 |
| `pass` | `sdk_vector_store_files_delete` | id=file_00000000398071fd82f85248532957b7; object=vector_store.file.deleted; deleted=True |
| `pass` | `sdk_files_delete` | id=file_00000000398071fd82f85248532957b7; object=file; deleted=True |
| `pass` | `sdk_vector_stores_delete` | id=vs-local-bb6f271644cf4f8fb578d752dd301da5; object=vector_store.deleted; deleted=True |
| `pass` | `sdk_audio_transcriptions_create` | text_present=True; text_len=0 |
| `pass` | `sdk_audio_speech_create` | bytes=309621 |
| `pass` | `sdk_images_generate` | data_count=1; b64_json_present=True; url_present=False |
