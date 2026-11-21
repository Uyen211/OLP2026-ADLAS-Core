/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

export interface DatabaseSchemaStats {
  schema_name: string;
  description: string;
  table_count: number;
  record_count: number;
  size_mb: number;
  status: "HEALTHY" | "OPTIMAL" | "ATTENTION";
}

export interface VectorIndexStatus {
  table_name: string;
  index_name: string;
  algorithm: string;
  m_parameter: number;
  ef_construction: number;
  indexed_vectors_count: number;
  avg_query_time_ms: number;
  last_reindexed_at?: string | null;
}

export interface StorageBucketStats {
  bucket_name: string;
  description: string;
  object_count: number;
  size_mb: number;
  max_quota_mb: number;
  usage_pct: number;
  status: "NORMAL" | "WARNING" | "FULL";
}

export interface OrphanedFileItem {
  file_id: string;
  bucket_name: string;
  file_path: string;
  size_bytes: number;
  uploaded_at: string;
  age_hours: number;
}

export interface OrphanedFilesScanResponse {
  total_orphaned_files: number;
  total_size_mb: number;
  items: OrphanedFileItem[];
  scanned_at: string;
}

export interface GlobalQuotaConfig {
  max_slide_mb: number;
  max_video_mb: number;
  max_submission_mb: number;
  max_course_storage_gb: number;
  warning_threshold_pct: number;
  updated_at?: string | null;
}

export interface GlobalQuotaUpdatePayload {
  max_slide_mb: number;
  max_video_mb: number;
  max_submission_mb: number;
  max_course_storage_gb: number;
  warning_threshold_pct: number;
}

export interface BackupHistoryItem {
  id: string;
  backup_name: string;
  file_size_bytes: number;
  storage_path?: string | null;
  created_by?: string | null;
  created_at: string;
  status: string;
}
