# Changelog

All notable changes to the ADLAS project will be documented in this file.
The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [Unreleased]
### Added
- Integrated live status telemetry from Kong Admin API (Port 8001 /status) into GatewayAdminService.
- Implemented resilient fallback mechanism when Kong Admin API is unreachable.
- Added live telemetry badges and real-time Nginx connection details to Web Admin Console.
- Added unit test cases verifying Kong live status and resilient fallback behavior.
- Added course assignments listing API (`GET /api/v1/assessments/courses/{course_id}/assignments`) and Assignments tab in CourseDetailPage.
- Added Viva timeout sealing endpoint (`POST /api/v1/assessments/submissions/{submission_id}/viva/timeout`) and `PREPARING` background state.
- Added `04-assessment-extensions.sql` migration for `assessment.assignment_submissions.project_title`.
- Persisted Call 1 `ai_digest_summary`, `digest_type`, and `digest_metadata` in `assessment.viva_transcripts.questions_answers`, added Instructor Submission & Viva Review endpoints (`GET /assignments/{assignment_id}/submissions`, `GET /submissions/{submission_id}/review`), and implemented `InstructorReviewPanel` UI in `AssignmentDetailPage`.

### Changed
- Enhanced GatewayMetricsResponse schema with KongLiveTelemetry model and telemetry_source tag.
- Updated GatewayMonitoring page to dynamically display Live vs Fallback data sources.
- Moved Viva question generation to FastAPI BackgroundTasks with fast Gemini 503 fallback.
- Upgraded Repomix ingestion to Tree-sitter AST compression (`compress: true`) prioritizing most-active Git files and stripped boilerplate `<file_summary>`.
- Replaced regex/TF-IDF document truncation and Ollama dead code with a clean 2-Call Gemini Long-Context pipeline (`gemini-3.6-flash`, Call 1 summary -> Call 2 Viva questions) plus transparent `generation_source` tracking.

### Fixed
- Fixed shared `/app/uploads` volume, safe `.zip`/`.tar` archive extraction for Repomix, and Nginx `/api/` reverse proxy in Docker.
- Fixed `DocumentSummarizer` missing word-count keys when processing empty or scanned documents.
- Fixed frontend file upload authentication token resolution by routing through `httpRequest`.
- Fixed Viva Sandbox countdown interval stability, server `remaining_seconds` sync, and dynamic duration/question count display.

## [0.1.0-alpha] - 2026-11-21
### Added
- Initial project structure aligned with DX-OS Open-Core architecture.
- Tier 1 Headless PaaS orchestration with Kong Gateway, PostgreSQL 16, and MinIO.
- Dual-mode AI Gateway adapter supporting Google Gemini API and local Ollama.
- Core FastAPI application skeleton with 8 Bounded Contexts.
- React 18 Single Page Application skeleton separating Main App and Admin Console.
- Open source compliance files, environment template, and Makefile tooling.
