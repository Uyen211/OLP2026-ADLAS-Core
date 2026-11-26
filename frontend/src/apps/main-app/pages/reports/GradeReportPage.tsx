/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { clsx } from "clsx";
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  Download,
  FileSpreadsheet,
  FileText,
  Lock,
  RefreshCw,
  ShieldCheck,
  Table2,
  Target,
  Users,
} from "lucide-react";
import { ApiError } from "../../../../services/httpClient";
import { reportingService } from "../../../../services/reportingService";
import type { BloomLevel } from "../../../../types/course";
import type { ExportFormat, ExportPreviewResponse } from "../../../../types/reporting";
import { BloomBadge } from "../../components/BloomBadge";
import { MmButton } from "../../components/MmButton";
import { MmCard } from "../../components/MmCard";
import { PillTabs, type PillTabItem } from "../../components/PillTabs";
import { showToast } from "../../components/Toast";
import { resolveErrorMessage } from "../../constants/errorMessages";
import { TeacherLayout } from "../../layouts/TeacherLayout";
import { GradeExportModal } from "./GradeExportModal";

type SheetTab = "tt08" | "lo";

function formatScore(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return Number(value).toFixed(1);
}

const VALID_BLOOM_LEVELS: ReadonlySet<BloomLevel> = new Set([
  "REMEMBER",
  "UNDERSTAND",
  "APPLY",
  "ANALYZE",
  "EVALUATE",
  "CREATE",
]);

function toBloomLevel(raw: string): BloomLevel {
  const upper = (raw || "").toUpperCase() as BloomLevel;
  return VALID_BLOOM_LEVELS.has(upper) ? upper : "UNDERSTAND";
}

