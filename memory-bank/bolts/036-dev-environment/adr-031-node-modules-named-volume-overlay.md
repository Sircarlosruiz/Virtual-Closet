---
bolt: 036-dev-environment
created: 2026-06-17T16:00:00Z
status: accepted
superseded_by: null
---

# ADR-031: Frontend node_modules Named Volume Overlay in Docker Compose

## Context

The frontend container uses a bind mount (`./frontend:/app`) for hot-reload so that host file changes are reflected inside the container in real time. However, `node_modules` lives inside `/app/node_modules`. When the bind mount is active, the host machine's `node_modules` (which may not exist, or may contain packages compiled for the host OS/architecture) overwrites the container's `/app/node_modules` (compiled for Linux/Alpine).

This causes two distinct failure modes:
1. Host has no `node_modules` (fresh clone, no `npm install` on host) → container import fails immediately
2. Host has `node_modules` compiled for macOS/Windows → native binaries (e.g., `sharp`, `esbuild`) have wrong architecture → cryptic runtime errors inside the container

Both failures are silent at compose startup and produce confusing error messages that are hard to attribute to the root cause without prior knowledge of the pattern.

## Decision

Mount a Docker named volume at `/app/node_modules` in addition to the bind mount at `/app`:

```yaml
volumes:
  - ./frontend:/app                         # bind mount (hot-reload)
  - frontend_node_modules:/app/node_modules # named volume overlay
```

Docker resolves volume mounts depth-first: the named volume at the more specific path `/app/node_modules` takes precedence over the bind mount at `/app`, effectively shadowing the host's `node_modules` directory. The named volume is populated by `npm install` during `docker build` (`Dockerfile.dev`).

## Rationale

The named volume overlay is the standard pattern for this problem in Docker Compose frontend development. It:
- Ensures container-compiled packages are always used (correct architecture)
- Requires no action from the developer (`npm install` on the host is unnecessary)
- Persists `node_modules` across container restarts (fast restarts — no reinstall needed)
- Is transparent to hot-reload (bind mount still works for source files; only `node_modules` is shadowed)

### Alternatives Considered

| Alternative | Pros | Cons | Why Rejected |
|-------------|------|------|--------------------|
| Run `npm install` on host before `docker-compose up` | Simple to understand | Requires host Node.js; architecture mismatch on Apple Silicon / Windows | Adds prerequisite; defeats the "zero local deps" goal |
| Don't bind-mount `/app`; copy source into image at build time | No architecture mismatch | No hot-reload (must rebuild image on every change) | Defeats the purpose of hot-reload |
| Use `.dockerignore` to exclude `node_modules` from build context only | No effect on bind mounts | Does not solve bind-mount overlay problem | Does not address the issue |
| Mount source at a different path (e.g., `/app/src`) | Avoids the collision | Requires Next.js config changes; non-standard | Higher complexity, breaks standard Next.js layout |

## Consequences

### Positive

- Container always uses Linux-compiled packages regardless of host OS
- Developers do not need Node.js installed on their machine
- `npm install` on host is not required
- `node_modules` survives `docker-compose restart` (named volume is persistent)
- Hot-reload works correctly — source file changes propagate via bind mount

### Negative

- If `package.json` changes (new dependency added), developer must rebuild the image (`docker-compose build frontend`) to get the new package into the named volume — a `docker-compose restart` is not enough
- Named volume must be explicitly deleted (`docker volume rm frontend_node_modules`) to force a clean install
- The overlay pattern is non-obvious to developers unfamiliar with Docker volume precedence rules

### Risks

- **Risk**: Developer adds a new npm package, restarts compose, and it's not found. **Mitigation**: Document in dev guide: "After changing `package.json`, run `docker-compose build frontend && docker-compose up frontend`".
- **Risk**: Stale `node_modules` after switching branches with different dependencies. **Mitigation**: Document: run `docker volume rm frontend_node_modules && docker-compose up` to force clean install.

## Related

- **Stories**: 003-hot-reload-frontend, 005-env-example, 007-dev-guide
- **Standards**: This pattern should be referenced in any future frontend service added to docker-compose
- **Previous ADRs**: None directly related
