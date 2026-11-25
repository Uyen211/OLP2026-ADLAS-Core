/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useEffect, useState } from "react";
import { AlertCircle, ExternalLink } from "lucide-react";
import { examinationService } from "../../../../services/examinationService";
import { ApiError } from "../../../../services/httpClient";
import type {
  RegradeReviewResponse,
  RegradeScope,
  RegradeSummaryResponse,
} from "../../../../types/examination";
import { FormField, mmInputClass } from "../../components/FormField";
import { MmButton } from "../../components/MmButton";
import { MmModal } from "../../components/MmModal";
import { showToast } from "../../components/Toast";
import { formatScore, toNumeric } from "./examHelpers";

export interface RegradeReviewModalProps {
  open: boolean;
  regrade: RegradeSummaryResponse | null;
  onClose: () => void;
  onReviewed: (result: RegradeReviewResponse) => void;
}

export const RegradeReviewModal: React.FC<RegradeReviewModalProps> = ({
  open,
  regrade,
  onClose,
  onReviewed,
}) => {
  const [approved, setApproved] = useState(true);
  const [scope, setScope] = useState<RegradeScope>("SINGLE_STUDENT");
  const [newScore, setNewScore] = useState("");
  const [awardFullCredit, setAwardFullCredit] = useState(true);
  const [correctKeysText, setCorrectKeysText] = useState("");
  const [feedback, setFeedback] = useState("");
  const [loading, setLoading] = useState(false);
  const [bannerError, setBannerError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !regrade) return;
    setApproved(true);
    setScope("SINGLE_STUDENT");
    setNewScore(String(toNumeric(regrade.old_score, 0)));
    setAwardFullCredit(true);
    setCorrectKeysText("");
    setFeedback("");
    setBannerError(null);
  }, [open, regrade]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!regrade) return;
    setBannerError(null);

    if (feedback.trim().length < 3) {
      setBannerError("Phản hồi của Giảng viên phải có ít nhất 3 ký tự.");
      return;
    }

    let parsedNewScore: number | null = null;
    let parsedOptionIds: string[] | null = null;

    if (approved) {
      if (scope === "SINGLE_STUDENT") {
        const numeric = Number(newScore);
        if (newScore.trim() === "" || Number.isNaN(numeric) || numeric < 0 || numeric > 10) {
          setBannerError("Vui lòng nhập điểm mới hợp lệ trong khoảng 0.0 đến 10.0.");
          return;
        }
        parsedNewScore = numeric;
      } else if (!awardFullCredit) {
        const keys = correctKeysText
          .split(",")
          .map((k) => k.trim().toUpperCase())
          .filter(Boolean);
        if (keys.length === 0) {
          setBannerError(
            "Vui lòng nhập ít nhất 1 mã phương án đúng mới (vd: B hoặc A,C) hoặc chọn Cộng trọn điểm câu lỗi."
          );
          return;
        }
        parsedOptionIds = keys;
      }
    }

    setLoading(true);
    try {
      const res = await examinationService.reviewRegradeRequest(regrade.id, {
        approved,
        regrade_scope: approved ? scope : "SINGLE_STUDENT",
        new_score: parsedNewScore,
        correct_option_ids: parsedOptionIds,
        award_full_question_credit: approved && scope === "ENTIRE_CLASS" ? awardFullCredit : false,
        reviewer_feedback: feedback.trim(),
      });

      if (approved && scope === "ENTIRE_CLASS") {
        showToast(
          "success",
          `Đã chấm lại toàn lớp thành công (${res.affected_submissions_count} bài thi cập nhật, đóng ${res.closed_pending_regrades_count} đơn chờ).`
        );
      } else {
        showToast(
          "success",
          approved
            ? "Đã chấp thuận đơn phúc khảo và cập nhật điểm sinh viên."
            : "Đã từ chối đơn phúc khảo."
        );
      }

      onReviewed(res);
      onClose();
    } catch (err) {
      setBannerError(
        err instanceof ApiError
          ? err.message
          : "Không thể xử lý đơn phúc khảo. Vui lòng thử lại."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <MmModal
      open={open}
      title="Xử lý đơn phúc khảo"
      subtitle={
        regrade
          ? `Điểm hiện tại: ${formatScore(regrade.old_score)} / 10.0`
          : undefined
      }
      maxWidthClass="max-w-xl"
      onClose={onClose}
      footer={
        <>
          <MmButton variant="secondary" onClick={onClose} disabled={loading}>
            Hủy bỏ
          </MmButton>
          <MmButton
            type="submit"
            form="regrade-review-form"
            variant={approved ? "brand" : "danger"}
            loading={loading}
          >
            {approved ? "Xác nhận chấp thuận" : "Xác nhận từ chối"}
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

      {regrade && (
        <div className="mb-4 rounded-mm-panel border border-mm-border bg-mm-divider/30 p-3.5">
          <p className="font-mm-ui text-xs font-medium text-mm-text-muted">
            Lý do sinh viên khiếu nại
          </p>
          <p className="mt-1 whitespace-pre-wrap font-mm-ui text-sm text-mm-heading">
            {regrade.student_reason}
          </p>
          {regrade.evidence_url && (
            <a
              href={regrade.evidence_url}
              target="_blank"
              rel="noreferrer"
              className="mt-2 inline-flex items-center gap-1 font-mm-ui text-xs font-medium text-mm-blue-hover hover:underline"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              <span>Xem minh chứng đính kèm</span>
            </a>
          )}
        </div>
      )}

      <form
        id="regrade-review-form"
        onSubmit={handleSubmit}
        noValidate
        className="space-y-4"
      >
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => setApproved(true)}
            className={`rounded-mm-btn border px-4 py-2.5 font-mm-ui text-sm font-medium transition-colors ${
              approved
                ? "border-mm-blue-hover bg-mm-blue-light/25 text-mm-blue-hover"
                : "border-mm-border bg-mm-bg text-mm-text-secondary hover:bg-mm-divider/40"
            }`}
          >
            Chấp thuận phúc khảo
          </button>
          <button
            type="button"
            onClick={() => setApproved(false)}
            className={`rounded-mm-btn border px-4 py-2.5 font-mm-ui text-sm font-medium transition-colors ${
              !approved
                ? "border-mm-danger bg-mm-danger-bg text-mm-danger"
                : "border-mm-border bg-mm-bg text-mm-text-secondary hover:bg-mm-divider/40"
            }`}
          >
            Từ chối (Giữ nguyên điểm)
          </button>
        </div>

        {approved && (
          <div className="space-y-4 rounded-mm-panel border border-mm-border p-4">
            <FormField label="Phạm vi chấm lại" htmlFor="regrade-scope" required>
              <select
                id="regrade-scope"
                value={scope}
                onChange={(e) => setScope(e.target.value as RegradeScope)}
                className={mmInputClass(false)}
              >
                <option value="SINGLE_STUDENT">
                  Cá nhân sinh viên này (SINGLE_STUDENT)
                </option>
                <option value="ENTIRE_CLASS">
                  Chấm lại toàn lớp khi đề gốc sai đáp án (ENTIRE_CLASS)
                </option>
              </select>
            </FormField>

            {scope === "SINGLE_STUDENT" ? (
              <FormField
                label="Điểm tổng bài mới (thang 10.0)"
                htmlFor="regrade-new-score"
                required
              >
                <input
                  id="regrade-new-score"
                  type="number"
                  min={0}
                  max={10}
                  step="0.1"
                  value={newScore}
                  onChange={(e) => setNewScore(e.target.value)}
                  className={mmInputClass(false)}
                />
              </FormField>
            ) : (
              <div className="space-y-3">
                <label className="flex cursor-pointer items-start gap-2.5 font-mm-ui text-sm text-mm-heading">
                  <input
                    type="checkbox"
                    checked={awardFullCredit}
                    onChange={(e) => setAwardFullCredit(e.target.checked)}
                    className="mt-0.5 h-4 w-4 accent-mm-blue-hover"
                  />
                  <span>
                    Cộng trọn điểm câu hỏi bị lỗi cho tất cả sinh viên đã nộp bài
                  </span>
                </label>

                {!awardFullCredit && (
                  <FormField
                    label="Mã phương án đúng chuẩn mới"
                    htmlFor="regrade-correct-keys"
                    required
                    helper="Nhập các mã đáp án đúng cách nhau bằng dấu phẩy (vd: B hoặc A,C)"
                  >
                    <input
                      id="regrade-correct-keys"
                      type="text"
                      value={correctKeysText}
                      onChange={(e) => setCorrectKeysText(e.target.value.toUpperCase())}
                      placeholder="vd: B"
                      className={`${mmInputClass(false)} font-mm-mono`}
                    />
                  </FormField>
                )}
              </div>
            )}
          </div>
        )}

        <FormField
          label="Phản hồi kết quả phúc khảo"
          htmlFor="regrade-feedback"
          required
          helper="Sinh viên sẽ nhìn thấy phản hồi này trong màn hình kết quả"
        >
          <textarea
            id="regrade-feedback"
            rows={3}
            maxLength={1000}
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            placeholder="Nhập giải thích kết quả duyệt phúc khảo..."
            className={mmInputClass(false)}
          />
        </FormField>
      </form>
    </MmModal>
  );
};
