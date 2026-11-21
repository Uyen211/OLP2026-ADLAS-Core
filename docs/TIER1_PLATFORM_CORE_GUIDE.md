# Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
# SPDX-License-Identifier: MIT

# TIER 1 PLATFORM CORE INTEGRATION & HANDOVER GUIDE
## ADLAS - Adaptive Dynamic Learning & Assessment System
### Author: Member 1 (Platform Core & Lead Systems Architect)

---

## 1. Overview of Tier-1 Headless PaaS Architecture

Tier 1 provides the foundational open-source backend and administrative infrastructure for the ADLAS platform:
1. **Multi-Schema PostgreSQL 16 (Supabase Cloud / Self-Hosted):**
   - 8 isolated schemas: `identity`, `system`, `course`, `learning`, `assessment`, `examination`, `gradebook`, `analytics`.
   - Native `pgvector` extension supporting Hierarchical Navigable Small World (HNSW) vector indexing ($m=16, ef\_construction=64$).
2. **Edge API Gateway (Kong Gateway Declarative Mode):**
   - Central ingress routing with sub-5ms proxy latency.
   - Dynamic rate limiting with exam room bandwidth prioritization.
   - Hardware exam room CIDR subnet isolation firewall.
3. **Storage Engine & Quotas (Supabase Storage / MinIO S3):**
   - 3 partitioned buckets: `course-materials`, `student-submissions`, `viva-recordings`.
   - Global file size quotas enforced in real time with automated orphaned temp cleanup.
4. **Asynchronous Event Engine (Transactional Outbox & DLQ):**
   - In-process Event Bus using asyncio queues.
   - Transactional Outbox pattern guaranteeing Zero Message Loss (`system.outbox_events`).
   - Dead-Letter Queue (`system.dead_letter_queue`) with 3-step Exponential Backoff and manual recovery.
5. **Security & Auditability:**
   - Role-Based Access Control (RBAC) with instantaneous session revocation (< 50ms) via token blacklisting.
   - Append-only immutable administrative audit log (`system.system_audit_logs`).
6. **Web Admin Console:**
   - Single Page Application built on React 18, Vite, TypeScript, and Tailwind CSS.
   - Five administrative consoles: Identity, Gateway, Storage, Task Queue, and Health.

---

## 2. Integration Guide for Member 2 (Learning Materials & Socratic AI)

### 2.1. Vector Search with pgvector HNSW
* **Table:** `learning.document_chunks`
* **Column:** `embedding vector(1536)` (or 768 depending on model).
* **Index:** `idx_document_chunks_embedding_hnsw` using `vector_cosine_ops`.
* **Query Pattern (Async SQLAlchemy):**
  ```python
  from sqlalchemy import text

  query = text("""
      SELECT id, material_id, content, 1 - (embedding <=> :query_vec) AS similarity
      FROM learning.document_chunks
      WHERE material_id = :mat_id
      ORDER BY embedding <=> :query_vec
      LIMIT 5;
  """)
  result = await db.execute(query, {"query_vec": str(query_vector), "mat_id": material_id})
  ```
* **Performance Guarantee (Rule BR-SYS-06):** Sub-15ms similarity search over 10,000 document chunks.

### 2.2. Respecting Storage Upload Quotas (Rule BR-STORAGE-02)
Before storing lecture files in the `course-materials` bucket, verify that file sizes comply with global system limits:
* **Slide/PDF Limit:** Enforced dynamically via `/api/v1/system/storage/quotas` (`max_slide_mb`, default 50MB, allowed up to 100MB).
* **Video Limit:** `max_video_mb` (default 500MB, allowed up to 1000MB).

### 2.3. Publishing Events to Transactional Outbox
When a lesson document is chunked or a Socratic session completes, insert an event into `system.outbox_events` within the same database transaction:
```python
outbox = OutboxEvent(
    event_type="LESSON_CHUNKED",
    aggregate_type="LEARNING_MATERIAL",
    aggregate_id=material_id,
    payload={"chunk_count": len(chunks), "tokens": total_tokens},
    status="PENDING"
)
db.add(outbox)
await db.commit()
```

