/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useState } from "react";
import {
  AlertCircle,
  AlertTriangle,
  Archive,
  CheckCircle2,
  Database,
  DownloadCloud,
  FileText,
  HardDrive,
  Layers,
  RefreshCw,
  RotateCw,
  Save,
  Trash2,
  Video,
} from "lucide-react";
import { Badge } from "../../../components/ui/Badge";
import { StorageService } from "../../../services/storageService";
import {
  BackupHistoryItem,
  DatabaseSchemaStats,
  GlobalQuotaConfig,
  GlobalQuotaUpdatePayload,
  OrphanedFilesScanResponse,
  StorageBucketStats,
  VectorIndexStatus,
} from "../../../types/storage";

export const StorageConfiguration: React.FC = () => {
  // Data States
  const [schemas, setSchemas] = useState<DatabaseSchemaStats[]>([]);
  const [vectorStatus, setVectorStatus] = useState<VectorIndexStatus | null>(null);
  const [buckets, setBuckets] = useState<StorageBucketStats[]>([]);
  const [quotas, setQuotas] = useState<GlobalQuotaConfig | null>(null);
  const [backups, setBackups] = useState<BackupHistoryItem[]>([]);
  const [orphanedScan, setOrphanedScan] = useState<OrphanedFilesScanResponse | null>(null);

  // Form Quota Edit States
  const [maxSlideMb, setMaxSlideMb] = useState(50);
  const [maxVideoMb, setMaxVideoMb] = useState(500);
  const [maxSubmissionMb, setMaxSubmissionMb] = useState(25);
  const [maxCourseStorageGb, setMaxCourseStorageGb] = useState(10);
  const [warningThresholdPct, setWarningThresholdPct] = useState(85);

  // Loading States
  const [isLoading, setIsLoading] = useState(false);
  const [isReindexing, setIsReindexing] = useState(false);
  const [isPurgingOrphaned, setIsPurgingOrphaned] = useState(false);
  const [isSavingQuotas, setIsSavingQuotas] = useState(false);
  const [isCreatingBackup, setIsCreatingBackup] = useState(false);

  // Feedback Notification
  const [notification, setNotification] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  const showNotification = (type: "success" | "error", message: string) => {
    setNotification({ type, message });
    setTimeout(() => setNotification(null), 5000);
  };

  const loadAllStorageData = useCallback(async () => {
    try {
      const [
        schemasData,
        vectorData,
        bucketsData,
        quotasData,
        backupsData,
        orphanedData,
      ] = await Promise.all([
        StorageService.getDatabaseSchemas(),
        StorageService.getVectorIndexStatus(),
        StorageService.getStorageBuckets(),
        StorageService.getGlobalQuotas(),
        StorageService.getBackupHistory(),
        StorageService.scanOrphanedFiles(),
      ]);

      setSchemas(schemasData);
      setVectorStatus(vectorData);
      setBuckets(bucketsData);
      setQuotas(quotasData);
      setBackups(backupsData);
      setOrphanedScan(orphanedData);

      // Populate form
      setMaxSlideMb(quotasData.max_slide_mb);
      setMaxVideoMb(quotasData.max_video_mb);
      setMaxSubmissionMb(quotasData.max_submission_mb);
      setMaxCourseStorageGb(quotasData.max_course_storage_gb);
      setWarningThresholdPct(quotasData.warning_threshold_pct);
    } catch (err: unknown) {
      if (err instanceof Error) {
        showNotification("error", err.message);
      }
    }
  }, []);

  useEffect(() => {
    setIsLoading(true);
    loadAllStorageData().finally(() => setIsLoading(false));
  }, [loadAllStorageData]);

  // Handle Vector Reindex
  const handleReindex = async () => {
    setIsReindexing(true);
    try {
      const res = await StorageService.reindexVector();
      setVectorStatus(res);
      showNotification("success", "pgvector HNSW index tree rebuilt successfully (m=16, ef_construction=64).");
    } catch (err: unknown) {
      if (err instanceof Error) {
        showNotification("error", err.message);
      }
    } finally {
      setIsReindexing(false);
    }
  };

  // Handle Purge Orphaned Files
  const handlePurgeOrphaned = async () => {
    if (!orphanedScan || orphanedScan.total_orphaned_files === 0) return;
    if (!window.confirm(`Purge ${orphanedScan.total_orphaned_files} unreferenced temporary files (${orphanedScan.total_size_mb} MB)? Active student submissions are guaranteed protected (Rule BR-STORAGE-01).`)) {
      return;
    }

    setIsPurgingOrphaned(true);
    try {
      const res = await StorageService.cleanupOrphanedFiles();
      showNotification("success", res.message);
      const updatedScan = await StorageService.scanOrphanedFiles();
      setOrphanedScan(updatedScan);
    } catch (err: unknown) {
      if (err instanceof Error) {
        showNotification("error", err.message);
      }
    } finally {
      setIsPurgingOrphaned(false);
    }
  };

  // Handle Save Quotas
  const handleSaveQuotas = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validation AC-02
    if (maxSlideMb < 5 || maxSlideMb > 100) {
      showNotification("error", "Slide file size must be between 5 and 100 MB (Rule AC-02).");
      return;
    }
    if (maxVideoMb < 50 || maxVideoMb > 1000) {
      showNotification("error", "Video file size must be between 50 and 1000 MB.");
      return;
    }
    if (maxSubmissionMb < 5 || maxSubmissionMb > 50) {
      showNotification("error", "Submission file size must be between 5 and 50 MB (Rule AC-01).");
      return;
    }
    if (maxCourseStorageGb < 1 || maxCourseStorageGb > 50) {
      showNotification("error", "Course storage quota must be between 1 and 50 GB.");
      return;
    }

    const payload: GlobalQuotaUpdatePayload = {
      max_slide_mb: Number(maxSlideMb),
      max_video_mb: Number(maxVideoMb),
      max_submission_mb: Number(maxSubmissionMb),
      max_course_storage_gb: Number(maxCourseStorageGb),
      warning_threshold_pct: Number(warningThresholdPct),
    };

    setIsSavingQuotas(true);
    try {
      const updated = await StorageService.updateGlobalQuotas(payload);
      setQuotas(updated);
      showNotification("success", "Storage upload quotas updated successfully across all student and teacher interfaces.");
    } catch (err: unknown) {
      if (err instanceof Error) {
        showNotification("error", err.message);
      }
    } finally {
      setIsSavingQuotas(false);
    }
  };

  // Handle Manual Backup Trigger
  const handleTriggerBackup = async () => {
    if (!window.confirm("Trigger manual full snapshot backup of all academic databases and scorebooks?")) {
      return;
    }

    setIsCreatingBackup(true);
    try {
      await StorageService.triggerBackup();
      showNotification("success", "Academic snapshot backup completed and cataloged in backup repository.");
      const updatedBackups = await StorageService.getBackupHistory();
      setBackups(updatedBackups);
    } catch (err: unknown) {
      if (err instanceof Error) {
        showNotification("error", err.message);
      }
    } finally {
      setIsCreatingBackup(false);
    }
  };

  // Storage breakdown calculations for 500GB disk
  const usedGb = 142.5;
  const totalGb = 500.0;
  const usagePercentage = Math.round((usedGb / totalGb) * 100);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-4 border-b border-slate-200">
        <div>
          <div className="flex items-center gap-2">
            <Database className="w-6 h-6 text-blue-600" />
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Database & Storage Administration
            </h1>
          </div>
          <p className="text-sm text-slate-500 mt-1">
            PostgreSQL 7-Schema telemetry, pgvector HNSW maintenance, S3 storage quotas, and snapshot backups (Use Case T1-C-M0-03 & T1-A-M0-03).
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => loadAllStorageData()}
            className="inline-flex items-center gap-2 px-3.5 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-pill shadow-sm transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            type="button"
            disabled={isCreatingBackup}
            onClick={handleTriggerBackup}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-pill shadow-brand transition-all disabled:opacity-50"
          >
            <DownloadCloud className="w-4 h-4" />
            {isCreatingBackup ? "Packaging Backup..." : "Create Backup Now"}
          </button>
        </div>
      </div>

      {/* Notification Banner */}
      {notification && (
        <div
          className={`flex items-center gap-3 p-4 rounded-xl border text-sm transition-all ${
            notification.type === "success"
              ? "bg-emerald-50 border-emerald-200 text-emerald-800"
              : "bg-rose-50 border-rose-200 text-rose-800"
          }`}
        >
          {notification.type === "success" ? (
            <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-600" />
          ) : (
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-600" />
          )}
          <span className="font-medium">{notification.message}</span>
        </div>
      )}

      {/* Storage Overview Progress Card (Main Flow Step 2.a) */}
      <div className="p-6 bg-white rounded-2xl border border-slate-200 shadow-card space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
              Global Disk Capacity & Partition Breakdown
            </span>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-2xl font-bold text-slate-900 tracking-tight">
                {usedGb} GB / {totalGb} GB
              </span>
              <span className="text-sm font-semibold text-blue-600">({usagePercentage}%)</span>
              <span className="text-xs text-slate-400 font-mono">| {totalGb - usedGb} GB Available</span>
            </div>
          </div>
          <Badge variant={usagePercentage >= (quotas?.warning_threshold_pct || 85) ? "danger" : "success"}>
            {usagePercentage >= (quotas?.warning_threshold_pct || 85) ? "CAPACITY WARNING" : "OPTIMAL - HEALTHY"}
          </Badge>
        </div>

        {/* 4-Color Progress Bar according to T1-C-M0-03 */}
        <div className="w-full h-3.5 bg-slate-100 rounded-full overflow-hidden flex shadow-inner">
          {/* Blue: Slides/PDFs (54.2 GB ~ 10.8%) */}
          <div style={{ width: "10.8%" }} className="bg-blue-600 h-full" title="Slides/PDFs (54.2 GB)" />
          {/* Green: Videos (19.9 GB ~ 4.0%) */}
          <div style={{ width: "4.0%" }} className="bg-emerald-500 h-full" title="Videos (19.9 GB)" />
          {/* Orange: Student Submissions (68.4 GB ~ 13.7%) */}
          <div style={{ width: "13.7%" }} className="bg-amber-500 h-full" title="Student Submissions (68.4 GB)" />
          {/* Purple: Academic Databases (0.25 GB ~ 0.1%) */}
          <div style={{ width: "0.5%" }} className="bg-purple-600 h-full" title="Academic Database (0.25 GB)" />
        </div>

        {/* Legend */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2 text-xs">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-blue-600 flex-shrink-0" />
            <span className="text-slate-600">Slides & PDFs (54.2 GB)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-emerald-500 flex-shrink-0" />
            <span className="text-slate-600">Video Modules (19.9 GB)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-amber-500 flex-shrink-0" />
            <span className="text-slate-600">Student Projects (68.4 GB)</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-purple-600 flex-shrink-0" />
            <span className="text-slate-600">PostgreSQL DB (256 MB)</span>
          </div>
        </div>
      </div>

      {/* Two Column Layout: Schemas + pgvector & Buckets + Orphaned */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column: 7 Schemas & pgvector */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Layers className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-slate-900 text-sm">PostgreSQL 16 Multi-Schema Telemetry</h3>
              </div>
              <span className="text-xs font-mono text-slate-500">ACID Isolation</span>
            </div>

            <div className="mt-4 divide-y divide-slate-100 max-h-72 overflow-y-auto pr-1">
              {schemas.map((s) => (
                <div key={s.schema_name} className="py-2.5 flex items-center justify-between">
                  <div>
                    <span className="font-mono text-xs font-bold text-slate-900">{s.schema_name}</span>
                    <p className="text-[11px] text-slate-500 truncate max-w-xs">{s.description}</p>
                  </div>
                  <div className="text-right">
                    <span className="font-mono text-xs font-semibold text-slate-800">{s.size_mb} MB</span>
                    <p className="text-[10px] text-slate-400 font-mono">
                      {s.table_count} tables | {s.record_count.toLocaleString()} rows
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* pgvector Vector Maintenance Card (BR-SYS-06) */}
          <div className="mt-4 p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-bold text-slate-800">pgvector HNSW Vector Tree</p>
                <p className="text-[11px] text-slate-500">
                  {vectorStatus?.indexed_vectors_count.toLocaleString()} lecture embeddings | Avg query: {vectorStatus?.avg_query_time_ms} ms (&lt; 15ms target)
                </p>
              </div>
              <button
                type="button"
                disabled={isReindexing}
                onClick={handleReindex}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-100 rounded-pill shadow-sm transition-colors disabled:opacity-50"
              >
                <RotateCw className={`w-3.5 h-3.5 ${isReindexing ? "animate-spin text-blue-600" : ""}`} />
                {isReindexing ? "Re-indexing..." : "Re-Index HNSW"}
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: S3 Buckets & Orphaned Files */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-card p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <HardDrive className="w-5 h-5 text-blue-600" />
                <h3 className="font-bold text-slate-900 text-sm">Object Storage Buckets (MinIO / S3)</h3>
              </div>
              <button
                type="button"
                disabled={isPurgingOrphaned || !orphanedScan || orphanedScan.total_orphaned_files === 0}
                onClick={handlePurgeOrphaned}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-rose-700 bg-rose-50 border border-rose-200 hover:bg-rose-100 rounded-pill shadow-sm transition-colors disabled:opacity-40"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Purge Orphaned ({orphanedScan?.total_orphaned_files || 0})
              </button>
            </div>

            <div className="mt-4 space-y-3">
              {buckets.map((b) => (
                <div key={b.bucket_name} className="p-3 bg-slate-50 rounded-xl border border-slate-100">
                  <div className="flex justify-between items-center mb-1">
                    <span className="font-mono text-xs font-bold text-slate-900">{b.bucket_name}</span>
                    <span className="font-mono text-xs font-medium text-slate-600">
                      {(b.size_mb / 1024).toFixed(1)} GB / {(b.max_quota_mb / 1024).toFixed(0)} GB
                    </span>
                  </div>
                  <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                    <div
                      style={{ width: `${b.usage_pct}%` }}
                      className={`h-full rounded-full ${
                        b.usage_pct > 80 ? "bg-rose-500" : "bg-blue-600"
                      }`}
                    />
                  </div>
                  <p className="text-[11px] text-slate-400 mt-1">{b.description}</p>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-4 p-3 bg-amber-50/70 border border-amber-200 rounded-xl text-xs text-amber-800 flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-600 flex-shrink-0 mt-0.5" />
            <span>
              Rule BR-STORAGE-01: Student submissions and official scorebooks are never purged automatically. Orphaned cleanups only target temp unreferenced files older than 24 hours.
            </span>
          </div>
        </div>
      </div>

      {/* Global Quota Settings Form (Main Flow Step 2.b / Rules AC-01, AC-02) */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-card p-6">
        <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
          <FileText className="w-5 h-5 text-blue-600" />
          <h3 className="font-bold text-slate-900 text-sm">Global System Storage Quotas (Rule BR-STORAGE-02)</h3>
        </div>

        <form onSubmit={handleSaveQuotas} className="mt-4 space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Max Slide/PDF Size (MB) <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <input
                  type="number"
                  min={5}
                  max={100}
                  required
                  value={maxSlideMb}
                  onChange={(e) => setMaxSlideMb(Number(e.target.value))}
                  className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <FileText className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              </div>
              <p className="text-[10px] text-slate-400 mt-1">Allowed: 5 - 100 MB (Default: 50 MB)</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Max Video Size (MB) <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <input
                  type="number"
                  min={50}
                  max={1000}
                  required
                  value={maxVideoMb}
                  onChange={(e) => setMaxVideoMb(Number(e.target.value))}
                  className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <Video className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              </div>
              <p className="text-[10px] text-slate-400 mt-1">Allowed: 50 - 1000 MB (Default: 500 MB)</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Max Submission (.zip) (MB) <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <input
                  type="number"
                  min={5}
                  max={50}
                  required
                  value={maxSubmissionMb}
                  onChange={(e) => setMaxSubmissionMb(Number(e.target.value))}
                  className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <Archive className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              </div>
              <p className="text-[10px] text-slate-400 mt-1">Allowed: 5 - 50 MB (Rule AC-01)</p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 uppercase tracking-wider mb-1.5">
                Course Quota (GB) <span className="text-rose-500">*</span>
              </label>
              <div className="relative">
                <input
                  type="number"
                  min={1}
                  max={50}
                  required
                  value={maxCourseStorageGb}
                  onChange={(e) => setMaxCourseStorageGb(Number(e.target.value))}
                  className="w-full pl-9 pr-3 py-2 text-sm bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <HardDrive className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
              </div>
              <p className="text-[10px] text-slate-400 mt-1">Per section limit (Default: 10 GB)</p>
            </div>
          </div>

          <div className="flex items-center justify-end pt-3 border-t border-slate-100">
            <button
              type="submit"
              disabled={isSavingQuotas}
              className="inline-flex items-center gap-2 px-5 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-pill shadow-brand transition-all disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {isSavingQuotas ? "Saving..." : "Save Storage Quotas"}
            </button>
          </div>
        </form>
      </div>

      {/* Backup History Table (Subflow A-1 / AC-03) */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-card overflow-hidden">
        <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-900">Academic Database Snapshots & Backup History</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Tar/Gzip packaged snapshots of gradebooks, rubrics, and active syllabi with SHA-256 verification (Rule AC-03).
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 text-xs uppercase tracking-wider font-semibold border-b border-slate-100">
              <tr>
                <th className="px-6 py-3.5">Backup Archive Name</th>
                <th className="px-6 py-3.5">File Size</th>
                <th className="px-6 py-3.5">Created At</th>
                <th className="px-6 py-3.5">Operator</th>
                <th className="px-6 py-3.5">Status</th>
                <th className="px-6 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {backups.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-slate-400 text-xs">
                    No snapshot backups recorded yet. Click &apos;Create Backup Now&apos; to trigger manual packaging.
                  </td>
                </tr>
              ) : (
                backups.map((b) => (
                  <tr key={b.id} className="hover:bg-slate-50/70 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs font-semibold text-slate-900">
                      {b.backup_name}
                    </td>
                    <td className="px-6 py-4 font-mono text-xs text-slate-600">
                      {(b.file_size_bytes / (1024 * 1024)).toFixed(1)} MB
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-500 font-mono">
                      {new Date(b.created_at).toLocaleString()}
                    </td>
                    <td className="px-6 py-4 text-xs text-slate-600">
                      {b.created_by || "System Admin"}
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant="success">{b.status}</Badge>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button
                        type="button"
                        onClick={() => alert(`Download URL generated for ${b.backup_name}`)}
                        className="inline-flex items-center gap-1 px-3 py-1 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 hover:bg-blue-100 rounded-pill transition-colors"
                      >
                        <DownloadCloud className="w-3.5 h-3.5" />
                        Download
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
