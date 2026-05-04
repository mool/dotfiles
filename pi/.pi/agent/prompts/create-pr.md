---
description: Open a pull request in the browser.
---

Create a pull request using the `gh` GitHub CLI tool from the current branch.

It has to have a title and description of the changes introduced by this
branch. If the repo has a pull request template, use it to fill the
description.

Before creating the pull request, ensure that the branch is pushed to the remote
repository and validate that the title and description are approved by the user.

---

description: Create and submit a GitHub PR after context gathering, hygiene checks, and user approval
argument-hint: "[extra instructions]"
---

Use git and the GitHub CLI to create and submit a PR for the current repository.

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
   - Keep the PR description concise and structured with these sections:
     - Summary
     - What changed
     - Risks / rollout notes
     - Testing

6. Ask the user to validate the proposed title and description.
   - Iterate until the user explicitly approves them.
   - Do not create the branch, commit, or submit the PR before approval.

7. Once approved, create the branch and commit the changes using git (if needed).

8. Push to remote and create a draft PR using the approved title and description.

9. Return both PR URLs:
   - The Graphite PR URL
   - The GitHub PR URL

Important behavior requirements:

- Be concise, but do not skip the hygiene report.
- Ask before taking irreversible or user-visible actions.
- Never modify repository files as part of this prompt. If checks fail, report the failure and ask whether to proceed with the PR as-is; do not attempt a fix.
- Do not invent testing results. Report only what you verified or what the user states.
