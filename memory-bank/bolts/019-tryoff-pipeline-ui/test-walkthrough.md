---
stage: test
bolt: 019-tryoff-pipeline-ui
created: 2026-06-01T00:00:00Z
---

## Test Report: 003-tryoff-pipeline-ui

### Summary

- **TypeScript**: All files compile with zero errors
- **ESLint**: No new errors or warnings introduced by tryoff files
- **Manual verification**: Both pages render correctly on dev server

### Test Files

- [x] `e2e/tryoff-extraction.spec.ts` — 6 E2E tests covering upload page, file validation, garment chips, status page, and golden path (Playwright browser not available in this environment due to missing system libraries)

### Manual Verification Results

| Check | Result |
|-------|--------|
| `/tryoff/new` renders with heading "Extract Garments from Image" | Confirmed via curl |
| Dropzone with "Drag and drop an image or browse files" | Confirmed in HTML output |
| Three garment chips (Upper Garment, Lower Garment, Full Dress / Outfit) | Confirmed in HTML output |
| "Start Extraction" button present and disabled initially | Confirmed (`disabled` attribute in HTML) |
| `/tryoff/status?job_ids=test-1` renders with heading "Extraction Status" | Confirmed via curl |
| Status page shows "1 job being processed" | Confirmed via curl |
| Job cards section renders | Confirmed ("Jobs" heading present) |

### Acceptance Criteria Validation

- [ ] **Mayorista can upload image, select 2 garment types, submit, and see 2 job cards with live status** — UI implemented, requires backend API (bolt 017) for full E2E
- [ ] **Job cards update without page refresh** — React Query polling with `refetchInterval` implemented
- [ ] **Completed job card shows extracted garment thumbnail** — `JobCard` renders `<img>` when `job.output_url` present
- [ ] **Failed job card shows error message** — `JobCard` renders error text when `job.status === "failed"`
- [ ] **Non-image files rejected with "Please upload a JPEG or PNG image"** — `validateFile()` in `image-dropzone.tsx`
- [ ] **Files > 10 MB rejected with "Image must be under 10 MB"** — `validateFile()` checks `file.size > MAX_SIZE`
- [ ] **"Start Extraction" disabled when no garment type selected** — `canSubmit` requires `selectedTypes.size > 0`
- [ ] **Polling stops when all jobs reach terminal state** — `calcRefreshInterval()` returns `false` when all jobs `complete` or `failed`

### Issues Found

- E2E tests cannot run in this environment due to missing Chromium system libraries (`libnspr4.so`). Tests are written and ready to execute once `npx playwright install-deps chromium` is run with sudo access.
- Full golden path E2E requires bolt 017 (tryoff-job-service) backend endpoints to be live (`POST /api/tryoff/jobs/batch`, `GET /api/tryoff/jobs/{id}`).

### Notes

- TypeScript strict mode passes with zero errors across all new files
- ESLint passes with no new violations (only pre-existing warnings in other files)
- Pages are server-rendered and confirmed to deliver correct HTML structure
- Polling hook uses `useRef` for attempt counter to avoid setState-in-effect warnings
