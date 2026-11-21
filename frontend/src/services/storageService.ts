/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import {
  BackupHistoryItem,
  DatabaseSchemaStats,
  GlobalQuotaConfig,
  GlobalQuotaUpdatePayload,
  OrphanedFilesScanResponse,
  StorageBucketStats,
  VectorIndexStatus,
} from "../types/storage";

const BASE_URL = import.meta.env.VITE_BACKEND_API_URL || "/api/v1";

export class StorageService {
  private static getHeaders(): HeadersInit {
    const token = localStorage.getItem("adlas_token");
    return {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    };
  }

  /**
   * Fetch 7-schema database storage stats.
   */
  static async getDatabaseSchemas(): Promise<DatabaseSchemaStats[]> {
    const response = await fetch(`${BASE_URL}/system/database/schemas`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch database schemas stats.");
    }
    return response.json();
  }

  /**
   * Inspect vector index status.
   */
  static async getVectorIndexStatus(): Promise<VectorIndexStatus> {
    const response = await fetch(`${BASE_URL}/system/database/vector-index`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch vector index status.");
    }
    return response.json();
  }

  /**
   * Rebuild pgvector HNSW index tree (Rule BR-SYS-06).
   */
  static async reindexVector(): Promise<VectorIndexStatus> {
    const response = await fetch(`${BASE_URL}/system/database/reindex`, {
      method: "POST",
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to trigger vector re-indexing.");
    }
    return response.json();
  }

  /**
   * Query S3 buckets capacity and usage.
   */
  static async getStorageBuckets(): Promise<StorageBucketStats[]> {
    const response = await fetch(`${BASE_URL}/system/storage/buckets`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch storage buckets stats.");
    }
    return response.json();
  }

  /**
   * Scan for orphaned S3 files older than 24 hours (Rule BR-SYS-07).
   */
  static async scanOrphanedFiles(): Promise<OrphanedFilesScanResponse> {
    const response = await fetch(`${BASE_URL}/system/storage/orphaned-files`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to scan orphaned files.");
    }
    return response.json();
  }

  /**
   * Purge scanned orphaned files safely (Rule BR-STORAGE-01).
   */
  static async cleanupOrphanedFiles(): Promise<{
    cleaned_count: number;
    freed_mb: number;
    message: string;
  }> {
    const response = await fetch(`${BASE_URL}/system/storage/cleanup-orphaned`, {
      method: "POST",
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to clean up orphaned files.");
    }
    return response.json();
  }

  /**
   * Get global storage quotas.
   */
  static async getGlobalQuotas(): Promise<GlobalQuotaConfig> {
    const response = await fetch(`${BASE_URL}/system/storage/quotas`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch storage quotas.");
    }
    return response.json();
  }

  /**
   * Update global upload and course storage quotas (Rules AC-01, AC-02).
   */
  static async updateGlobalQuotas(payload: GlobalQuotaUpdatePayload): Promise<GlobalQuotaConfig> {
    const response = await fetch(`${BASE_URL}/system/storage/quotas`, {
      method: "PUT",
      headers: this.getHeaders(),
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({}));
      throw new Error(err.detail || "Failed to update storage quotas.");
    }
    return response.json();
  }

  /**
   * Trigger manual full academic backup (Subflow A-1 / AC-03).
   */
  static async triggerBackup(): Promise<{
    backup_id: string;
    backup_name: string;
    file_size_bytes: number;
    status: string;
  }> {
    const response = await fetch(`${BASE_URL}/system/database/backup`, {
      method: "POST",
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to initiate database backup.");
    }
    return response.json();
  }

  /**
   * Retrieve backup history records.
   */
  static async getBackupHistory(): Promise<BackupHistoryItem[]> {
    const response = await fetch(`${BASE_URL}/system/database/backups`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error("Failed to fetch backup history.");
    }
    return response.json();
  }
}
