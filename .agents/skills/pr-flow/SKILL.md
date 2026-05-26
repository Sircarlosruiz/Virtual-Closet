---
name: lvz-pr-flow
description: Standardized PR-ready flow for La Voz Nicaragua. Use when the user says "create pr", "create pull request", or "run pr flow". Defaults PR target to dev and enforces local branch/commit/PR conventions.
---

# Virtual Closet PR Flow

Use this skill when code is ready for PR and the user asks to run PR flow.

## Triggers
- `create pr`
- `create pull request`
- `run pr flow`

## Project Constraints (from GEMINI.md)
- **Commands:** NEVER run terminal commands on your own. Always propose the command sequence first, then use `run_shell_command` which will trigger a user confirmation dialog.
- **Style:** No emojis/emoticons in logs, commits, or PR metadata.
- **Commits:** Clear, concise, no file paths. Use Conventional Commits with scopes.

## Branch Naming Rules
Choose branch type by work type:
- `bugfix/` for defects
- `feat/` for new behavior
- `hotfix/` for urgent fixes
- `refactor/` for structural changes

Format: `<type>/lvz[id]-[short-dashed-description]`
Example: `feat/lvz214-backend-optimizations`

## Execution Workflow

1. **Research & Inspect**
   - Identify the Story ID (e.g., `2-14`) from context or `_bmad-output/implementation-artifacts/sprint-status.yaml`.
   - Run `git status --short` to see pending changes.
   - Run `git rev-parse --abbrev-ref HEAD` to check the current branch.

2. **Propose the Plan**
   - Present a summary of the intended actions:
     - Branch name to create/use.
     - Files to be staged.
     - Commit message (e.g., `feat(backend): implement R2 upload logic`).
     - PR Title (e.g., `feat: lvz214 Backend Optimizations`) and Target Branch (`dev`).
   - **Wait for User Approval.**

3. **Prepare Branch & Commit**
   - If current branch is not compliant, create a new one: `git checkout -b <branch>`.
   - Stage files: `git add <files>`.
   - Commit: `git commit -m "<message>"`.

4. **Push & PR Generation**
   - Push: `git push -u origin HEAD`.
   - Generate PR body using `.github/pull_request_template.md`.
   - **Break down Implementation Details by Domain** (Backend, Frontend, Shared, etc.) based on the files changed.
   - Create PR: `gh pr create --base dev --title "..." --body-file "..."`.

5. **Report Result**
   - Provide the PR URL and a summary of the work performed.

## Guardrails
- Base branch is always `dev` unless explicitly told otherwise.
- Use `pnpm lint` or `pnpm build` if requested to verify before PR.
- Never include unrelated files or "just-in-case" changes.
- Do not use emojis in any git/github metadata.

