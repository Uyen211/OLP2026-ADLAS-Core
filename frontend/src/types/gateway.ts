/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

export interface GatewayMetrics {
  status: "ONLINE" | "DEGRADED" | "OFFLINE";
  total_rps: number;
  average_latency_ms: number;
  success_rate_pct: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  active_connections: number;
  timestamp: string;
}

export interface ServiceModuleHealth {
  module_id: string;
  name: string;
  route_prefix: string;
  status: "HEALTHY" | "HIGH_LOAD" | "UNREACHABLE";
  req_per_min: number;
  error_rate_pct: number;
  latency_ms: number;
  last_restart?: string | null;
}

export interface RateLimitConfig {
  standard_rpm: number;
  exam_rpm: number;
  ip_block_duration_minutes: number;
  exam_mode_enabled: boolean;
  updated_at: string;
}

export interface RateLimitUpdatePayload {
  standard_rpm: number;
  exam_rpm: number;
  ip_block_duration_minutes: number;
  exam_mode_enabled?: boolean;
}

export interface IpWhitelistEntry {
  id: string;
  cidr: string;
  description: string;
  created_at: string;
  created_by: string;
  is_active: boolean;
}

export interface AddIpWhitelistPayload {
  cidr: string;
  description: string;
}
