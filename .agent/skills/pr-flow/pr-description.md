## Ticket

[Story 2.12: Sync Artifact Normalization and Centralized Paths]

## Description

This PR centralizes all sync-generated data (snapshots, hashes, backups) into a single `apps/backend/artifacts/` folder. It also restructures the backend services layer to follow a professional, industry-standard hierarchy (`core/`, `search/`, `sync/`), drastically improving code discoverability and separation of concerns. Finally, it streamlines local data hydration by merging all restoration scripts into a single, unified `restore-data.ts` orchestrator.

## Implementation Details

### Architecture & Service Restructuring

- Reorganized `apps/backend/src/services` into scoped domains: `core/`, `search/`, and `sync/`.
- Relocated `SyncOrchestrator` from the `api/` routes layer to `services/sync/`.
- Created `SearchOrchestratorService` to centralize all Typesense re-indexing logic (Media, Products, Taxonomy).
- Created `src/config/paths.ts` to manage all absolute paths for the new `artifacts/` directory structure.

### Artifacts & Data Hydration

- Centralized all sync outputs (Firestore JSON snapshots, Typesense JSONL backups, state hashes) into `apps/backend/artifacts/`.
- Moved local development seed data (`users.json`) into the `artifacts/snapshots/firestore/` structure.
- Refactored and consolidated multiple seed scripts (`restore-firestore`, `seed-users`, `seed-local`, etc.) into a single, robust `restore-data.ts` CLI tool.
- Integrated `scp` logic directly into the restoration script (`pnpm run data:pull` / `data:seed`) to fetch the latest "Golden Record" from the production server (`t40`) and hydrate the local emulator in one step.

### API & Endpoints

- Added a new protected admin endpoint `POST /api/admin/search/reindex` to trigger manual, entity-specific search index recovery via the `SearchOrchestratorService`.

### Maintenance

- Cleaned up legacy data directories (`firebase-data/`, `sync-data/`) and updated `.gitignore` to exclude the new transient `artifacts/` folder.

## Testing Instructions

1. Checkout this branch locally.
2. Ensure you have an active SSH connection/configuration for the `t40` production server.
3. Run the unified pull and seed command from the repository root: `pnpm run data:seed`.
4. Observe the CLI output. It should securely `scp` the latest JSON artifacts from the server into `apps/backend/artifacts/`.
5. Verify that the script successfully hydrates the local Firebase Emulators (Catalog, Inventory, Taxonomy, Media, Users) and the local Typesense instance.
6. (Optional) Test the new admin endpoint by sending a POST request to `http://localhost:6005/api/admin/search/reindex` with `{"entity": "media", "options": {"backfill": true}}` and a valid API key.

## Acceptance Criteria Met

- [x] Create `apps/backend/artifacts/` with subfolders for snapshots, state, and backups.
- [x] Implement a centralized `src/config/paths.ts` to manage all artifact locations.
- [x] Update sync services (`BackupManager`, `HashManager`, `SyncOrchestrator`) to use the new centralized paths.
- [x] Relocate existing snapshots and hashes to the new structure and clean up legacy folders.
- [x] Update `package.json` scripts and restore scripts to reflect the new artifact locations and provide a unified developer experience.
