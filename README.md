# ADLAS: Interactive Learning and Multi-Dimensional Competency Assessment Platform

Project for Vietnam Student Olympiad in Informatics (OLP) 2026 - Open Source Software Track
Core Architecture: DX-OS Open-Core (2-Tier Architecture: Headless PaaS and Process x Intelligence Application)
Theoretical Framework: EBAF (Evidence-Based Adaptive Assessment Framework)
Software License: MIT License (Zero Proprietary Dependencies)

---

## 1. Overview

ADLAS is an educational platform designed to resolve academic integrity challenges in higher education. The system shifts from evaluating solely summative products to continuous, evidence-based assessment.

Key Highlights:
- Transparent AI Disclosure: Structured declarations of AI assistance levels.
- Adaptive Viva Defense Sandbox: Isolated evaluation environment with clipboard restrictions.
- Socratic Scaffolding: Progressive guidance preventing direct solution generation.
- Human-in-the-Loop Governance: AI generates proposed evidence; instructors maintain final approval authority via a 3-column SpeedGrader.

---

## 2. System Architecture

The project follows a Modular Monolith architecture decoupled into two tiers:
- Tier 1 (Headless PaaS): Core services running headlessly (Identity, Kong API Gateway, Multi-Schema PostgreSQL 16, MinIO S3 Storage, In-process Event Bus). Includes a dedicated Web Admin Console for system administrators.
- Tier 2 (Application Tier): Business logic implemented in Python 3.11+ FastAPI across 8 Bounded Contexts, with a React 18 Single Page Application client for instructors and students.
- AI Gateway: Dual-mode architecture supporting Google Gemini API (default development mode with zero host RAM overhead) and local Ollama inference runtime.

---

## 3. Network and Port Matrix

| Service | Port | Protocol | Description |
| :--- | :---: | :---: | :--- |
| Kong API Gateway | 8000 | HTTP | Central edge routing and reverse proxy |
| FastAPI Backend | 8080 | HTTP | Core business engine and API documentation |
| React Web Application | 5173 | HTTP | Primary application for teachers and students |
| Web Admin Console | 5174 | HTTP | System administration interface for Tier 1 |
| PostgreSQL Database | 5432 | TCP | Relational and vector storage (7 schemas) |
| MinIO Storage Console | 9001 | HTTP | Object storage management interface |

---

## 4. Quick Start (Building and Running from Source)

### Prerequisites
- Docker Engine >= 24.0 and Docker Compose >= 2.20
- Python >= 3.11
- Node.js >= 18.0 and pnpm >= 8.0

### Step 1: Clone Repository and Configure Environment
```bash
git clone <repository-url>
cd repo-chinh
cp .env.example .env
```

Note: Configure `GEMINI_API_KEY` in `.env` to enable AI capabilities with zero server memory footprint.

### Step 2: Launch Platform Services
```bash
docker compose up -d
```

### Step 3: Run Seed Data Script
```bash
python scripts/seed_data.py
```

### Step 4: Access Interfaces
- Main Application: `http://localhost:5173`
- Web Admin Console: `http://localhost:5174`
- API Documentation (Swagger): `http://localhost:8080/docs`

---

## 5. Development Standards and Governance

- Formatting: Ruff (Backend) and ESLint/Prettier (Frontend).
- Commit Convention: Conventional Commits (`feat`, `fix`, `docs`, `refactor`, `test`, `chore`).
- Documentation Style: Academic engineering standard without emojis or informal icons.
- License Compliance: Every source file contains standard copyright and license headers.
