# Codex Apps MCP Tools Inventory

- Generated: `2026-05-29T21:56:36Z`
- HTTP status: `200`
- Tools listed: `111`
- Prefix counts: `{'github': 90, 'gmail': 21}`
- Class counts: `{'mutation-capable': 66, 'read-like': 45}`
- Source route: `POST https://chatgpt.com/backend-api/wham/apps` with `tools/list`
- This is metadata only. Personal-data or write-capable tools were not called.

| Heuristic class | Tool | Description prefix |
|---|---|---|
| `mutation-capable` | `github_add_comment_to_issue` | Create a top-level PR Conversation comment (Issue comment). |
| `mutation-capable` | `github_add_issue_assignees` | Add assignees to an issue or pull request. Returns a normalized issue snapshot after the mutation. Docs: https://docs.github.com/en/rest/issues/assignees?apiVersion=2022-11-28#add-assignees-to-an-issue |
| `mutation-capable` | `github_add_issue_labels` | Add labels to an issue or pull request. Returns a normalized issue snapshot after the mutation. Docs: https://docs.github.com/en/rest/issues/labels?apiVersion=2022-11-28#add-labels-to-an-issue |
| `mutation-capable` | `github_add_reaction_to_issue_comment` | Add a reaction to an issue comment. |
| `mutation-capable` | `github_add_reaction_to_pr` | Add a reaction to a GitHub pull request. |
| `mutation-capable` | `github_add_reaction_to_pr_review_comment` | Add a reaction to a pull request review comment. |
| `mutation-capable` | `github_add_review_to_pr` | Add a review to a GitHub pull request. review is required for REQUEST_CHANGES and COMMENT events. |
| `read-like` | `github_check_repo_initialized` | Check if a GitHub repository has been set up. |
| `read-like` | `github_compare_commits` | Compare two commits/refs and return per-file stats plus compare metadata. This is a thin wrapper around `GithubPlugin.compare_commits` to provide a stable, compact response shape to connector consumers. |
| `mutation-capable` | `github_convert_pull_request_to_draft` | Convert an open pull request back to draft state. Returns the connector's normalized PR snapshot after the transition. Docs: https://docs.github.com/en/graphql/reference/mutations#convertpullrequesttodraft |
| `mutation-capable` | `github_create_blob` | Create a blob in the repository and return its SHA. |
| `mutation-capable` | `github_create_branch` | Create a new branch in the given repository from base_branch. |
| `mutation-capable` | `github_create_commit` | Create a commit pointing to tree_sha with parent parent_sha. |
| `mutation-capable` | `github_create_file` | Create a UTF-8 text file through GitHub's contents API. Returns only the resulting commit SHA, not GitHub's full content/commit payload. Docs: https://docs.github.com/en/rest/repos/contents?apiVersion=2022-11-28#create-o |
| `mutation-capable` | `github_create_issue` | Create a GitHub issue. Returns a normalized issue snapshot, not GitHub's raw REST payload. Docs: https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#create-an-issue |
| `mutation-capable` | `github_create_pull_request` | Open a pull request in the repository. Returns the connector's normalized PR snapshot, not the full REST response payload. Docs: https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#create-a-pull-request |
| `mutation-capable` | `github_create_tree` | Create a tree object in the repository from the given elements. |
| `mutation-capable` | `github_delete_file` | Delete a file through GitHub's contents API. Returns only the resulting commit SHA. Docs: https://docs.github.com/en/rest/repos/contents?apiVersion=2022-11-28#delete-a-file |
| `mutation-capable` | `github_dismiss_pull_request_review` | Dismiss a submitted pull request review. Returns the normalized review snapshot after dismissal. Docs: https://docs.github.com/en/graphql/reference/mutations#dismisspullrequestreview |
| `read-like` | `github_download_user_content` | Download a GitHub private user image attachment URL. Use this only for private-user-images.githubusercontent.com URLs, such as GitHub issue or pull request image uploads. Use fetch or fetch_file for repository files. |
| `mutation-capable` | `github_download_workflow_artifact` | Download a GitHub Actions workflow artifact ZIP archive. GitHub serves this endpoint through a temporary redirect; the underlying client follows that redirect before returning a reusable file reference for the ZIP bytes. |
| `mutation-capable` | `github_enable_auto_merge` | Enable auto-merge for a pull request. This wrapper infers the merge method from repository settings and returns only `success`. Docs: https://docs.github.com/en/graphql/reference/mutations#enablepullrequestautomerge |
| `read-like` | `github_fetch` | Fetch a UTF-8 text file from GitHub by URL. Use a file URL such as ``https://github.com/owner/repo/blob/branch/path/to/file.py``. ``raw.githubusercontent.com`` file URLs and ``api.github.com/repos/.../contents/...`` URLs |
| `read-like` | `github_fetch_blob` | Fetch blob content by SHA from the given repository. |
| `read-like` | `github_fetch_commit` | Fetch a commit with its metadata, diff, and canonical URL. |
| `read-like` | `github_fetch_commit_workflow_runs` | Fetch GitHub Actions workflow runs associated with a commit SHA. This wrapper currently filters to pull-request-triggered runs and returns the first page only. Docs: https://docs.github.com/en/rest/actions/workflow-runs? |
| `read-like` | `github_fetch_file` | Fetch file content by repository path, using the default branch when ref is omitted. |
| `read-like` | `github_fetch_issue` | Fetch GitHub issue. |
| `read-like` | `github_fetch_issue_comments` | Fetch comments for a GitHub issue across all pages. |
| `read-like` | `github_fetch_pr` | Fetch a pull request with its diff, metadata, and optionally comments. |
| `mutation-capable` | `github_fetch_pr_comments` | Fetch a merged PR discussion timeline. The returned list combines issue comments, inline review comments, and review submissions into one normalized array. Docs: https://docs.github.com/en/rest/issues/comments?apiVersion |
| `read-like` | `github_fetch_pr_file_patch` | Fetch a single-file patch from a PR, searching across all file-list pages. |
| `read-like` | `github_fetch_pr_patch` | Fetch the patch for a GitHub pull request across all changed-file pages. |
| `read-like` | `github_fetch_workflow_job_logs` | Fetch decoded logs for a GitHub Actions workflow job. GitHub serves this endpoint through a temporary redirect; the underlying client follows that redirect before decoding the bytes. Docs: https://docs.github.com/en/rest |
| `read-like` | `github_fetch_workflow_job_steps` | Fetch steps for a GitHub Actions workflow job. Returns only step summaries, not the full job payload. Docs: https://docs.github.com/en/rest/actions/workflow-jobs?apiVersion=2022-11-28#get-a-job-for-a-workflow-run |
| `read-like` | `github_fetch_workflow_run_artifacts` | Fetch artifacts for a GitHub Actions workflow run. This wrapper returns the first page only. Docs: https://docs.github.com/en/rest/actions/artifacts?apiVersion=2022-11-28#list-workflow-run-artifacts |
| `read-like` | `github_fetch_workflow_run_jobs` | Fetch jobs for a GitHub Actions workflow run. This wrapper returns the latest attempt's jobs from the first page only. Docs: https://docs.github.com/en/rest/actions/workflow-jobs?apiVersion=2022-11-28#list-jobs-for-a-wor |
| `read-like` | `github_get_commit_combined_status` | Fetch the combined CI status and individual status checks for a commit. |
| `read-like` | `github_get_issue_comment_reactions` | Fetch reactions for an issue comment. |
| `read-like` | `github_get_pr_diff` | Fetch just the diff or patch text for a pull request. |
| `read-like` | `github_get_pr_info` | Get metadata (title, description, refs, and status) for a pull request. This action does *not* include the actual code changes. If you need the diff or per-file patches, call `fetch_pr_patch` instead (or use `get_users_r |
| `read-like` | `github_get_pr_reactions` | Fetch reactions for a GitHub pull request. |
| `read-like` | `github_get_pr_review_comment_reactions` | Fetch reactions for a pull request review comment. |
| `read-like` | `github_get_profile` | Retrieve the GitHub profile for the authenticated user. |
| `read-like` | `github_get_repo` | Retrieve metadata for a GitHub repository. Provide exactly one repository locator: - `repository_full_name`: `owner/name`, such as `openai/openai`. Maps to GitHub REST `owner` and `repo` path parameters. - `repository_id |
| `read-like` | `github_get_repo_collaborator_permission` | Return the collaborator permission level for a user on a repository. |
| `read-like` | `github_get_user_login` | Return the GitHub login for the authenticated user. |
| `read-like` | `github_get_users_recent_prs_in_repo` | List the user's recent GitHub pull requests in a repository. `limit` is the final number of PRs returned. The connector paginates the underlying GitHub search endpoint to satisfy larger limits. |
| `mutation-capable` | `github_label_pr` | Label a pull request. |
| `mutation-capable` | `github_list_installations` | List all organizations the authenticated user has installed this GitHub App on. |
| `mutation-capable` | `github_list_installed_accounts` | List all accounts that the user has installed our GitHub app on. |
| `read-like` | `github_list_pr_changed_filenames` | List changed filenames for a PR across all paginated file-list pages. |
| `mutation-capable` | `github_list_pull_request_review_threads` | List inline review threads on a pull request, including resolved state. Returns GraphQL review thread nodes, including comment bodies and resolution metadata. Docs: https://docs.github.com/en/graphql/reference/objects#pu |
| `mutation-capable` | `github_list_pull_request_reviews` | List review submissions on a pull request. Returns GraphQL review nodes normalized into the connector's review model. Docs: https://docs.github.com/en/graphql/reference/objects#pullrequestreview |
| `read-like` | `github_list_recent_issues` | Return the most recent GitHub issues the user can access. `top_k` is the final result limit. The connector transparently paginates GitHub's issues API until that limit is reached or no more pages exist. |
| `read-like` | `github_list_repositories` | List repositories accessible to the authenticated user. |
| `read-like` | `github_list_repositories_by_affiliation` | List repositories accessible to the authenticated user filtered by affiliation. |
| `mutation-capable` | `github_list_repositories_by_installation` | List repositories accessible to the authenticated user. |
| `read-like` | `github_list_user_org_memberships` | List the authenticated user's organization memberships. |
| `read-like` | `github_list_user_orgs` | List organizations the authenticated user is a member of. |
| `mutation-capable` | `github_lock_issue_conversation` | Lock an issue or pull request conversation. Allowed `lock_reason` values are `off-topic`, `too heated`, `resolved`, and `spam`. Docs: https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#lock-an-issue |
| `mutation-capable` | `github_mark_pull_request_ready_for_review` | Mark a draft pull request as ready for review. Returns the connector's normalized PR snapshot after the transition. Docs: https://docs.github.com/en/graphql/reference/mutations#markpullrequestreadyforreview |
| `mutation-capable` | `github_merge_pull_request` | Merge a pull request immediately. Returns GitHub's merge result payload (`sha`, `merged`, `message`). Docs: https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#merge-a-pull-request |
| `mutation-capable` | `github_remove_issue_assignees` | Remove assignees from an issue or pull request. Returns a normalized issue snapshot after the mutation. Docs: https://docs.github.com/en/rest/issues/assignees?apiVersion=2022-11-28#remove-assignees-from-an-issue |
| `mutation-capable` | `github_remove_issue_label` | Remove one label from an issue or pull request. Returns a normalized issue snapshot after the mutation. Docs: https://docs.github.com/en/rest/issues/labels?apiVersion=2022-11-28#remove-a-label-from-an-issue |
| `mutation-capable` | `github_remove_pull_request_reviewers` | Remove individual or team reviewer requests from a pull request. Returns the connector's normalized PR snapshot after the mutation. Docs: https://docs.github.com/en/rest/pulls/review-requests?apiVersion=2022-11-28#remove |
| `mutation-capable` | `github_remove_reaction_from_issue_comment` | Remove a reaction from an issue comment. |
| `mutation-capable` | `github_remove_reaction_from_pr` | Remove a reaction from a GitHub pull request. |
| `mutation-capable` | `github_remove_reaction_from_pr_review_comment` | Remove a reaction from a pull request review comment. |
| `mutation-capable` | `github_reply_to_review_comment` | Reply to an inline review comment on a PR (Files changed thread). comment_id must be the ID of the thread’s top-level inline review comment (replies-to-replies are not supported by the API) |
| `mutation-capable` | `github_request_pull_request_reviewers` | Request individual or team reviewers on a pull request. Returns the connector's normalized PR snapshot after the review request mutation. Docs: https://docs.github.com/en/rest/pulls/review-requests?apiVersion=2022-11-28# |
| `mutation-capable` | `github_rerun_failed_workflow_run_jobs` | Re-run all failed jobs in a GitHub Actions workflow run. Use this to retry only the failed jobs from a workflow run, instead of starting a full new attempt for successful jobs too. The linked GitHub app or token must hav |
| `mutation-capable` | `github_rerun_workflow_job` | Re-run one GitHub Actions workflow job. Use this when a specific failed or cancelled job should be retried without re-running every failed job in the workflow run. The linked GitHub app or token must have GitHub Actions  |
| `mutation-capable` | `github_resolve_review_thread` | Resolve an inline pull request review thread. Docs: https://docs.github.com/en/graphql/reference/mutations#resolvereviewthread |
| `read-like` | `github_search` | Search files within a specific GitHub repository. Provide a plain string query, avoid GitHub query flags such as ``is:pr``. Include keywords that match file names, functions, or error messages. ``repository_name`` or ``o |
| `read-like` | `github_search_branches` | Search GitHub branches within a repository. |
| `read-like` | `github_search_commits` | Search GitHub commits across one or more repositories. |
| `mutation-capable` | `github_search_installed_repositories_streaming` | Search for a repository (not a file) by name or description. To search for a file, use `search`. |
| `mutation-capable` | `github_search_installed_repositories_v2` | Search repositories within the user's installations using GitHub search. |
| `read-like` | `github_search_issues` | Search GitHub issues. |
| `read-like` | `github_search_prs` | Search GitHub pull requests. |
| `read-like` | `github_search_repositories` | Search for a repository (not a file) by name or description. To search for a file, use `search`. |
| `mutation-capable` | `github_unlock_issue_conversation` | Unlock an issue or pull request conversation. Docs: https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#unlock-an-issue |
| `mutation-capable` | `github_unresolve_review_thread` | Mark an inline pull request review thread as unresolved. Docs: https://docs.github.com/en/graphql/reference/mutations#unresolvereviewthread |
| `mutation-capable` | `github_update_file` | Replace a UTF-8 text file through GitHub's contents API. Returns only the resulting commit SHA. Do not run update/delete writes for the same path in parallel. Docs: https://docs.github.com/en/rest/repos/contents?apiVersi |
| `mutation-capable` | `github_update_issue` | Update a GitHub issue, including title/body, state, labels, assignees, or milestone. Returns a normalized issue snapshot after the patch. Docs: https://docs.github.com/en/rest/issues/issues?apiVersion=2022-11-28#update-a |
| `mutation-capable` | `github_update_issue_comment` | Update a top-level PR Conversation comment (Issue comment). |
| `mutation-capable` | `github_update_pull_request` | Update PR metadata, base branch, or open/closed state. Returns the connector's normalized PR snapshot. Docs: https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#update-a-pull-request |
| `mutation-capable` | `github_update_ref` | Move branch ref to the given commit SHA. |
| `mutation-capable` | `github_update_review_comment` | Update an inline review comment (or a reply) on a PR. |
| `mutation-capable` | `gmail_apply_labels_to_emails` | Apply labels to Gmail messages using label names rather than Gmail label IDs. This is the preferred labeling action for models because it avoids a separate label-id lookup step. |
| `mutation-capable` | `gmail_archive_emails` | Archive one or more existing Gmail messages by removing Gmail's INBOX label. The messages remain in Gmail and can still be found later. |
| `mutation-capable` | `gmail_batch_modify_email` | Add or remove Gmail labels on a batch of individual messages. This modifies messages, not whole threads. To label by subject, sender, or search query, search first or use bulk_label_matching_emails/apply_labels_to_emails |
| `mutation-capable` | `gmail_batch_read_email` | Read multiple Gmail messages in a single call. Each successful result includes the message body plus metadata such as sender/recipient fields, subject, snippet, labels, timestamp, and attachment metadata. |
| `mutation-capable` | `gmail_batch_read_email_threads` | Fetch multiple Gmail conversation threads in one call. Pass message ids by default, or pass id_type='thread' when the provided ids are thread ids. Do not mix message IDs and thread IDs in one call. Responses are deduplic |
| `mutation-capable` | `gmail_bulk_label_matching_emails` | Apply a label to every Gmail message matching a Gmail search query. This action performs the search and label batching server-side, so it is suitable for very large backfills without sending message IDs through the model |
| `mutation-capable` | `gmail_create_draft` | Create a Gmail draft without sending it. Use this when the user wants to review or manually send the message later in Gmail. |
| `mutation-capable` | `gmail_create_label` | Create a Gmail label. If the label already exists, the existing label is returned instead of creating a duplicate. |
| `mutation-capable` | `gmail_delete_emails` | Move one or more existing Gmail messages to Trash. This matches Gmail's delete behavior and does not permanently delete the messages. |
| `mutation-capable` | `gmail_forward_emails` | Forward one or more existing Gmail messages. Each source message is sent as a separate forwarded email, with the original message inlined below any optional note in the forwarded body and the original attachments preserv |
| `read-like` | `gmail_get_profile` | Return the current Gmail user's profile information. |
| `read-like` | `gmail_list_drafts` | List Gmail drafts with summarized metadata so they can be reviewed or selected. |
| `mutation-capable` | `gmail_list_labels` | List Gmail labels with per-label counts. Use this for questions like how many emails are in the inbox or unread, because Gmail exposes those totals directly on labels without paging through messages. For search label fil |
| `read-like` | `gmail_read_attachment` | Read one attachment from a Gmail message. First read/search the parent message and select an entry from its attachments or inline_images. Pass the parent message id as message_id. Prefer the entry's non-null attachment_i |
| `read-like` | `gmail_read_email` | Fetch a single Gmail message including its body. |
| `read-like` | `gmail_read_email_thread` | Fetch an entire Gmail conversation thread. Pass a message id by default, or pass id_type='thread' when you already have a thread id. Do not pass placeholder values, Gmail URLs, subjects, or email addresses. If max_messag |
| `mutation-capable` | `gmail_search_email_ids` | Retrieve Gmail message IDs that match a search. Put Gmail search operators in query, not label_ids. Prefer list_labels for label counts. |
| `mutation-capable` | `gmail_search_emails` | Search Gmail for emails matching a query or exact label IDs. Put all Gmail search operators in query, including after:, before:, from:, to:, subject:, has:attachment, -in:spam, -in:trash, -category:promotions, and label: |
| `mutation-capable` | `gmail_send_draft` | Send an existing Gmail draft as currently stored. Use this after the user has reviewed the draft or after you update it with update_draft. |
| `mutation-capable` | `gmail_send_email` | Send an email from the authenticated Gmail account. |
| `mutation-capable` | `gmail_update_draft` | Update an existing Gmail draft in place. Omitted fields preserve the current draft content; pass an empty string only when the user explicitly wants to clear that field. Drafts with attachments are not editable through t |
