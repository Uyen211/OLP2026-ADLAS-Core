/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

export interface OutboxEventItem {
  id: string;
  event_type: string;
  aggregate_type: string;
  aggregate_id: string;
  payload: Record<string, unknown>;
  status: "PENDING" | "PROCESSING" | "PROCESSED" | "FAILED";
  retry_count: number;
  created_at: string;
  processed_at?: string | null;
}

export interface ActiveBackgroundTask {
  task_id: string;
  name: string;
  category: "AI_EXTRACTION" | "RUBRIC_CALCULATION" | "PLAGIARISM_SCAN" | "REPORT_GEN";
  progress_pct: number;
  started_at: string;
  eta_seconds: number;
  status: "RUNNING" | "COMPLETED" | "FAILED";
}

export interface DeadLetterItem {
  id: string;
  outbox_event_id?: string | null;
  event_type: string;
  payload: Record<string, unknown>;
  error_message: string;
  stack_trace?: string | null;
  retry_attempts: number;
  status: "DEAD_LETTER" | "RETRYING" | "RESOLVED";
  created_at: string;
  resolved_at?: string | null;
}

export interface CoreInfrastructureHealth {
  component_id: string;
  name: string;
  endpoint: string;
  status: "HEALTHY" | "DEGRADED" | "UNHEALTHY";
  latency_ms: number;
  details: Record<string, unknown>;
  last_heartbeat: string;
}

export interface AuditLogItem {
  id: string;
  actor_id?: string | null;
  actor_email?: string | null;
  action: string;
  module: string;
  severity: "INFO" | "WARNING" | "CRITICAL";
  ip_address?: string | null;
  user_agent?: string | null;
  details: Record<string, unknown>;
  created_at: string;
}

export interface PaginatedAuditLogsResponse {
  items: AuditLogItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
