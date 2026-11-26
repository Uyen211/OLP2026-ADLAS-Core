/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import { clsx } from "clsx";
import {
  AlertTriangle,
  Download,
  FileSpreadsheet,
  FileText,
  Lock,
  Printer,
  ShieldCheck,
  Table2,
} from "lucide-react";
import { ApiError } from "../../../../services/httpClient";
import { reportingService } from "../../../../services/reportingService";
import type { ExportFormat, ExportPreviewResponse } from "../../../../types/reporting";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";
import { resolveErrorMessage } from "../../constants/errorMessages";

export interface GradeExportModalProps {
  open: boolean;
  courseId: string;
  preview: ExportPreviewResponse;
  initialFormat?: ExportFormat;
  onClose: () => void;
}

const FORMAT_OPTIONS: Array<{
  value: ExportFormat;
  title: string;
  subtitle: string;
  badge: string;
}> = [
  {
    value: "xlsx",
    title: "Excel chuẩn Đào tạo (.xlsx)",
    subtitle: "Đủ 2 Sheet độc lập: Diem_Tin_Chi_TT08 và Ho_So_Nang_Luc_LO",
    badge: "2 Sheets",
  },
  {
    value: "csv",
    title: "Tệp dữ liệu CSV (.csv)",
    subtitle: "Mã hóa UTF-8 BOM, tự động khử mã độc Formula / DDE Injection",
    badge: "UTF-8 BOM",
  },
  {
    value: "pdf",
    title: "Biểu mẫu in ấn PDF (.pdf)",
    subtitle: "Khổ A4 ngang có Quốc hiệu, Tên Trường/Khoa và 3 ô ký tên",
    badge: "A4 Ngang",
  },
];

const SIGNATURE_ROLES = [
  "Giảng viên chấm thi",
  "Trưởng Bộ môn",
  "Trưởng Khoa",
];

function formatScore(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return Number(value).toFixed(1);
}

