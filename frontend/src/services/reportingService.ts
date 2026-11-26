/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import type { ExportPreviewResponse } from "../types/reporting";
import { httpDownloadBlob, httpRequest } from "./httpClient";

export const reportingService = {
  /**
   * Lấy dữ liệu xem trước bảng điểm, hồ sơ năng lực LO và trạng thái khóa sổ điểm
   */
  getExportPreview(courseId: string): Promise<ExportPreviewResponse> {
    return httpRequest<ExportPreviewResponse>(
      `/analytics/reports/courses/${courseId}/export-preview`
    );
  },

  /**
   * Tải tệp Excel (.xlsx) 2 Sheets (Diem_Tin_Chi_TT08 & Ho_So_Nang_Luc_LO)
   */
  downloadExcel(
    courseId: string,
    confirmDraft = false,
    filename = "bang-diem.xlsx"
  ): Promise<void> {
    const query = confirmDraft ? "?confirm_draft=true" : "?confirm_draft=false";
    return httpDownloadBlob(
      `/analytics/reports/courses/${courseId}/export/excel${query}`,
      filename
    );
  },

  /**
   * Tải tệp CSV (UTF-8 BOM, đã khử mã độc Formula Injection)
   */
  downloadCsv(
    courseId: string,
    confirmDraft = false,
    filename = "bang-diem.csv"
  ): Promise<void> {
    const query = confirmDraft ? "?confirm_draft=true" : "?confirm_draft=false";
    return httpDownloadBlob(
      `/analytics/reports/courses/${courseId}/export/csv${query}`,
      filename
    );
  },

  /**
   * Tải tệp PDF chuẩn in ấn A4 ngang có Quốc hiệu và 3 ô ký tên
   */
  downloadPdf(
    courseId: string,
    confirmDraft = false,
    filename = "bang-diem.pdf"
  ): Promise<void> {
    const query = confirmDraft ? "?confirm_draft=true" : "?confirm_draft=false";
    return httpDownloadBlob(
      `/analytics/reports/courses/${courseId}/export/pdf${query}`,
      filename
    );
  },
};
