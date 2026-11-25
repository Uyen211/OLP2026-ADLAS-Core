/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import { AlertCircle } from "lucide-react";
import { examinationService } from "../../../../services/examinationService";
import { ApiError } from "../../../../services/httpClient";
import type {
  RegradeSummaryResponse,
  ResultQuestionAnalysis,
} from "../../../../types/examination";
import { FormField, mmInputClass } from "../../components/FormField";
import { MathCodeContent } from "../../components/MathCodeContent";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";

export interface RegradeSubmitModalProps {
  open: boolean;
  submissionId: string;
  question: ResultQuestionAnalysis | null;
  onClose: () => void;
  onSubmitted: (regrade: RegradeSummaryResponse) => void;
}

export const RegradeSubmitModal: React.FC<RegradeSubmitModalProps> = ({
  open,
  submissionId,
  question,
  onClose,
  onSubmitted,
}) => {
  const [reason, setReason] = useState("");
  const [evidenceUrl, setEvidenceUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [bannerError, setBannerError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setReason("");
    setEvidenceUrl("");
    setBannerError(null);
  }, [open, question]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!question) return;
    setBannerError(null);

    const cleanedReason = reason.trim();
    if (cleanedReason.length < 30 || cleanedReason.length > 500) {
      setBannerError("Lý do phúc khảo phải có độ dài từ 30 đến 500 ký tự.");
      return;
    }

    const cleanedUrl = evidenceUrl.trim();
    if (cleanedUrl && !/^https?:\/\/.+/i.test(cleanedUrl)) {
      setBannerError("Liên kết minh chứng phải bắt đầu bằng http:// hoặc https://.");
      return;
    }

    setLoading(true);
    try {
      const created = await examinationService.createRegradeRequest(submissionId, {
        attempt_question_id: question.attempt_question_id,
        student_reason: cleanedReason,
        evidence_url: cleanedUrl || null,
      });
      showToast(
        "success",
        "Đã gửi đơn phúc khảo thành công! Giảng viên sẽ xem xét và phản hồi."
      );
      onSubmitted(created);
      onClose();
    } catch (err) {
      setBannerError(
        err instanceof ApiError
          ? err.message
          : "Không thể gửi đơn phúc khảo. Vui lòng thử lại."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <MmModal
      open={open}
      title={
        question
          ? `Gửi đơn phúc khảo - Câu ${question.question_order}`
          : "Gửi đơn phúc khảo"
      }
      subtitle="Nêu rõ lập luận hoặc bằng chứng học thuật (30 - 500 ký tự)"
      maxWidthClass="max-w-xl"
      onClose={onClose}
      footer={
        <>
          <MmButton variant="secondary" onClick={onClose} disabled={loading}>
            Hủy bỏ
          </MmButton>
          <MmButton
            type="submit"
            form="regrade-submit-form"
            variant="brand"
            loading={loading}
          >
            Gửi đơn phúc khảo
          </MmButton>
        </>
      }
    >
      {bannerError && (
        <div
          role="alert"
          className="mb-4 flex items-start gap-2 rounded-mm-panel border border-mm-danger/30 bg-mm-danger-bg px-3.5 py-2.5 text-mm-danger"
        >
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
          <span className="font-mm-ui text-sm">{bannerError}</span>
        </div>
      )}

      {question && (
        <div className="mb-4 rounded-mm-panel border border-mm-border bg-mm-divider/30 p-3.5">
          <p className="mb-1 font-mm-ui text-xs font-medium text-mm-text-muted">
            Nội dung câu hỏi
          </p>
          <MathCodeContent
            content={question.question_text}
            className="text-sm text-mm-heading"
          />
        </div>
      )}

      <form
        id="regrade-submit-form"
        onSubmit={handleSubmit}
        noValidate
        className="space-y-4"
      >
        <FormField
          label="Lý do khiếu nại / phúc khảo"
          htmlFor="regrade-reason"
          required
          helper={`Độ dài hiện tại: ${reason.trim().length}/500 ký tự (tối thiểu 30 ký tự)`}
        >
          <textarea
            id="regrade-reason"
            rows={4}
            maxLength={500}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Trình bày cụ thể lý do đáp án của bạn đúng hoặc đề bài có sai sót..."
            className={mmInputClass(false)}
          />
        </FormField>

        <FormField
          label="Liên kết tài liệu minh chứng (tùy chọn)"
          htmlFor="regrade-evidence"
          helper="Đường dẫn tới giáo trình, slide hoặc tài liệu tham khảo (http/https)"
        >
          <input
            id="regrade-evidence"
            type="url"
            maxLength={500}
            value={evidenceUrl}
            onChange={(e) => setEvidenceUrl(e.target.value)}
            placeholder="https://..."
            className={mmInputClass(false)}
          />
        </FormField>
      </form>
    </MmModal>
  );
};