---

## 3. Integration Guide for Member 3 (Examination, SpeedGrader & Gradebook)

### 3.1. Authentication & Bearer Token Verification
* Every incoming request from frontend applications must include the Bearer JWT header:
  `Authorization: Bearer <jwt_token>`
* Use `app.core.security.decode_access_token(token)` to extract `sub` (User UUID) and verify that the token has not been blacklisted via `is_token_blacklisted(token)`.

### 3.2. Exam Room Autosave & Bandwidth Protection (Rule BR-GATEWAY-01)
* Autosave requests to `/api/v1/examination/submissions/{id}/autosave` are granted high-priority throughput.
* Edge Gateway enforces a guaranteed rate limit of at least 300 req/min for exam endpoints, ensuring student submissions are never throttled during high-stakes sessions.

### 3.3. Exam Hall CIDR Subnet Restriction (Rule BR-SYS-04)
* Prior to scheduled exam sessions, administrators configure the laboratory local network block (e.g., `192.168.10.0/24`) via the Admin Console.
* Requests attempting exam submission from unauthorized external IPs are rejected at the edge with HTTP 403 Forbidden without reaching backend worker pools.

### 3.4. Final Gradebook Lock via Transactional Outbox (Rule BR-SYS-08)
When an instructor seals final semester scores, persist the lock in `gradebook.course_gradebook_locks` and simultaneously emit `GRADEBOOK_LOCKED` into `system.outbox_events`.

---

## 4. Administrative API Reference

| Endpoint | Method | Description | Governed Rule |
| :--- | :---: | :--- | :--- |
| `/api/v1/system/auth/users` | GET / POST | Manage platform identities | BR-02, E-4 |
| `/api/v1/system/auth/revoke-session` | POST | Instantaneous token revocation | BR-SYS-02 |
| `/api/v1/system/gateway/metrics` | GET | Real-time proxy RPS & latency | AC-01 |
| `/api/v1/system/gateway/rate-limits` | GET / PUT | Dynamic edge rate limiting | BR-GATEWAY-01, E-GATEWAY-02 |
| `/api/v1/system/gateway/ip-whitelist` | GET / POST / DELETE | Exam room CIDR subnet firewall | BR-SYS-04, E-SYS-02 |
| `/api/v1/system/database/schemas` | GET | 7-schema capacity statistics | T1-A-M0-03 |
| `/api/v1/system/database/reindex` | POST | pgvector HNSW maintenance | BR-SYS-06 |
| `/api/v1/system/storage/quotas` | GET / PUT | Global file upload quotas | BR-STORAGE-02, AC-01 |
| `/api/v1/system/database/backup` | POST | Trigger manual snapshot backup | Subflow A-1, AC-03 |
| `/api/v1/system/tasks/dlq` | GET | Inspect Dead-Letter Queue | BR-SYS-09 |
| `/api/v1/system/tasks/dlq/{id}/retry` | POST | Re-queue failed event to Event Bus | AC-02 |
| `/api/v1/system/infrastructure/health` | GET | Probe 6 core infrastructure services | BR-SYS-10 |
| `/api/v1/system/audit-logs` | GET | Query immutable audit trail | BR-SYS-11 |

---

## 5. Development & Running Instructions

### 5.1. Backend Service
```powershell
cd repo-chinh
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API documentation: `http://localhost:8000/docs`.

### 5.2. Frontend Admin Console
```powershell
cd repo-chinh\frontend
pnpm run dev
```
Access console: `http://localhost:3000`.

### 5.3. Running Test Suites
```powershell
cd repo-chinh
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\pytest.exe tests/ -v
```
All unit tests and integration tests must pass 100% prior to pushing code to git repositories.
