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
  return (
    <div className="flex h-full flex-col rounded-2xl border border-[#e5e7eb] bg-white shadow-xs">
      {/* Column 2 Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#f3f4f6] px-4 py-3">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-mm-blue-primary" />
          <h2 className="font-mm-display text-sm font-bold text-mm-dark">
            2. Tóm tắt AI & Bằng chứng Viva
          </h2>
        </div>
        <span className="rounded-full bg-gray-100 px-2.5 py-0.5 font-mm-mono text-[10px] font-semibold text-mm-dark">
          {workspace.viva_status || "CHƯA CÓ VIVA"}
        </span>
      </div>

      {/* Scrollable Body */}
      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        {/* E-SPEED-01 Missing Viva Banner */}
        {workspace.missing_viva && (
          <div className="rounded-xl border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 mt-0.5" />
            <div>
              <p className="font-bold">Cảnh báo thiếu biên bản Vấn đáp Viva (E-SPEED-01)</p>
              <p className="mt-0.5 text-[11px] leading-relaxed">
                Sinh viên chưa hoàn thành phiên Vấn đáp AI Viva hoặc bài tập không yêu cầu Viva. Giảng viên vẫn có thể chấm trực tiếp dựa trên sản phẩm bài nộp.
              </p>
            </div>
          </div>
        )}

        {/* Section A: Call-1 AI Digest */}
        <div className="rounded-xl border border-[#e5e7eb] bg-[#fafafa] p-3.5 space-y-2.5">
          <div className="flex flex-wrap items-center justify-between gap-1.5 border-b border-[#e5e7eb] pb-2">
            <span className="text-xs font-bold text-mm-dark">
              Bản tóm tắt nội dung bài nộp (Call 1)
            </span>
            <div className="flex flex-wrap gap-1 text-[10px] font-mm-mono">
              {workspace.digest_type && (
                <span className="rounded-full bg-[#eff6ff] px-2 py-0.5 font-semibold text-[#1e40af]">
                  {workspace.digest_type}
                </span>
              )}
              {workspace.summarizer_mode && (
                <span className="rounded-full bg-gray-200 px-2 py-0.5 text-[#374151]">
                  {workspace.summarizer_mode}
                </span>
              )}
            </div>
          </div>

          {workspace.ai_digest_summary ? (
            <div className="prose prose-xs max-w-none text-xs text-[#1f2937]">
              <MarkdownRenderer content={workspace.ai_digest_summary} />
            </div>
          ) : (
            <p className="text-xs italic text-[#6b7280]">
              Chưa có bản tóm tắt AI Call-1 cho bài nộp này.
            </p>
          )}
        </div>

        {/* Section B: Viva Q&A Transcript */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <span className="inline-flex items-center gap-1.5 text-xs font-bold text-mm-dark">
              <CheckCircle2 className="h-3.5 w-3.5 text-[#047857]" />
              Biên bản Hỏi-Đáp Viva ({workspace.questions.length} câu)
            </span>
          </div>

          {workspace.questions.length === 0 ? (
            <p className="rounded-xl border border-dashed border-[#d1d5db] p-3 text-xs text-[#6b7280]">
              Chưa có câu hỏi Viva nào được ghi nhận.
            </p>
          ) : (
            <div className="space-y-3">
              {workspace.questions.map((q) => {
                const ans = workspace.answers[q.id];
                const words = ans?.answer_text ? countWords(ans.answer_text) : 0;
                const isHighlighted =
                  highlightedRef !== null &&
                  (highlightedRef.toLowerCase().includes(`q${q.question_index}`) ||
                    highlightedRef.toLowerCase().includes(`câu ${q.question_index}`) ||
                    highlightedRef.toLowerCase().includes(q.id.toLowerCase()));

                return (
                  <div
                    key={q.id}
                    className={clsx(
                      "rounded-xl border p-3 space-y-2 transition-colors",
                      isHighlighted
                        ? "border-amber-400 bg-amber-50/70 ring-2 ring-amber-200"
                        : "border-[#e5e7eb] bg-white"
                    )}
                  >
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-mm-mono text-[11px] font-bold text-mm-blue-primary">
                        Câu {q.question_index} / {q.total_questions || workspace.questions.length}
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
                            <span className="rounded-full bg-amber-100 px-1.5 py-0.5 font-semibold text-amber-800">
                              Hết giờ
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
                          Sinh viên chưa gửi câu trả lời cho câu hỏi này.
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Section C: Integrity Violation Logs */}
        <div className="rounded-xl border border-[#e5e7eb] bg-white p-3.5 space-y-2.5">
          <div className="flex items-center justify-between border-b border-[#f3f4f6] pb-2">
            <span className="inline-flex items-center gap-1.5 text-xs font-bold text-mm-dark">
              <ShieldAlert className="h-3.5 w-3.5 text-rose-600" />
              Nhật ký Liêm chính ({workspace.violation_logs.length})
            </span>
            <div className="flex items-center gap-2 font-mm-mono text-[10px]">
              <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[#374151]">
                Blur: {workspace.window_blur_count}
              </span>
              <span className="rounded bg-gray-100 px-1.5 py-0.5 text-[#374151]">
                Paste: {workspace.paste_attempt_count}
              </span>
            </div>
          </div>

          {workspace.violation_logs.length > 0 ? (
            <div className="space-y-1.5">
              {workspace.violation_logs.map((log, idx) => (
                <div
                  key={`${log.type}-${idx}`}
                  className="flex items-center justify-between rounded-lg border border-rose-200 bg-rose-50 px-2.5 py-1.5 text-[11px] text-rose-800"
                >
                  <span className="font-semibold">{log.type}</span>
                  <span className="font-mm-mono text-[10px]">
                    {log.timestamp
                      ? new Date(log.timestamp).toLocaleTimeString("vi-VN")
                      : ""}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-[11px] text-[#047857]">
              Không phát hiện hành vi rời màn hình hay cố tình dán văn bản trong phiên Viva.
            </p>
          )}
        </div>
      </div>
    </div>
  );
};
