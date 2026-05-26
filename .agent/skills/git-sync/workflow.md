# Git Sync Workflow

## Objectives
- Maintain a clean, atomic, and descriptive commit history.
- Ensure all relevant changes are staged before committing.
- Follow the **Conventional Commits** standard (e.g., `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `test:`, `build:`, `ci:`, `chore:`, `revert:`).

## Steps

### 1. Research & Analysis
- Run `git status` to see the current state of the workspace.
- Run `git diff HEAD` (for all changes) or `git diff --staged` (if already staged) to understand the scope of changes.
- Run `git log -n 3 --oneline` to match the project's commit message style.

### 2. Strategy
- Group related changes into logical, atomic commits.
- Identify if changes should be split into multiple commits for better history readability.

### 3. Execution (Commit Phase)
- **Stage**: Use `git add <files>` for the specific group of changes.
- **Message**: Draft a clear, concise commit message.
- Type: `<type>(<scope>): <short description>`
- Why: (Optional) A brief explanation if the "What" is not obvious.
- **Commit**: Run `git commit -m "<message>"`.

### 4. Validation & Push
- Run `git status` to confirm everything is committed.
- Run `git push` to sync with the remote repository.

## Project Style Notes
- Commits are generally lowercase for the short description.
- Use Spanish for UI/UX-specific notes if the project is primarily in Spanish, but keep commit prefixes in English (Conventional Commits).
- Never use emojis in commit messages.
- Always include the scope (e.g., `(cms)`, `(sync)`, `(shared)`) when appropriate.