export const GradeReportPage: React.FC = () => {
  const { courseId = "" } = useParams<{ courseId: string }>();

  const [preview, setPreview] = useState<ExportPreviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [activeSheet, setActiveSheet] = useState<SheetTab>("tt08");
  const [exportModalOpen, setExportModalOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState<ExportFormat>("xlsx");

  const loadPreview = useCallback(async () => {
    if (!courseId) return;
    setLoading(true);
    setErrorMessage(null);
    try {
      const data = await reportingService.getExportPreview(courseId);
      setPreview(data);
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? resolveErrorMessage(err.code, err.message)
          : "Không thể tải dữ liệu bảng điểm và báo cáo đào tạo.";
      setErrorMessage(msg);
      showToast("error", msg);
    } finally {
      setLoading(false);
    }
  }, [courseId]);

  useEffect(() => {
    void loadPreview();
  }, [loadPreview]);

  const openExportWithFormat = (format: ExportFormat) => {
    setExportFormat(format);
    setExportModalOpen(true);
  };

  const sheetTabs: PillTabItem<SheetTab>[] = [
    {
      value: "tt08",
      label: "Sheet 1: Diem_Tin_Chi_TT08",
      count: preview?.grade_rows.length ?? 0,
      icon: <FileSpreadsheet className="h-4 w-4" />,
    },
    {
      value: "lo",
      label: "Sheet 2: Ho_So_Nang_Luc_LO",
      count: preview?.lo_rows.length ?? 0,
      icon: <Target className="h-4 w-4" />,
    },
  ];

  return (
    <TeacherLayout>
      {loading ? (
        <div className="space-y-4">
          <div className="h-10 w-80 animate-pulse rounded-mm-btn bg-mm-divider" />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
            <div className="h-24 animate-pulse rounded-mm-card bg-mm-divider/60" />
            <div className="h-24 animate-pulse rounded-mm-card bg-mm-divider/60" />
            <div className="h-24 animate-pulse rounded-mm-card bg-mm-divider/60" />
            <div className="h-24 animate-pulse rounded-mm-card bg-mm-divider/60" />
          </div>
          <div className="h-80 animate-pulse rounded-mm-card bg-mm-divider/50" />
        </div>
      ) : errorMessage || !preview ? (
        <MmCard variant="standard" className="space-y-4 py-12 text-center">
          <AlertCircle className="mx-auto h-10 w-10 text-mm-danger" />
          <div className="space-y-1">
            <h1 className="font-mm-display text-xl font-semibold text-mm-heading">
              Không thể truy cập Báo cáo Bảng điểm
            </h1>
            <p className="mx-auto max-w-lg font-mm-ui text-sm text-mm-text-secondary">
              {errorMessage || "Chưa có dữ liệu sổ điểm cho lớp học phần này."}
            </p>
          </div>
          <div className="flex items-center justify-center gap-2.5 pt-2">
            <Link to={`/courses/${courseId}`}>
              <MmButton variant="secondary">
                <ArrowLeft className="h-4 w-4" />
                <span>Quay lại môn học</span>
              </MmButton>
            </Link>
            <MmButton variant="brand" onClick={() => void loadPreview()}>
              <RefreshCw className="h-4 w-4" />
              <span>Thử tải lại</span>
            </MmButton>
          </div>
        </MmCard>
      ) : (
        <div className="space-y-6">
          {/* Header & Điều hướng */}
          <div className="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
            <div className="space-y-2">
              <Link
                to={`/courses/${courseId}`}
                className="inline-flex items-center gap-1.5 font-mm-ui text-sm font-medium text-mm-text-secondary transition-colors hover:text-mm-heading"
              >
                <ArrowLeft className="h-4 w-4" />
                <span>Quay lại chi tiết môn học</span>
              </Link>
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="font-mm-display text-2xl font-semibold text-mm-heading">
                  Kết xuất Bảng điểm &amp; Báo cáo Đào tạo
                </h1>
                <span
                  className={clsx(
                    "inline-flex items-center gap-1.5 rounded-full px-3 py-1 font-mm-ui text-xs font-medium",
                    preview.is_locked
                      ? "bg-mm-success-bg text-mm-success"
                      : "bg-mm-warning-bg text-mm-warning"
                  )}
                >
                  {preview.is_locked ? (
                    <ShieldCheck className="h-3.5 w-3.5" />
                  ) : (
                    <Lock className="h-3.5 w-3.5" />
                  )}
                  <span>
                    {preview.is_locked
                      ? "SỔ ĐIỂM ĐÃ NIÊM PHONG CHÍNH THỨC"
                      : "SỔ ĐIỂM ĐANG Ở CHẾ ĐỘ DỰ KIẾN (Đóng dấu mờ Watermark)"}
                  </span>
                </span>
              </div>
              <p className="font-mm-ui text-sm text-mm-text-secondary">
                Học phần: <span className="font-medium text-mm-heading">{preview.course_name}</span>{" "}
                ({preview.course_code} · Lớp {preview.section_code})
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <MmButton
                variant="secondary"
                size="sm"
                onClick={() => openExportWithFormat("csv")}
              >
                <Table2 className="h-4 w-4" />
                <span>CSV</span>
              </MmButton>
              <MmButton
                variant="secondary"
                size="sm"
                onClick={() => openExportWithFormat("pdf")}
              >
                <FileText className="h-4 w-4" />
                <span>PDF In ấn</span>
              </MmButton>
              <MmButton variant="brand" onClick={() => openExportWithFormat("xlsx")}>
                <Download className="h-4 w-4" />
                <span>Xuất bảng điểm &amp; Xem trước in</span>
              </MmButton>
            </div>
          </div>

          {/* Thẻ thống kê tổng quan */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MmCard variant="standard" padding="md" className="space-y-1">
              <div className="flex items-center justify-between text-mm-text-secondary">
                <span className="font-mm-ui text-xs">Tổng số sinh viên</span>
                <Users className="h-4 w-4 text-mm-blue-hover" />
              </div>
              <p className="font-mm-data text-2xl font-semibold text-mm-heading">
                {preview.total_students}
              </p>
            </MmCard>

            <MmCard variant="standard" padding="md" className="space-y-1">
              <div className="flex items-center justify-between text-mm-text-secondary">
                <span className="font-mm-ui text-xs">Sinh viên thiếu điểm</span>
                <AlertTriangle
                  className={clsx(
                    "h-4 w-4",
                    preview.missing_grade_students_count > 0
                      ? "text-mm-warning"
                      : "text-mm-success"
                  )}
                />
              </div>
              <p
                className={clsx(
                  "font-mm-data text-2xl font-semibold",
                  preview.missing_grade_students_count > 0
                    ? "text-mm-warning"
                    : "text-mm-success"
                )}
              >
                {preview.missing_grade_students_count}
              </p>
            </MmCard>

            <MmCard variant="standard" padding="md" className="space-y-1">
              <div className="flex items-center justify-between text-mm-text-secondary">
                <span className="font-mm-ui text-xs">Chuẩn đầu ra (LO)</span>
                <Target className="h-4 w-4 text-mm-blue-hover" />
              </div>
              <p className="font-mm-data text-2xl font-semibold text-mm-heading">
                {preview.lo_rows.length}
              </p>
            </MmCard>

            <MmCard variant="standard" padding="md" className="space-y-1">
              <div className="flex items-center justify-between text-mm-text-secondary">
                <span className="font-mm-ui text-xs">Trạng thái khóa sổ</span>
                {preview.is_locked ? (
                  <ShieldCheck className="h-4 w-4 text-mm-success" />
                ) : (
                  <Lock className="h-4 w-4 text-mm-warning" />
                )}
              </div>
              <p className="font-mm-mid text-sm font-semibold text-mm-heading">
                {preview.is_locked ? "Đã khóa chính thức" : "Bản dự kiến"}
              </p>
              {preview.locked_at && (
                <p className="font-mm-data text-[11px] text-mm-text-muted">
                  {new Date(preview.locked_at).toLocaleString("vi-VN")}
                </p>
              )}
            </MmCard>
          </div>

          {/* Biểu ngữ cảnh báo E-EXP-01 */}
          {!preview.is_locked && preview.missing_grade_students_count > 0 && (
            <div
              role="alert"
              className="flex flex-wrap items-start justify-between gap-3 rounded-mm-card border border-mm-warning/40 bg-mm-warning-bg px-5 py-4 text-mm-warning"
            >
              <div className="flex items-start gap-3">
                <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
                <div className="space-y-1">
                  <p className="font-mm-mid text-sm font-semibold">
                    E-EXP-01: Hiện còn {preview.missing_grade_students_count} sinh viên chưa đủ điểm thành phần
                  </p>
                  <p className="font-mm-ui text-xs">
                    Khi xuất tệp ở trạng thái chưa khóa sổ, hệ thống sẽ đóng dấu mờ &quot;
                    {preview.watermark_text || "BẢNG ĐIỂM DỰ KIẾN - CHƯA KHÓA"}&quot; và yêu cầu xác nhận trước khi tải xuống.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Chuyển đổi xem trước 2 Sheet */}
          <PillTabs
            items={sheetTabs}
            value={activeSheet}
            onChange={setActiveSheet}
          />

          {activeSheet === "tt08" ? (
            <MmCard variant="standard" padding="none" className="overflow-hidden">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-mm-divider px-6 py-4">
                <div>
                  <h2 className="font-mm-display text-lg font-semibold text-mm-heading">
                    Sheet 1: Diem_Tin_Chi_TT08
                  </h2>
                  <p className="font-mm-ui text-xs text-mm-text-secondary">
                    Bảng điểm quy đổi Thang 10 (làm tròn 1 chữ số thập phân) → Điểm chữ → Thang 4 chuẩn Thông tư 08/2021/TT-BGDĐT
                  </p>
                </div>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[780px] border-collapse text-left">
                  <thead>
                    <tr className="border-b border-mm-divider bg-mm-divider/35 font-mm-ui text-xs font-medium text-mm-text-secondary">
                      <th className="px-4 py-3 text-center">STT</th>
                      <th className="px-4 py-3">MSSV</th>
                      <th className="px-4 py-3">Họ và tên</th>
                      {preview.group_names.map((group) => (
                        <th key={group} className="px-4 py-3 text-right">
                          {group}
                        </th>
                      ))}
                      <th className="px-4 py-3 text-right">Tổng (10)</th>
                      <th className="px-4 py-3 text-center">Điểm chữ</th>
                      <th className="px-4 py-3 text-right">Thang 4</th>
                      <th className="px-4 py-3">Trạng thái</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-mm-divider font-mm-ui text-sm">
                    {preview.grade_rows.length === 0 ? (
                      <tr>
                        <td
                          colSpan={7 + preview.group_names.length}
                          className="px-6 py-10 text-center text-sm text-mm-text-muted"
                        >
                          Chưa có sinh viên hoặc dữ liệu điểm trong lớp học phần này.
                        </td>
                      </tr>
                    ) : (
                      preview.grade_rows.map((row, index) => (
                        <tr
                          key={`${row.user_code}-${index}`}
                          className={clsx(
                            row.hurdle_failed
                              ? "bg-mm-danger-bg/40"
                              : row.missing
                                ? "bg-mm-warning-bg/35"
                                : "hover:bg-mm-divider/15"
                          )}
                        >
                          <td className="px-4 py-3 text-center font-mm-data text-xs text-mm-text-muted">
                            {index + 1}
                          </td>
                          <td className="px-4 py-3 font-mm-mono text-xs font-medium text-mm-heading">
                            {row.user_code}
                          </td>
                          <td className="px-4 py-3 text-mm-heading">{row.full_name}</td>
                          {preview.group_names.map((group) => (
                            <td
                              key={group}
                              className="px-4 py-3 text-right font-mm-data text-xs text-mm-text-secondary"
                            >
                              {formatScore(row.group_scores[group])}
                            </td>
                          ))}
                          <td className="px-4 py-3 text-right font-mm-data text-sm font-semibold text-mm-heading">
                            {formatScore(row.total_score)}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span
                              className={clsx(
                                "inline-flex min-w-[2.2rem] justify-center rounded-full px-2 py-0.5 font-mm-data text-xs font-semibold",
                                row.letter_grade === "F" || row.hurdle_failed
                                  ? "bg-mm-danger-bg text-mm-danger"
                                  : row.letter_grade
                                    ? "bg-mm-blue-light/35 text-mm-blue-deep"
                                    : "bg-mm-divider text-mm-text-muted"
                              )}
                            >
                              {row.letter_grade || "—"}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right font-mm-data text-xs text-mm-heading">
                            {formatScore(row.scale4)}
                          </td>
                          <td className="px-4 py-3 text-xs">
                            {row.hurdle_failed ? (
                              <span className="inline-flex rounded-full bg-mm-danger-bg px-2.5 py-0.5 font-medium text-mm-danger">
                                Trượt điểm liệt
                              </span>
                            ) : row.missing ? (
                              <span className="inline-flex rounded-full bg-mm-warning-bg px-2.5 py-0.5 font-medium text-mm-warning">
                                Thiếu điểm
                              </span>
                            ) : (
                              <span className="inline-flex rounded-full bg-mm-success-bg px-2.5 py-0.5 font-medium text-mm-success">
                                Đủ điểm
                              </span>
                            )}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </MmCard>
          ) : (
            <MmCard variant="standard" padding="none" className="overflow-hidden">
              <div className="border-b border-mm-divider px-6 py-4">
                <h2 className="font-mm-display text-lg font-semibold text-mm-heading">
                  Sheet 2: Ho_So_Nang_Luc_LO
                </h2>
                <p className="font-mm-ui text-xs text-mm-text-secondary">
                  Tổng hợp ánh xạ Chuẩn đầu ra (Learning Outcomes) với các tiêu chí Rubric đánh giá phục vụ kiểm định OBE
                </p>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full min-w-[700px] border-collapse text-left">
                  <thead>
                    <tr className="border-b border-mm-divider bg-mm-divider/35 font-mm-ui text-xs font-medium text-mm-text-secondary">
                      <th className="px-5 py-3">Mã LO</th>
                      <th className="px-5 py-3">Mô tả chuẩn đầu ra</th>
                      <th className="px-5 py-3">Mức Bloom</th>
                      <th className="px-5 py-3">Tiêu chí Rubric gắn kết</th>
                      <th className="px-5 py-3 text-right">Tổng điểm tối đa</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-mm-divider font-mm-ui text-sm">
                    {preview.lo_rows.length === 0 ? (
                      <tr>
                        <td
                          colSpan={5}
                          className="px-6 py-10 text-center text-sm text-mm-text-muted"
                        >
                          Chưa có chuẩn đầu ra (LO) nào được cấu hình cho môn học này.
                        </td>
                      </tr>
                    ) : (
                      preview.lo_rows.map((lo) => (
                        <tr key={lo.code} className="hover:bg-mm-divider/15">
                          <td className="px-5 py-3.5 font-mm-mono text-xs font-semibold text-mm-heading">
                            {lo.code}
                          </td>
                          <td className="px-5 py-3.5 text-sm text-mm-heading">
                            {lo.description}
                          </td>
                          <td className="px-5 py-3.5">
                            <BloomBadge level={toBloomLevel(lo.bloom_level)} />
                          </td>
                          <td className="px-5 py-3.5">
                            {lo.criterion_titles.length > 0 ? (
                              <div className="flex flex-wrap gap-1.5">
                                {lo.criterion_titles.map((title) => (
                                  <span
                                    key={title}
                                    className="rounded-full bg-mm-btn-secondary px-2.5 py-0.5 text-xs text-mm-text-secondary"
                                  >
                                    {title}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <span className="text-xs text-mm-text-muted">
                                Chưa gắn tiêu chí Rubric
                              </span>
                            )}
                          </td>
                          <td className="px-5 py-3.5 text-right font-mm-data text-sm font-semibold text-mm-heading">
                            {formatScore(lo.max_points)}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </MmCard>
          )}

          <GradeExportModal
            open={exportModalOpen}
            courseId={courseId}
            preview={preview}
            initialFormat={exportFormat}
            onClose={() => setExportModalOpen(false)}
          />
        </div>
      )}
    </TeacherLayout>
  );
};
