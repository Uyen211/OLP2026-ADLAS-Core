/*
 * Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
 * SPDX-License-Identifier: MIT
 */

import React from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { clsx } from "clsx";

import type { SpeedGraderWorkspaceResponse } from "../../../../types/gradebook";
import { MarkdownRenderer } from "../../components/MarkdownRenderer";

interface VivaEvidenceColumnProps {
  workspace: SpeedGraderWorkspaceResponse;
  highlightedRef: string | null;
}

const countWords = (text: string): number => {
  const trimmed = text.trim();
  return trimmed ? trimmed.split(/\s+/).length : 0;
};

export const VivaEvidenceColumn: React.FC<VivaEvidenceColumnProps> = ({
  workspace,
  highlightedRef,
}) => {
  const isRefHighlighted = (qIndex: number): boolean => {
    if (!highlightedRef) return false;
    const normalized = highlightedRef.toLowerCase();
    return (
      normalized.includes(`q${qIndex}`) ||
      normalized.includes(`câu ${qIndex}`) ||
      normalized.includes(`question ${qIndex}`)
    );
  };

  return (
    <div className="flex h-full flex-col rounded-2xl border border-[#e5e7eb] bg-white shadow-xs">
      {/* Column 2 Header */}
      <div className="border-b border-[#f3f4f6] px-4 py-3 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <Sparkles className="h-4 w-4 text-mm-blue-primary shrink-0" />
          <h2 className="font-mm-display text-sm font-bold text-mm-dark truncate">
            2. Hồ sơ AI Digest & Biên bản Viva
          </h2>
        </div>
        <span className="rounded-full bg-gray-100 px-2.5 py-0.5 font-mm-mono text-[10px] font-semibold text-mm-dark shrink-0">
          {workspace.viva_status || "CHƯA VIVA"}
        </span>
      </div>

      {/* Scrollable Evidence Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* E-SPEED-01 Missing Viva Banner */}
        {workspace.missing_viva && (
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 flex items-start gap-2.5">
            <AlertTriangle className="h-4 w-4 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <p className="font-bold">
                Thiếu biên bản Vấn đáp Viva (E-SPEED-01)
              </p>
              <p className="mt-0.5 text-[11px] leading-relaxed">
                Sinh viên chưa hoàn thành phiên kiểm chứng Viva cho phiên bản bài nộp này. Hãy cân nhắc yêu cầu sinh viên bổ sung hoặc áp dụng chế độ chấm thủ công.
              </p>
            </div>
          </div>
        )}

        {/* Integrity Logs Summary Card */}
        <div
          className={clsx(
            "rounded-xl border p-3.5 text-xs space-y-2",
            workspace.violation_logs.length > 0 ||
              workspace.window_blur_count > 0 ||
              workspace.paste_attempt_count > 0
              ? "border-rose-200 bg-rose-50/70"
              : "border-[#a7f3d0] bg-[#ecfdf5]/60"
          )}
        >
          <div className="flex items-center justify-between gap-2">
            <span className="inline-flex items-center gap-1.5 font-bold text-mm-dark">
              <ShieldAlert
                className={clsx(
                  "h-3.5 w-3.5",
                  workspace.violation_logs.length > 0 ? "text-rose-600" : "text-[#047857]"
                )}
              />
              Liêm chính Vấn đáp
            </span>
            <div className="flex items-center gap-2 font-mm-mono text-[10px]">
              <span className="rounded-full bg-white px-2 py-0.5 border border-[#e5e7eb]">
                Rời tab: {workspace.window_blur_count}
              </span>
              <span className="rounded-full bg-white px-2 py-0.5 border border-[#e5e7eb]">
                Dán văn bản: {workspace.paste_attempt_count}
              </span>
            </div>
          </div>

          {workspace.violation_logs.length > 0 ? (
            <div className="space-y-1 max-h-28 overflow-y-auto pr-1">
              {workspace.violation_logs.map((log, idx) => (
                <div
                  key={`${log.type}-${idx}`}
                  className="flex items-center justify-between rounded-md bg-white/80 px-2.5 py-1 text-[11px] text-rose-800"
                >
                  <span className="font-semibold">{log.type}</span>
                  <span className="font-mm-mono text-[10px]">
                    {log.timestamp ? new Date(log.timestamp).toLocaleTimeString("vi-VN") : ""}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-[#047857]">
              Không phát hiện vi phạm rời màn hình hay cố tình dán văn bản trong phiên Viva.
            </p>
          )}
        </div>

        {/* Call-1 Saved AI Digest */}
        <div className="rounded-xl border border-[#e5e7eb] bg-[#fafafa] p-3.5 space-y-2">
          <div className="flex flex-wrap items-center justify-between gap-1.5 border-b border-[#e5e7eb] pb-2">
            <span className="text-xs font-bold text-mm-dark">
              Bản tóm tắt nội dung bài nộp (Call 1 AI Digest)
            </span>
            <div className="flex flex-wrap gap-1 font-mm-mono text-[10px]">
              {workspace.digest_type && (
                <span className="rounded bg-[#eff6ff] px-1.5 py-0.5 text-[#1e40af]">
                  {workspace.digest_type}
                </span>
              )}
              {workspace.generation_source && (
                <span className="rounded bg-gray-200 px-1.5 py-0.5 text-[#374151]">
                  {workspace.generation_source}
                </span>
              )}
            </div>
          </div>

          {workspace.ai_digest_summary ? (
            <div className="prose prose-xs max-w-none text-xs text-[#1f2937] max-h-64 overflow-y-auto pr-1">
              <MarkdownRenderer content={workspace.ai_digest_summary} />
            </div>
          ) : (
            <p className="text-[11px] text-[#6b7280] italic">
              Chưa có bản tóm tắt AI Digest lưu trong CSDL cho bài nộp này.
            </p>
          )}
        </div>

        {/* N Viva Q&A Transcript */}
        <div className="space-y-2.5">
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="h-4 w-4 text-[#047857]" />
            <h3 className="font-mm-display text-xs font-bold text-mm-dark">
              Biên bản Hỏi - Đáp Viva ({workspace.questions.length} câu)
            </h3>
          </div>

          {workspace.questions.length === 0 ? (
            <div className="rounded-xl border border-dashed border-[#d1d5db] bg-[#f9fafb] p-4 text-center text-xs text-[#6b7280]">
              Chưa có câu hỏi Viva nào được sinh cho bài nộp này.
            </div>
          ) : (
            workspace.questions.map((q) => {
              const ans = workspace.answers[q.id];
              const words = ans?.answer_text ? countWords(ans.answer_text) : 0;
              const highlighted = isRefHighlighted(q.question_index);
              return (
                <div
                  key={q.id}
                  className={clsx(
                    "rounded-xl border p-3.5 space-y-2 transition-all",
                    highlighted
                      ? "border-amber-400 bg-amber-50/70 ring-2 ring-amber-200"
                      : "border-[#e5e7eb] bg-white"
                  )}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mm-mono text-[11px] font-bold text-mm-blue-primary">
                      Câu {q.question_index}/{q.total_questions || workspace.questions.length}
                      {q.category ? ` (${q.category})` : ""}
                    </span>
                    {ans && (
                      <div className="flex items-center gap-2 text-[10px] text-[#6b7280]">
                        <span>{words} từ</span>
                        {typeof ans.time_spent_seconds === "number" && (
                          <span className="inline-flex items-center gap-0.5">
                            <Clock className="h-3 w-3" />
                            {ans.time_spent_seconds}s
                          </span>
                        )}
                        {ans.auto_saved_on_timeout && (
                          <span className="rounded-full bg-amber-100 px-2 py-0.5 font-semibold text-amber-800">
                            Hết giờ (Tự lưu)
                          </span>
                        )}
                      </div>
                    )}
                  </div>

                  <p className="text-xs font-semibold text-mm-dark leading-relaxed">
                    {q.question_text}
                  </p>

                  <div className="rounded-lg border border-[#f3f4f6] bg-[#f9fafb] p-2.5 text-xs text-[#374151] whitespace-pre-wrap leading-relaxed">
                    {ans?.answer_text ? (
                      ans.answer_text
                    ) : (
                      <span className="italic text-[#9ca3af]">
                        Sinh viên chưa nhập câu trả lời cho câu hỏi này.
                      </span>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
