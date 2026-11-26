/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React, { useState } from "react";
import { AlertTriangle, CheckCircle2, HelpCircle, Loader2, Lock } from "lucide-react";
import { learningService } from "../../../../services/learningService";
import { ApiError } from "../../../../services/httpClient";
import type { MaterialCheckpoint } from "../../../../types/learning";
import { MmButton } from "../../components/MmButton";
import { showToast } from "../../components/Toast";

export interface DocumentCheckpointsPanelProps {
  courseId: string;
  checkpoints: MaterialCheckpoint[];
  isCompleted: boolean;
  completing: boolean;
  onCheckpointPassed: (checkpointId: string) => void;
  onCompleteMaterial: () => void;
}

export const DocumentCheckpointsPanel: React.FC<DocumentCheckpointsPanelProps> = ({
  courseId,
  checkpoints,
  isCompleted,
  completing,
  onCheckpointPassed,
  onCompleteMaterial,
}) => {
  const [selectedMap, setSelectedMap] = useState<Record<string, string>>({});
  const [submittingId, setSubmittingId] = useState<string | null>(null);
  const [feedbackMap, setFeedbackMap] = useState<Record<string, { ok: boolean; text: string }>>({});

  const blockingCheckpoints = checkpoints.filter((c) => c.is_blocking);
  const allBlockingPassed = blockingCheckpoints.every((c) => c.is_passed);

  const handleSubmitOne = async (chk: MaterialCheckpoint) => {
    const selected = selectedMap[chk.id];
    if (!selected) {
      showToast("warning", "Vui lòng chọn một phương án trước khi kiểm tra.");
      return;
    }
    setSubmittingId(chk.id);
    try {
      const res = await learningService.submitCheckpoint(courseId, chk.id, selected);
      setFeedbackMap((prev) => ({
        ...prev,
        [chk.id]: { ok: res.is_correct, text: res.message },
      }));
      if (res.is_correct) {
        onCheckpointPassed(chk.id);
      }
    } catch (err) {
      showToast("error", err instanceof ApiError ? err.message : "Lỗi khi kiểm tra đáp án.");
    } finally {
      setSubmittingId(null);
    }
  };

  return (
    <div className="mt-4 space-y-3 rounded-mm border border-mm-divider bg-mm-surface p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-mm-divider pb-3">
        <div className="flex items-center gap-2">
          <HelpCircle className="h-4 w-4 text-mm-brand" />
          <h4 className="text-sm font-semibold text-mm-heading">
            Kiểm tra mức độ hiểu tài liệu ({checkpoints.filter((c) => c.is_passed).length}/{checkpoints.length} đã đạt)
          </h4>
        </div>

        <MmButton
          variant={allBlockingPassed ? "primary" : "secondary"}
          size="sm"
          disabled={!allBlockingPassed || completing || isCompleted}
          onClick={onCompleteMaterial}
        >
          {completing ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : isCompleted ? (
            <CheckCircle2 className="h-3.5 w-3.5" />
          ) : !allBlockingPassed ? (
            <Lock className="h-3.5 w-3.5" />
          ) : null}
          <span>
            {isCompleted
              ? "Đã hoàn thành"
              : allBlockingPassed
              ? "Xác nhận hoàn thành tài liệu"
              : "Hoàn thành câu hỏi bắt buộc để mở khóa"}
          </span>
        </MmButton>
      </div>

      {checkpoints.length === 0 ? (
        <p className="text-xs text-mm-text-muted">
          Tài liệu này không có câu hỏi kiểm tra. Bạn có thể bấm nút xác nhận hoàn thành ở góc phải.
        </p>
      ) : (
        <div className="space-y-3">
          {checkpoints.map((chk, idx) => {
            const fb = feedbackMap[chk.id];
            return (
              <div
                key={chk.id}
                className={`rounded-mm border p-3.5 ${
                  chk.is_passed
                    ? "border-emerald-500/40 bg-emerald-500/5"
                    : "border-mm-border bg-mm-bg/40"
                }`}
              >
                <div className="mb-2 flex items-center justify-between gap-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="rounded bg-mm-brand/10 px-2 py-0.5 font-semibold text-mm-brand">
                      Câu {idx + 1} • Mục {chk.section_index ?? 1}
                    </span>
                    <span
                      className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${
                        chk.is_blocking ? "bg-red-500/10 text-red-600" : "bg-slate-500/10 text-slate-500"
                      }`}
                    >
                      {chk.is_blocking ? "Bắt buộc" : "Tùy chọn"}
                    </span>
                  </div>
                  {chk.is_passed && (
                    <span className="inline-flex items-center gap-1 font-medium text-emerald-600">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Đã đạt
                    </span>
                  )}
                </div>

                <p className="mb-2.5 text-sm font-medium text-mm-heading">{chk.question_text}</p>

                <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2">
                  {Object.entries(chk.options || {}).map(([key, val]) => (
                    <label
                      key={key}
                      className={`flex cursor-pointer items-start gap-2 rounded border px-3 py-2 text-xs transition-colors ${
                        selectedMap[chk.id] === key
                          ? "border-mm-brand bg-mm-brand/10 text-mm-heading"
                          : "border-mm-border bg-mm-surface text-mm-text hover:bg-mm-surface-alt/40"
                      }`}
                    >
                      <input
                        type="radio"
                        name={`chk-${chk.id}`}
                        checked={selectedMap[chk.id] === key}
                        disabled={Boolean(chk.is_passed)}
                        onChange={() => setSelectedMap((p) => ({ ...p, [chk.id]: key }))}
                      />
                      <span>
                        <strong>{key}.</strong> {val}
                      </span>
                    </label>
                  ))}
                </div>

                {!chk.is_passed && (
                  <div className="mt-2.5 flex items-center justify-between gap-2">
                    <div>
                      {fb && !fb.ok && (
                        <span className="inline-flex items-center gap-1 text-xs text-amber-600">
                          <AlertTriangle className="h-3.5 w-3.5" />
                          Chưa chính xác! Hãy đọc lại nội dung và thử lại.
                        </span>
                      )}
                    </div>
                    <MmButton
                      variant="secondary"
                      size="sm"
                      disabled={submittingId === chk.id}
                      onClick={() => handleSubmitOne(chk)}
                    >
                      {submittingId === chk.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
                      <span>Kiểm tra đáp án</span>
                    </MmButton>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
