# Global Story Index

## Overview
- **Total stories**: 36
- **Generated**: 36
- **Last updated**: 2026-05-31

---

## Stories by Intent

### 001-vton-generation-pipeline

#### Unit: 001-media-service

- [x] **001-upload-garment-photo** ✅ GENERATED — Upload Garment Photo — Must
- [x] **002-upload-own-model-photo** ✅ GENERATED — Upload Own Model Photo — Must
- [x] **003-curated-model-library** ✅ GENERATED — Browse Curated Model Library — Must

#### Unit: 002-vton-job-service

- [x] **001-submit-vton-job** ✅ GENERATED — Submit VTON Job — Must
- [x] **002-process-job-celery** ✅ GENERATED — Process Job via Celery Worker — Must
- [x] **003-poll-job-status** ✅ GENERATED — Poll Job Status — Must
- [x] **004-retry-on-failure** ✅ GENERATED — Automatic Retry on Failure — Must
- [x] **005-job-history** ✅ GENERATED — Job History — Should

#### Unit: 003-vton-pipeline-ui

- [x] **001-garment-upload-ui** ✅ GENERATED — Garment Upload Form — Must
- [x] **002-model-selection-ui** ✅ GENERATED — Model Selection UI — Must
- [x] **003-job-submission-ui** ✅ GENERATED — Job Submission Form — Must
- [x] **004-job-status-polling-ui** ✅ GENERATED — Job Status Polling UI — Must
- [x] **005-result-display-ui** ✅ GENERATED — Result Display — Must
- [x] **006-job-history-ui** ✅ GENERATED — Job History Page — Should

---

### 002-catalog-management

#### Unit: 001-catalog-service

- [x] **001-create-catalog** ✅ GENERATED — Create Named Catalog — Must
- [x] **002-add-catalog-item** ✅ GENERATED — Add Item to Catalog — Must
- [x] **003-remove-catalog-item** ✅ GENERATED — Remove Item from Catalog — Must
- [x] **004-reorder-catalog-items** ✅ GENERATED — Reorder Catalog Items — Must
- [x] **005-rename-catalog** ✅ GENERATED — Rename Catalog — Must
- [x] **006-publish-unpublish-catalog** ✅ GENERATED — Publish / Unpublish Catalog — Must
- [x] **007-delete-catalog** ✅ GENERATED — Delete Catalog — Must
- [x] **008-list-catalogs** ✅ GENERATED — List Mayorista's Catalogs — Must

#### Unit: 002-customer-portal-service

- [x] **001-register-customer** ✅ GENERATED — Register Buyer / Customer — Must
- [x] **002-buyer-portal-auth** ✅ GENERATED — Buyer Portal Authentication — Must
- [x] **003-browse-published-catalogs** ✅ GENERATED — Browse Published Catalogs — Must

#### Unit: 003-catalog-management-ui

- [x] **001-catalog-list-page** ✅ GENERATED — Catalog Dashboard (Mayorista) — Must
- [x] **002-catalog-detail-page** ✅ GENERATED — Catalog Detail & Item Management — Must
- [x] **003-catalog-publish-flow** ✅ GENERATED — Publish / Unpublish Catalog Flow — Must
- [x] **004-customer-management-page** ✅ GENERATED — Customer Management Page — Must
- [x] **005-buyer-portal-page** ✅ GENERATED — Buyer Portal Catalog Browser — Must

---

---

### 003-fashn-provider-upgrade

#### Unit: 001-fashn-postprocess

- [x] **001-hand-compositing-tuning** ✅ GENERATED — Tune Hand Compositing to Eliminate Artifacts — Must
- [x] **002-long-pants-threshold-validation** ✅ GENERATED — Validate and Tune Long-Pants Detection Thresholds — Must
- [x] **003-segmentation-free-ab-test** ✅ GENERATED — A/B Test segmentation_free for One-Pieces — Should
- [x] **004-full-resolution-model-image** ✅ GENERATED — Compare Thumbnail vs Full-Res Model Input — Could

#### Unit: 002-fashn-validation

- [x] **001-container-deployment-reliability** ✅ GENERATED — Fix Stale Container; Add Version Logging — Must
- [x] **002-multi-subject-test-suite** ✅ GENERATED — Source ≥3 Subjects; Run and Document Test Suite — Must

---

## Stories by Status

- **Planned/Generated**: 6 (003-fashn-provider-upgrade)
- **In Progress**: 0
- **Completed**: 30 (intents 001 and 002)
