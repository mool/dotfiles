---
description: Create and submit a PR with Graphite after context gathering, hygiene checks, and user approval
argument-hint: "[extra instructions]"
---

Use the `graphite` skill and the Graphite CLI to create and submit a PR for the current repository.

Extra instructions from the user: $@

Follow this workflow exactly:

1. Gather context about the current repo changes.
   - Inspect git status, staged and unstaged diffs, recent commits if helpful, and any existing PR template.
   - Summarize the change set concisely.

2. Run pre-flight hygiene checks across the relevant changed files.
   Look for at least:
   - Debug statements or temporary traces
     - Examples: `console.log`, `print`, `dbg!`, `fmt.Println`, temporary logging, ad-hoc traces, breakpoint helpers
   - `TODO` and `FIXME` comments
   - Secrets that could be spilled
     - API keys, tokens, passwords, private keys, credentials, `.env` values, suspicious long random strings
   - Conflict markers
     - `<<<<<<<`, `=======`, `>>>>>>>`
   - AI-generated comments that should likely be removed

3. Report findings before making any branch, commit, or PR changes.
   Provide:
   - A concise summary of the repo changes
   - A list of hygiene issues that must be fixed
   - A list of non-blocking items, if any

4. If there are important or ambiguous issues, stop and ask whether to fix them first.
   - Do not create a branch, commit, or PR until the user answers.

5. Draft a PR title and PR description.
   - The title must use the format: `INF-# - <title>`
   - If the Linear issue ID is not clearly available from the repo context, ask the user for it before continuing.
   - Keep the PR description concise and structured with these sections:
     - Summary
     - What changed
     - Risks / rollout notes
     - Testing

6. Ask the user to validate the proposed title and description.
   - Iterate until the user explicitly approves them.
   - Do not create the branch, commit, or submit the PR before approval.

7. Once approved, create the branch and commit the changes using Graphite.
   - Use the `graphite` skill's conventions.
   - Prefer Graphite commands for branch creation and submission.
   - If the current branch is untracked or Graphite needs setup, handle that carefully and explain what you are doing.

8. Submit the PR with Graphite.
   - If needed, use `gh pr edit` to finalize the approved title and body.

9. Return both PR URLs:
   - The Graphite PR URL
   - The GitHub PR URL

Important behavior requirements:

- Be concise, but do not skip the hygiene report.
- Ask before taking irreversible or user-visible actions.
- Never modify repository files as part of this prompt. If checks fail, report the failure and ask whether to proceed with the PR as-is; do not attempt a fix.
- If the change set should obviously be split into multiple atomic PRs, say so before proceeding and propose the split.
- Do not invent testing results. Report only what you verified or what the user states.