export const GradeExportModal: React.FC<GradeExportModalProps> = ({
  open,
  courseId,
  preview,
  initialFormat = "xlsx",
  onClose,
}) => {
  const [format, setFormat] = useState<ExportFormat>(initialFormat);
  const [confirmDraft, setConfirmDraft] = useState(false);
  const [showPrintPreview, setShowPrintPreview] = useState(true);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setFormat(initialFormat);
    setConfirmDraft(false);
    setShowPrintPreview(true);
    setDownloading(false);
  }, [open, initialFormat]);

  const needsConfirmation =
    !preview.is_locked &&
    (preview.requires_confirmation || preview.missing_grade_students_count > 0);

  const canDownload = !downloading && (!needsConfirmation || confirmDraft);
  const watermarkLabel =
    preview.watermark_text || "BẢNG ĐIỂM DỰ KIẾN - CHƯA KHÓA";

  const today = new Date();
  const formattedDate = `Ngày ${String(today.getDate()).padStart(2, "0")} tháng ${String(
    today.getMonth() + 1
  ).padStart(2, "0")} năm ${today.getFullYear()}`;

  const handleDownload = async () => {
    if (needsConfirmation && !confirmDraft) {
      showToast("error", resolveErrorMessage("E-EXP-01"));
      return;
    }

    const fallbackName = `${preview.section_code}_${preview.course_code}_BangDiem.${format}`;
    const filename = preview.filenames?.[format] || fallbackName;
    const draftFlag = !preview.is_locked ? true : confirmDraft;

    setDownloading(true);
    try {
      if (format === "xlsx") {
        await reportingService.downloadExcel(courseId, draftFlag, filename);
      } else if (format === "csv") {
        await reportingService.downloadCsv(courseId, draftFlag, filename);
      } else {
        await reportingService.downloadPdf(courseId, draftFlag, filename);
      }
      showToast("success", `Đã tải xuống tệp báo cáo "${filename}".`);
      onClose();
    } catch (err) {
      const msg =
        err instanceof ApiError
          ? resolveErrorMessage(err.code, err.message)
          : "Không thể kết xuất tệp bảng điểm. Vui lòng thử lại.";
      showToast("error", msg);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <MmModal
      open={open}
      title="Kết xuất Bảng điểm & Bản xem trước Trang in"
      subtitle={`Học phần ${preview.course_code} · Lớp ${preview.section_code} — ${preview.course_name}`}
      maxWidthClass="max-w-5xl"
      onClose={onClose}
      footer={
        <>
          <MmButton variant="secondary" onClick={onClose} disabled={downloading}>
            Đóng
          </MmButton>
          <MmButton
            variant="brand"
            loading={downloading}
            disabled={!canDownload}
            onClick={() => void handleDownload()}
          >
            <Download className="h-4 w-4" />
            <span>
              {format === "xlsx"
                ? "Tải tệp Excel (.xlsx)"
                : format === "csv"
                  ? "Tải tệp CSV (.csv)"
                  : "Tải tệp PDF (.pdf)"}
            </span>
          </MmButton>
        </>
      }
    >
      <div className="space-y-6">
        {/* Trạng thái pháp lý sổ điểm */}
        <div
          className={clsx(
            "flex flex-wrap items-center justify-between gap-3 rounded-mm-card border px-4 py-3.5",
            preview.is_locked
              ? "border-mm-success/30 bg-mm-success-bg text-mm-success"
              : "border-mm-warning/40 bg-mm-warning-bg text-mm-warning"
          )}
        >
          <div className="flex items-center gap-2.5">
            {preview.is_locked ? (
              <ShieldCheck className="h-5 w-5 shrink-0" />
            ) : (
              <Lock className="h-5 w-5 shrink-0" />
            )}
            <div>
              <p className="font-mm-mid text-sm font-semibold">
                {preview.is_locked
                  ? "SỔ ĐIỂM ĐÃ NIÊM PHONG CHÍNH THỨC"
                  : "SỔ ĐIỂM ĐANG Ở CHẾ ĐỘ DỰ KIẾN (Đóng dấu mờ Watermark)"}
              </p>
              <p className="font-mm-ui text-xs opacity-90">
                {preview.is_locked
                  ? "Tệp kết xuất có giá trị nộp Phòng Đào tạo và không chứa dấu mờ dự kiến."
                  : `Sổ điểm chưa khóa chính thức. Hệ thống sẽ đóng dấu mờ "${watermarkLabel}" lên tệp kết xuất.`}
              </p>
            </div>
          </div>
          <span className="rounded-full bg-mm-bg/80 px-3 py-1 font-mm-data text-xs font-medium text-mm-heading">
            {preview.total_students} sinh viên
          </span>
        </div>

        {/* Cảnh báo E-EXP-01 & Hộp kiểm xác nhận khi còn sinh viên thiếu điểm */}
        {needsConfirmation && (
          <div
            role="alert"
            className="space-y-3 rounded-mm-card border border-mm-danger/30 bg-mm-danger-bg/60 p-4 text-mm-danger"
          >
            <div className="flex items-start gap-2.5">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
              <div className="space-y-1">
                <p className="font-mm-mid text-sm font-semibold">
                  Cảnh báo E-EXP-01: Còn {preview.missing_grade_students_count} sinh viên chưa đủ điểm thành phần
                </p>
                <p className="font-mm-ui text-xs text-mm-heading">
                  Bảng điểm hiện tại chưa hoàn tất toàn bộ cột điểm theo Thông tư 08/2021/TT-BGDĐT. Bạn cần xác nhận bên dưới để tiếp tục xuất bản dự kiến.
                </p>
              </div>
            </div>
            <label className="flex cursor-pointer items-center gap-2.5 rounded-mm-btn border border-mm-danger/25 bg-mm-bg px-3.5 py-2.5 text-mm-heading">
              <input
                type="checkbox"
                checked={confirmDraft}
                onChange={(e) => setConfirmDraft(e.target.checked)}
                className="h-4 w-4 rounded border-mm-border text-mm-blue-hover focus:ring-mm-blue-hover/30"
              />
              <span className="font-mm-ui text-xs font-medium">
                Tôi hiểu và muốn xuất bản dự kiến
              </span>
            </label>
          </div>
        )}

        {/* Chọn định dạng kết xuất */}
        <section className="space-y-3">
          <h3 className="font-mm-display text-sm font-semibold text-mm-heading">
            Chọn định dạng tệp kết xuất
          </h3>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            {FORMAT_OPTIONS.map((opt) => {
              const active = format === opt.value;
              const Icon =
                opt.value === "xlsx"
                  ? FileSpreadsheet
                  : opt.value === "csv"
                    ? Table2
                    : FileText;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => setFormat(opt.value)}
                  className={clsx(
                    "flex flex-col items-start gap-2 rounded-mm-card border p-4 text-left transition-colors",
                    active
                      ? "border-mm-blue-hover bg-mm-blue-light/25"
                      : "border-mm-border bg-mm-bg hover:border-mm-blue-hover/50"
                  )}
                >
                  <div className="flex w-full items-center justify-between gap-2">
                    <Icon
                      className={clsx(
                        "h-5 w-5",
                        active ? "text-mm-blue-deep" : "text-mm-text-secondary"
                      )}
                    />
                    <span className="rounded-full bg-mm-btn-secondary px-2.5 py-0.5 font-mm-data text-[11px] font-medium text-mm-text-secondary">
                      {opt.badge}
                    </span>
                  </div>
                  <span className="font-mm-mid text-sm font-semibold text-mm-heading">
                    {opt.title}
                  </span>
                  <span className="font-mm-ui text-xs leading-relaxed text-mm-text-secondary">
                    {opt.subtitle}
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        {/* Bản xem trước trang in chuẩn biểu mẫu Đào tạo (Print Preview) */}
        <section className="space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Printer className="h-4 w-4 text-mm-blue-hover" />
              <h3 className="font-mm-display text-sm font-semibold text-mm-heading">
                Bản xem trước trang in chuẩn biểu mẫu Đào tạo (Print Preview)
              </h3>
            </div>
            <MmButton
              variant="ghost"
              size="sm"
              onClick={() => setShowPrintPreview((prev) => !prev)}
            >
              <span>{showPrintPreview ? "Thu gọn bản xem trước" : "Mở bản xem trước"}</span>
            </MmButton>
          </div>

          {showPrintPreview && (
            <div className="relative overflow-hidden rounded-mm-card border border-mm-border bg-white p-6 shadow-xs">
              {/* Watermark chéo khi chưa khóa sổ */}
              {!preview.is_locked && (
                <div
                  aria-hidden="true"
                  className="pointer-events-none absolute inset-0 flex items-center justify-center overflow-hidden"
                >
                  <span className="-rotate-12 select-none font-mm-display text-2xl font-semibold tracking-widest text-mm-danger/15 sm:text-4xl">
                    {watermarkLabel}
                  </span>
                </div>
              )}

              <div className="relative z-10 space-y-5">
                {/* Quốc hiệu & Tên Trường / Khoa */}
                <div className="grid grid-cols-1 gap-4 border-b border-mm-divider pb-4 text-center sm:grid-cols-2">
                  <div className="space-y-0.5">
                    <p className="font-mm-mid text-xs font-semibold uppercase text-mm-heading">
                      TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN
                    </p>
                    <p className="font-mm-ui text-xs font-medium uppercase text-mm-text-secondary">
                      KHOA CÔNG NGHỆ PHẦN MỀM
                    </p>
                  </div>
                  <div className="space-y-0.5">
                    <p className="font-mm-mid text-xs font-semibold uppercase text-mm-heading">
                      CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
                    </p>
                    <p className="font-mm-ui text-xs font-medium text-mm-heading underline underline-offset-4">
                      Độc lập - Tự do - Hạnh phúc
                    </p>
                  </div>
                </div>

                {/* Tiêu đề bảng điểm */}
                <div className="space-y-1 text-center">
                  <h4 className="font-mm-display text-base font-semibold uppercase text-mm-heading">
                    BẢNG ĐIỂM TỔNG KẾT HỌC PHẦN (THÔNG TƯ 08/2021/TT-BGDĐT)
                  </h4>
                  <p className="font-mm-ui text-xs text-mm-text-secondary">
                    Học phần: {preview.course_name} ({preview.course_code}) · Lớp học phần:{" "}
                    {preview.section_code}
                  </p>
                </div>

                {/* Bảng xem trước rút gọn */}
                <div className="overflow-x-auto">
                  <table className="w-full border-collapse text-left font-mm-ui text-xs">
                    <thead>
                      <tr className="bg-mm-divider/45 text-mm-heading">
                        <th className="border border-mm-border px-2.5 py-2 text-center">STT</th>
                        <th className="border border-mm-border px-2.5 py-2">MSSV</th>
                        <th className="border border-mm-border px-2.5 py-2">Họ và tên</th>
                        {preview.group_names.map((group) => (
                          <th
                            key={group}
                            className="border border-mm-border px-2.5 py-2 text-right"
                          >
                            {group}
                          </th>
                        ))}
                        <th className="border border-mm-border px-2.5 py-2 text-right">
                          Tổng (10)
                        </th>
                        <th className="border border-mm-border px-2.5 py-2 text-center">
                          Chữ
                        </th>
                        <th className="border border-mm-border px-2.5 py-2 text-right">
                          Thang 4
                        </th>
                        <th className="border border-mm-border px-2.5 py-2">Ghi chú</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.grade_rows.slice(0, 8).map((row, idx) => (
                        <tr
                          key={`${row.user_code}-${idx}`}
                          className={clsx(
                            row.hurdle_failed
                              ? "bg-mm-danger-bg/45"
                              : row.missing
                                ? "bg-mm-warning-bg/45"
                                : "bg-white"
                          )}
                        >
                          <td className="border border-mm-border px-2.5 py-1.5 text-center font-mm-data">
                            {idx + 1}
                          </td>
                          <td className="border border-mm-border px-2.5 py-1.5 font-mm-mono">
                            {row.user_code}
                          </td>
                          <td className="border border-mm-border px-2.5 py-1.5 text-mm-heading">
                            {row.full_name}
                          </td>
                          {preview.group_names.map((group) => (
                            <td
                              key={group}
                              className="border border-mm-border px-2.5 py-1.5 text-right font-mm-data"
                            >
                              {formatScore(row.group_scores[group])}
                            </td>
                          ))}
                          <td className="border border-mm-border px-2.5 py-1.5 text-right font-mm-data font-semibold">
                            {formatScore(row.total_score)}
                          </td>
                          <td className="border border-mm-border px-2.5 py-1.5 text-center font-mm-data font-semibold">
                            {row.letter_grade || "—"}
                          </td>
                          <td className="border border-mm-border px-2.5 py-1.5 text-right font-mm-data">
                            {formatScore(row.scale4)}
                          </td>
                          <td className="border border-mm-border px-2.5 py-1.5">
                            {row.hurdle_failed
                              ? "Trượt điểm liệt"
                              : row.missing
                                ? "Thiếu điểm"
                                : ""}
                          </td>
                        </tr>
                      ))}
                      {preview.grade_rows.length === 0 && (
                        <tr>
                          <td
                            colSpan={7 + preview.group_names.length}
                            className="border border-mm-border px-3 py-4 text-center text-mm-text-muted"
                          >
                            Chưa có dữ liệu điểm sinh viên trong lớp học phần này.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                  {preview.grade_rows.length > 8 && (
                    <p className="mt-2 text-right font-mm-ui text-[11px] text-mm-text-muted">
                      Đang hiển thị 8 / {preview.grade_rows.length} sinh viên đầu tiên. Tệp tải về chứa đầy đủ toàn bộ danh sách lớp.
                    </p>
                  )}
                </div>

                {/* Ngày ký & 3 ô ký tên */}
                <div className="space-y-4 pt-2">
                  <p className="text-right font-mm-ui text-xs italic text-mm-text-secondary">
                    {formattedDate}
                  </p>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                    {SIGNATURE_ROLES.map((role) => (
                      <div
                        key={role}
                        className="flex flex-col items-center rounded-mm-panel border border-dashed border-mm-border px-3 py-3 text-center"
                      >
                        <span className="font-mm-mid text-xs font-semibold text-mm-heading">
                          {role}
                        </span>
                        <span className="font-mm-ui text-[11px] italic text-mm-text-muted">
                          (Ký, ghi rõ họ tên)
                        </span>
                        <div className="h-12" />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>
      </div>
    </MmModal>
  );
};
