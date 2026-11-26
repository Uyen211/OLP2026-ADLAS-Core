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
    <div className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-3.5">
        <div className="flex items-center gap-2">
          <HelpCircle className="h-4 w-4 text-blue-600" />
          <h4 className="text-sm font-bold text-slate-900">
            Kiểm tra mức độ hiểu tài liệu ({checkpoints.filter((c) => c.is_passed).length}/{checkpoints.length} đã đạt)
          </h4>
        </div>

        <MmButton
          variant={allBlockingPassed ? "brand" : "secondary"}
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
        <p className="text-xs text-slate-500">
          Tài liệu này không có câu hỏi kiểm tra. Bạn có thể bấm nút xác nhận hoàn thành ở góc phải.
        </p>
      ) : (
        <div className="space-y-3">
          {checkpoints.map((chk, idx) => {
            const fb = feedbackMap[chk.id];
            return (
              <div
                key={chk.id}
                className={`rounded-xl border p-4 transition-all ${
                  chk.is_passed
                    ? "border-emerald-200 bg-emerald-50/40"
                    : "border-slate-200 bg-white shadow-2xs hover:border-slate-300"
                }`}
              >
                <div className="mb-2.5 flex items-center justify-between gap-2 text-xs">
                  <div className="flex items-center gap-2">
                    <span className="rounded-md bg-blue-50 border border-blue-100 px-2 py-0.5 font-mono text-xs font-bold text-blue-600">
                      Câu {idx + 1} • Mục {chk.section_index ?? 1}
                    </span>
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-semibold ${
                        chk.is_blocking
                          ? "bg-rose-50 border border-rose-200 text-rose-700"
                          : "bg-slate-100 border border-slate-200 text-slate-600"
                      }`}
                    >
                      {chk.is_blocking ? "Bắt buộc" : "Tùy chọn"}
                    </span>
                  </div>
                  {chk.is_passed && (
                    <span className="inline-flex items-center gap-1 font-semibold text-emerald-600">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Đã đạt
                    </span>
                  )}
                </div>

                <p className="mb-3 text-sm font-semibold text-slate-900 leading-snug">{chk.question_text}</p>

                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {Object.entries(chk.options || {}).map(([key, val]) => (
                    <label
                      key={key}
                      className={`flex cursor-pointer items-start gap-2.5 rounded-lg border p-2.5 text-xs transition-all ${
                        selectedMap[chk.id] === key
                          ? "border-blue-500 bg-blue-50/80 text-blue-900 ring-1 ring-blue-500 font-medium"
                          : "border-slate-200 bg-slate-50/60 text-slate-700 hover:border-slate-300 hover:bg-slate-100/60"
                      }`}
                    >
                      <input
                        type="radio"
                        name={`chk-${chk.id}`}
                        checked={selectedMap[chk.id] === key}
                        disabled={Boolean(chk.is_passed)}
                        onChange={() => setSelectedMap((p) => ({ ...p, [chk.id]: key }))}
                        className="mt-0.5"
                      />
                      <span>
                        <strong className="text-slate-900">{key}.</strong> {val}
                      </span>
                    </label>
                  ))}
                </div>

                {!chk.is_passed && (
                  <div className="mt-3 flex items-center justify-between gap-2 border-t border-slate-100 pt-2.5">
                    <div>
                      {fb && !fb.ok && (
                        <span className="inline-flex items-center gap-1 text-xs font-medium text-rose-600">
                          <AlertTriangle className="h-3.5 w-3.5" />
                          Chưa chính xác! Hãy đọc lại nội dung và thử lại.
                        </span>
                      )}
                    </div>
                    <MmButton
                      variant="brand"
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
