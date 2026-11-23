/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from "react";
import { AlertCircle, CheckCircle2, Download, Upload } from "lucide-react";
import { courseService } from "../../../../services/courseService";
import { ApiError } from "../../../../services/httpClient";
import type { RosterPreviewResponse, RosterRowStatus } from "../../../../types/course";
import { FileDropzone } from "../../components/FileDropzone";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";

export interface RosterImportModalProps {
  open: boolean;
  courseId: string;
  onClose: () => void;
  onImported: () => void;
}

const ROW_STATUS_LABELS: Record<RosterRowStatus, string> = {
  VALID: "Hợp lệ",
  DUPLICATE_IN_COURSE: "Đã có trong lớp",
  DUPLICATE_IN_FILE: "Trùng trong tệp",
  INVALID: "Lỗi dữ liệu",
};

export const RosterImportModal: React.FC<RosterImportModalProps> = ({
  open,
  courseId,
  onClose,
  onImported,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<RosterPreviewResponse | null>(null);
  const [sendNotification, setSendNotification] = useState(true);
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [downloadingTpl, setDownloadingTpl] = useState(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [missingColumns, setMissingColumns] = useState<string[]>([]);

  const reset = () => {
    setFile(null);
    setPreview(null);
    setSendNotification(true);
    setErrorBanner(null);
    setMissingColumns([]);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleFileSelect = async (nextFile: File | null) => {
    setFile(nextFile);
    setPreview(null);
    setErrorBanner(null);
    setMissingColumns([]);

    if (!nextFile) return;

    setLoadingPreview(true);
    try {
      const result = await courseService.previewRosterUpload(courseId, nextFile);
      setPreview(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrorBanner(err.message);
        if (err.missingColumns && err.missingColumns.length > 0) {
          setMissingColumns(err.missingColumns);
        }
      } else {
        setErrorBanner("Không thể đọc tệp danh sách sinh viên. Vui lòng kiểm tra lại định dạng.");
      }
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleDownloadTemplate = async () => {
    setDownloadingTpl(true);
    try {
      await courseService.downloadRosterTemplate();
    } catch (err) {
      showToast(
        "error",
        err instanceof ApiError ? err.message : "Không thể tải tệp mẫu danh sách lớp."
      );
    } finally {
      setDownloadingTpl(false);
    }
  };

  const handleConfirm = async () => {
    if (!file || !preview || preview.valid_count === 0) return;

    setConfirming(true);
    setErrorBanner(null);
    try {
      const res = await courseService.confirmRosterUpload(courseId, file, sendNotification);
      showToast(
        "success",
        `Đã thêm ${res.added} sinh viên vào lớp (${res.created_accounts} tài khoản mới, bỏ qua ${res.skipped_duplicates} dòng trùng).`
      );
      reset();
      onImported();
      onClose();
    } catch (err) {
      setErrorBanner(
        err instanceof ApiError ? err.message : "Không thể xác nhận nhập danh sách lớp."
      );
    } finally {
      setConfirming(false);
    }
  };

  const hasFormatError = Boolean(errorBanner) || missingColumns.length > 0;
  const canConfirm =
    Boolean(file) &&
    Boolean(preview) &&
    !hasFormatError &&
    !loadingPreview &&
    (preview?.valid_count ?? 0) > 0;

  return (
    <MmModal
      open={open}
      title="Nhập danh sách sinh viên từ Excel / CSV"
      subtitle="Tải tệp lên để kiểm tra trước 5 dòng đầu và phát hiện trùng lặp trước khi lưu"
      onClose={handleClose}
      maxWidthClass="max-w-3xl"
      footer={
        <>
          <MmButton variant="secondary" onClick={handleClose} disabled={confirming}>
            Hủy bỏ
          </MmButton>
          <MmButton
            variant="brand"
            disabled={!canConfirm}
            loading={confirming}
            onClick={handleConfirm}
          >
            <Upload className="h-4 w-4" />
            <span>
              Xác nhận thêm {preview && preview.valid_count > 0 ? `(${preview.valid_count} SV)` : ""}
            </span>
          </MmButton>
        </>
      }
    >
      <div className="space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-mm-panel border border-mm-border bg-mm-divider/40 px-4 py-3">
          <div className="font-mm-ui text-xs text-mm-text-secondary">
            Tệp cần có 3 cột bắt buộc:{" "}
            <span className="font-medium text-mm-heading">MSSV</span>,{" "}
            <span className="font-medium text-mm-heading">Họ và tên</span>,{" "}
            <span className="font-medium text-mm-heading">Email</span>.
          </div>
          <MmButton
            variant="secondary"
            size="sm"
            loading={downloadingTpl}
            onClick={handleDownloadTemplate}
          >
            <Download className="h-3.5 w-3.5" />
            <span>Tải tệp mẫu (.xlsx)</span>
          </MmButton>
        </div>

        <FileDropzone
          file={file}
          onFileSelect={handleFileSelect}
          hasError={hasFormatError}
          disabled={loadingPreview || confirming}
        />

        {loadingPreview && (
          <p className="text-center font-mm-ui text-sm text-mm-text-secondary">
            Đang phân tích dữ liệu tệp danh sách sinh viên...
          </p>
        )}

        {errorBanner && (
          <div
            role="alert"
            className="flex items-start gap-2.5 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-4 py-3 text-mm-danger"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <div className="font-mm-ui text-sm">
              <p>{errorBanner}</p>
              {missingColumns.length > 0 && (
                <p className="mt-1 text-xs">
                  Các cột bị thiếu: <span className="font-medium">{missingColumns.join(", ")}</span>
                </p>
              )}
            </div>
          </div>
        )}

        {preview && (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-mm-panel border border-mm-border p-3">
                <p className="font-mm-ui text-xs text-mm-text-muted">Tổng số dòng</p>
                <p className="mt-1 font-mm-data text-xl font-medium text-mm-heading">
                  {preview.total_rows}
                </p>
              </div>
              <div className="rounded-mm-panel border border-mm-success/30 bg-mm-success-bg/60 p-3">
                <p className="font-mm-ui text-xs text-mm-success">Hợp lệ</p>
                <p className="mt-1 font-mm-data text-xl font-medium text-mm-success">
                  {preview.valid_count}
                </p>
              </div>
              <div className="rounded-mm-panel border border-mm-warning/30 bg-mm-warning-bg p-3">
                <p className="font-mm-ui text-xs text-mm-warning">Bỏ qua do trùng</p>
                <p className="mt-1 font-mm-data text-xl font-medium text-mm-warning">
                  {preview.duplicate_count}
                </p>
              </div>
              <div className="rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg p-3">
                <p className="font-mm-ui text-xs text-mm-danger">Dòng lỗi</p>
                <p className="mt-1 font-mm-data text-xl font-medium text-mm-danger">
                  {preview.error_count}
                </p>
              </div>
            </div>

            {preview.preview_rows.length > 0 && (
              <div className="overflow-x-auto rounded-mm-panel border border-mm-border">
                <table className="w-full border-collapse text-left">
                  <thead>
                    <tr className="border-b border-mm-divider bg-mm-divider/50 font-mm-ui text-xs font-medium text-mm-text-secondary">
                      <th className="px-3.5 py-2.5">Dòng</th>
                      <th className="px-3.5 py-2.5">MSSV</th>
                      <th className="px-3.5 py-2.5">Họ và tên</th>
                      <th className="px-3.5 py-2.5">Email</th>
                      <th className="px-3.5 py-2.5">Trạng thái</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-mm-divider font-mm-ui text-sm">
                    {preview.preview_rows.map((row) => {
                      const isDup =
                        row.status === "DUPLICATE_IN_COURSE" ||
                        row.status === "DUPLICATE_IN_FILE";
                      const isInvalid = row.status === "INVALID";
                      return (
                        <tr
                          key={row.row_number}
                          className={
                            isDup
                              ? "bg-mm-warning-bg"
                              : isInvalid
                                ? "bg-mm-danger-bg/60"
                                : "bg-mm-bg"
                          }
                        >
                          <td className="px-3.5 py-2.5 font-mm-data text-xs text-mm-text-muted">
                            {row.row_number}
                          </td>
                          <td className="px-3.5 py-2.5 font-mm-mono text-xs text-mm-heading">
                            {row.user_code || "—"}
                          </td>
                          <td className="px-3.5 py-2.5 text-mm-heading">
                            {row.full_name || "—"}
                          </td>
                          <td className="px-3.5 py-2.5 text-mm-text-secondary">
                            {row.email || "—"}
                          </td>
                          <td className="px-3.5 py-2.5 text-xs">
                            <span
                              className={
                                isDup
                                  ? "inline-flex items-center rounded-full bg-white/80 px-2.5 py-0.5 font-medium text-mm-warning"
                                  : isInvalid
                                    ? "inline-flex items-center rounded-full bg-white/80 px-2.5 py-0.5 font-medium text-mm-danger"
                                    : "inline-flex items-center gap-1 rounded-full bg-mm-success-bg px-2.5 py-0.5 font-medium text-mm-success"
                              }
                            >
                              {row.status === "VALID" && (
                                <CheckCircle2 className="h-3.5 w-3.5" />
                              )}
                              {ROW_STATUS_LABELS[row.status]}
                            </span>
                            {row.reason && (
                              <p className="mt-0.5 text-[11px] text-mm-text-helper">
                                {row.reason}
                              </p>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            <label className="flex cursor-pointer items-center gap-2.5 rounded-mm-panel border border-mm-border px-4 py-3">
              <input
                type="checkbox"
                checked={sendNotification}
                onChange={(e) => setSendNotification(e.target.checked)}
                className="h-4 w-4 rounded border-mm-border text-mm-blue-hover focus:ring-mm-blue-hover/30"
              />
              <span className="font-mm-ui text-sm text-mm-text-secondary">
                Tự động gửi email thông báo tài khoản cho sinh viên mới
              </span>
            </label>
          </div>
        )}
      </div>
    </MmModal>
  );
};
