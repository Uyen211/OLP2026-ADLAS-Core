# Changelog

All notable changes to the ADLAS project will be documented in this file.
The format is based on Keep a Changelog, and this project adheres to Semantic Versioning.

## [Unreleased]
### Added
- Integrated live status telemetry from Kong Admin API (Port 8001 /status) into GatewayAdminService.
- Implemented resilient fallback mechanism when Kong Admin API is unreachable.
- Added live telemetry badges and real-time Nginx connection details to Web Admin Console.
- Added unit test cases verifying Kong live status and resilient fallback behavior.

### Changed
- Enhanced GatewayMetricsResponse schema with KongLiveTelemetry model and telemetry_source tag.
- Updated GatewayMonitoring page to dynamically display Live vs Fallback data sources.

## [0.1.0-alpha] - 2026-11-21
### Added
- Initial project structure aligned with DX-OS Open-Core architecture.
- Tier 1 Headless PaaS orchestration with Kong Gateway, PostgreSQL 16, and MinIO.
- Dual-mode AI Gateway adapter supporting Google Gemini API and local Ollama.
- Core FastAPI application skeleton with 8 Bounded Contexts.
- React 18 Single Page Application skeleton separating Main App and Admin Console.
- Open source compliance files, environment template, and Makefile tooling.
