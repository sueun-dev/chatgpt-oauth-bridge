# OpenAI SDK Proxy Smoke Report

- Finished: `2026-06-06T13:29:42Z`
- SDK base URL: `http://127.0.0.1:50868/v1`
- Include speech: `True`
- Include images: `True`

| Status | Test | Evidence |
|---|---|---|
| `pass` | `sdk_models_list` | object=list; data_count=5; first_model=gpt-5.5 |
| `pass` | `sdk_models_retrieve` | object=model; id=gpt-5.5 |
| `pass` | `sdk_assistants_create` | object=assistant; id=asst_local_855a04722ff549b6ba4c4f439843c257; resource_name=sdk-local-assistant; model=gpt-5.5 |
| `pass` | `sdk_assistants_list` | object=list; data_count=12; first_id=asst_local_02252e7f993d445996d8387ddbfdc03d |
| `pass` | `sdk_assistants_retrieve` | object=assistant; id=asst_local_855a04722ff549b6ba4c4f439843c257; resource_name=sdk-local-assistant |
| `pass` | `sdk_assistants_update` | object=assistant; id=asst_local_855a04722ff549b6ba4c4f439843c257; resource_name=sdk-local-assistant-updated |
| `pass` | `sdk_threads_create` | object=thread; id=thread_local_b83eb71afcbc4751bbf16042522b8fff |
| `pass` | `sdk_threads_retrieve` | object=thread; id=thread_local_b83eb71afcbc4751bbf16042522b8fff |
| `pass` | `sdk_threads_update` | object=thread; id=thread_local_b83eb71afcbc4751bbf16042522b8fff |
| `pass` | `sdk_thread_messages_create` | object=thread.message; id=msg_local_f9ba62b2c58546279b5844233c3abc21; role=user; thread_id=thread_local_b83eb71afcbc4751bbf16042522b8fff |
| `pass` | `sdk_thread_messages_list` | object=list; data_count=2; first_id=msg_local_6cababf1feec4b3790091e7e9eb6541f |
| `pass` | `sdk_thread_messages_retrieve` | object=thread.message; id=msg_local_f9ba62b2c58546279b5844233c3abc21; role=user |
| `pass` | `sdk_thread_messages_update` | object=thread.message; id=msg_local_f9ba62b2c58546279b5844233c3abc21 |
| `pass` | `sdk_thread_runs_create` | object=thread.run; id=run_local_92bef9ba91e14fc1a874d1aa3c850117; assistant_id=asst_local_855a04722ff549b6ba4c4f439843c257; thread_id=thread_local_b83eb71afcbc4751bbf16042522b8fff; resource_status=completed |
| `pass` | `sdk_thread_runs_list` | object=list; data_count=1; first_id=run_local_92bef9ba91e14fc1a874d1aa3c850117 |
| `pass` | `sdk_thread_runs_retrieve` | object=thread.run; id=run_local_92bef9ba91e14fc1a874d1aa3c850117; resource_status=completed |
| `pass` | `sdk_thread_runs_update` | object=thread.run; id=run_local_92bef9ba91e14fc1a874d1aa3c850117; resource_status=completed |
| `pass` | `sdk_thread_run_steps_list` | object=list; data_count=1; first_id=step_local_b8fea8abd36949f8a16aa48e67afcbd1; first_type=message_creation |
| `pass` | `sdk_thread_run_steps_retrieve` | object=thread.run.step; id=step_local_b8fea8abd36949f8a16aa48e67afcbd1; resource_status=completed; step_type=message_creation |
| `pass` | `sdk_thread_runs_cancel` | object=thread.run; id=run_local_92bef9ba91e14fc1a874d1aa3c850117; resource_status=cancelled |
| `pass` | `sdk_threads_create_and_run` | object=thread.run; id=run_local_ab86710ae2e442329bbdb151ec899092; assistant_id=asst_local_855a04722ff549b6ba4c4f439843c257; thread_id=thread_local_a8245ca778d94246ae910a4893f7a087; resource_status=completed |
| `pass` | `sdk_thread_messages_delete` | object=thread.message.deleted; id=msg_local_f9ba62b2c58546279b5844233c3abc21; deleted=True |
| `pass` | `sdk_threads_delete` | object=thread.deleted; id=thread_local_b83eb71afcbc4751bbf16042522b8fff; deleted=True |
| `pass` | `sdk_assistants_delete` | object=assistant.deleted; id=asst_local_855a04722ff549b6ba4c4f439843c257; deleted=True |
| `pass` | `sdk_responses_create` | object=response; id=resp_oauth_ed412625da54469ab41145c7844d94e7; output_text_len=16; output_count=1 |
| `pass` | `sdk_responses_retrieve` | object=response; id=resp_oauth_ed412625da54469ab41145c7844d94e7; resource_status=completed; output_text_len=16 |
| `pass` | `sdk_response_input_items_list` | object=list; data_count=1; first_type=message |
| `pass` | `sdk_responses_cancel` | object=response; id=resp_oauth_ed412625da54469ab41145c7844d94e7; resource_status=cancelled |
| `pass` | `sdk_responses_delete` | deleted_none=True |
| `pass` | `sdk_responses_stream` | event_count=8; delta_text_len=23; completed=True |
| `pass` | `sdk_responses_compact` | object=response.compaction; id=cmpct_oauth_ea64b88845af4321a334c0a08ca2b2d2; output_count=1; total_tokens=94 |
| `pass` | `sdk_completions_create` | object=text_completion; id=cmpl_oauth_d4d6107f40da4e7fba5af4ee475f17e3; choices_count=1; text_len=24 |
| `pass` | `sdk_completions_stream` | chunk_count=2; delta_text_len=31 |
| `pass` | `sdk_chat_completions_create` | object=chat.completion; id=chatcmpl_oauth_6173905b37254e81b3896049aac60a51; choices_count=1; message_len=11 |
| `pass` | `sdk_chat_completions_retrieve` | object=chat.completion; id=chatcmpl_oauth_6173905b37254e81b3896049aac60a51; choices_count=1 |
| `pass` | `sdk_chat_completions_list` | object=list; data_count=13 |
| `pass` | `sdk_chat_completions_update` | object=chat.completion; id=chatcmpl_oauth_6173905b37254e81b3896049aac60a51 |
| `pass` | `sdk_chat_completion_messages` | object=list; data_count=1; first_role=assistant |
| `pass` | `sdk_chat_completions_delete` | object=chat.completion.deleted; id=chatcmpl_oauth_6173905b37254e81b3896049aac60a51; deleted=True |
| `pass` | `sdk_chat_completions_stream` | chunk_count=3; delta_text_len=18 |
| `pass` | `sdk_embeddings_create` | object=list; data_count=1; embedding_dims=1536 |
| `pass` | `sdk_moderations_create` | id=modr-local-8527afcf4ffe4268be0ed52e3b0a5464; model=local-heuristic-moderation; results_count=1; flagged=False |
| `pass` | `sdk_batch_input_file_create` | object=file; id=file_00000000aff0722fb50b5109747cff51; filename=compat_upload_8b19ffed2c544976b3798010388313a9_sdk_proxy_batch_input.jsonl; bytes=132 |
| `pass` | `sdk_batches_create` | object=batch; id=batch-local-3d283908e77040319dd88e4ab2851283; endpoint=/v1/moderations; input_file_id=file_00000000aff0722fb50b5109747cff51; resource_status=completed; request_counts_total=1; output_file_id=file-local-17ebd59d0c854aae98d4ce9399af8f0b |
| `pass` | `sdk_batches_list` | object=list; data_count=25 |
| `pass` | `sdk_batches_retrieve` | object=batch; id=batch-local-3d283908e77040319dd88e4ab2851283; endpoint=/v1/moderations; resource_status=completed |
| `pass` | `sdk_batches_output_file_content` | bytes=1445 |
| `pass` | `sdk_batches_output_file_delete` | id=file-local-17ebd59d0c854aae98d4ce9399af8f0b; object=file; deleted=True |
| `pass` | `sdk_batches_cancel_create` | object=batch; id=batch-local-8e72e7a4b704426796cb17699e558447; endpoint=/v1/moderations; input_file_id=file_00000000aff0722fb50b5109747cff51; resource_status=in_progress; request_counts_total=0 |
| `pass` | `sdk_batches_cancel` | object=batch; id=batch-local-8e72e7a4b704426796cb17699e558447; resource_status=cancelled |
| `pass` | `sdk_batch_input_file_delete` | id=file_00000000aff0722fb50b5109747cff51; object=file; deleted=True |
| `pass` | `sdk_uploads_create` | object=upload; id=upload-local-433d3e658d6f4bb4a870a5bd109e3787; bytes=43; filename=sdk_proxy_upload_probe.txt; resource_status=pending |
| `pass` | `sdk_upload_parts_create` | object=upload.part; id=uploadpart-local-28568d26913b4143bc4def93ff3b966f; upload_id=upload-local-433d3e658d6f4bb4a870a5bd109e3787 |
| `pass` | `sdk_uploads_complete` | object=upload; id=upload-local-433d3e658d6f4bb4a870a5bd109e3787; resource_status=completed; file_id=file_00000000ecc0722fb0848532d2fc379d; file_object=file |
| `pass` | `sdk_uploads_completed_file_delete` | id=file_00000000ecc0722fb0848532d2fc379d; object=file; deleted=True |
| `pass` | `sdk_uploads_cancel_create` | object=upload; id=upload-local-bacc3f3b9e434946bc7b1573fedddc30; bytes=43; filename=sdk_proxy_upload_probe.txt; resource_status=pending |
| `pass` | `sdk_uploads_cancel` | object=upload; id=upload-local-bacc3f3b9e434946bc7b1573fedddc30; resource_status=cancelled |
| `pass` | `sdk_evals_create` | object=eval; id=eval-local-893818825ed94ec78970957611300e94; resource_name=sdk-local-eval |
| `pass` | `sdk_evals_list` | object=list; data_count=18 |
| `pass` | `sdk_evals_retrieve` | object=eval; id=eval-local-893818825ed94ec78970957611300e94; resource_name=sdk-local-eval |
| `pass` | `sdk_evals_update` | object=eval; id=eval-local-893818825ed94ec78970957611300e94; resource_name=sdk-local-eval-updated |
| `pass` | `sdk_eval_runs_create` | object=eval.run; id=evalrun-local-2f5a1667ca434b45aa4b590d570909d6; eval_id=eval-local-893818825ed94ec78970957611300e94; resource_status=completed; result_counts_total=1 |
| `pass` | `sdk_eval_runs_list` | object=list; data_count=1 |
| `pass` | `sdk_eval_runs_retrieve` | object=eval.run; id=evalrun-local-2f5a1667ca434b45aa4b590d570909d6; eval_id=eval-local-893818825ed94ec78970957611300e94; resource_status=completed |
| `pass` | `sdk_eval_output_items_list` | object=list; data_count=1; first_id=evaloi-local-121dd36f5ea145d0bf4194f0010329d2 |
| `pass` | `sdk_eval_output_items_retrieve` | object=eval.run.output_item; id=evaloi-local-121dd36f5ea145d0bf4194f0010329d2; eval_id=eval-local-893818825ed94ec78970957611300e94; run_id=evalrun-local-2f5a1667ca434b45aa4b590d570909d6; resource_status=pass |
| `pass` | `sdk_eval_runs_cancel` | object=eval.run; id=evalrun-local-2f5a1667ca434b45aa4b590d570909d6; eval_id=eval-local-893818825ed94ec78970957611300e94; resource_status=canceled |
| `pass` | `sdk_eval_runs_delete` | object=eval.run.deleted; id=evalrun-local-2f5a1667ca434b45aa4b590d570909d6; deleted=True |
| `pass` | `sdk_evals_delete` | object=eval.deleted; id=eval-local-893818825ed94ec78970957611300e94; deleted=True |
| `pass` | `sdk_files_create` | object=file; id=file_0000000066a071f58c74f921f324c64a; filename=compat_upload_9977672bb1304212ad9ec4490c3983cc_sdk_proxy_upload_probe.txt; bytes=43 |
| `pass` | `sdk_files_retrieve` | object=file; id=file_0000000066a071f58c74f921f324c64a; filename=compat_upload_9977672bb1304212ad9ec4490c3983cc_sdk_proxy_upload_probe.txt; bytes=43 |
| `pass` | `sdk_files_content` | bytes=43 |
| `pass` | `sdk_files_list` | object=list; data_count=1 |
| `pass` | `sdk_vector_stores_create` | object=vector_store; id=vs-local-0b4d1826704c4692802674463512593d |
| `pass` | `sdk_vector_store_files_create` | object=vector_store.file; id=file_0000000066a071f58c74f921f324c64a; vector_store_id=vs-local-0b4d1826704c4692802674463512593d |
| `pass` | `sdk_vector_store_files_list` | object=list; data_count=1 |
| `pass` | `sdk_vector_store_files_retrieve` | object=vector_store.file; id=file_0000000066a071f58c74f921f324c64a; vector_store_id=vs-local-0b4d1826704c4692802674463512593d |
| `pass` | `sdk_vector_store_files_content` | object=list; data_count=1 |
| `pass` | `sdk_vector_store_file_batches_create` | object=vector_store.file_batch; id=vsfb-local-d884bbd23b55406f86f5fde43bc3bb31; vector_store_id=vs-local-0b4d1826704c4692802674463512593d; resource_status=completed; file_counts_total=1 |
| `pass` | `sdk_vector_store_file_batches_retrieve` | object=vector_store.file_batch; id=vsfb-local-d884bbd23b55406f86f5fde43bc3bb31; vector_store_id=vs-local-0b4d1826704c4692802674463512593d; resource_status=completed; file_counts_total=1 |
| `pass` | `sdk_vector_store_file_batches_files` | object=list; data_count=1 |
| `pass` | `sdk_vector_store_file_batches_cancel` | object=vector_store.file_batch; id=vsfb-local-d884bbd23b55406f86f5fde43bc3bb31; vector_store_id=vs-local-0b4d1826704c4692802674463512593d; resource_status=cancelled; file_counts_total=1 |
| `pass` | `sdk_vector_stores_list` | object=list; data_count=12 |
| `pass` | `sdk_vector_stores_retrieve` | object=vector_store; id=vs-local-0b4d1826704c4692802674463512593d |
| `pass` | `sdk_vector_store_files_delete` | id=file_0000000066a071f58c74f921f324c64a; object=vector_store.file.deleted; deleted=True |
| `pass` | `sdk_files_delete` | id=file_0000000066a071f58c74f921f324c64a; object=file; deleted=True |
| `pass` | `sdk_vector_stores_delete` | id=vs-local-0b4d1826704c4692802674463512593d; object=vector_store.deleted; deleted=True |
| `pass` | `sdk_audio_transcriptions_create` | text_present=True; text_len=0 |
| `pass` | `sdk_audio_speech_create` | bytes=33600 |
| `pass` | `sdk_images_generate` | data_count=1; b64_json_present=True; url_present=False |
