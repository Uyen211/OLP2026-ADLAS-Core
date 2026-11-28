// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React from "react";
import { Trash2, Plus, CheckCircle2 } from "lucide-react";
import { EduBadge, EduCard } from "../../../../design-system";
import type { ExtractedQuestionDraft, QuestionOption } from "../../../../types/examination";

export interface StagingQuestionEditorProps {
  questions: ExtractedQuestionDraft[];
  onChange: (questions: ExtractedQuestionDraft[]) => void;
}

export const StagingQuestionEditor: React.FC<StagingQuestionEditorProps> = ({
  questions,
  onChange,
}) => {
  const handleUpdateField = (
    index: number,
    field: keyof ExtractedQuestionDraft,
    value: any
  ) => {
    const next = [...questions];
    next[index] = { ...next[index], [field]: value };
    onChange(next);
  };

  const handleDeleteQuestion = (index: number) => {
    const next = questions.filter((_, i) => i !== index);
    onChange(next);
  };

  const handleUpdateOption = (
    qIndex: number,
    optIndex: number,
    field: keyof QuestionOption,
    value: any
  ) => {
    const next = [...questions];
    const opts = [...next[qIndex].options];
    opts[optIndex] = { ...opts[optIndex], [field]: value };

    // Nếu đánh dấu là đáp án đúng
    if (field === "is_correct" && value === true) {
      opts.forEach((o, i) => {
        if (i !== optIndex) o.is_correct = false;
      });
      next[qIndex].correct_key = opts[optIndex].key;
    }

    next[qIndex].options = opts;
    onChange(next);
  };

  const handleAddOption = (qIndex: number) => {
    const next = [...questions];
    const opts = next[qIndex].options;
    const nextKey = String.fromCharCode(65 + opts.length); // A, B, C, D, E...
    next[qIndex].options = [
      ...opts,
      { key: nextKey, text: "", is_correct: false },
    ];
    onChange(next);
  };

  const handleDeleteOption = (qIndex: number, optIndex: number) => {
    const next = [...questions];
    if (next[qIndex].options.length <= 2) return; // Giữ tối thiểu 2 phương án
    next[qIndex].options = next[qIndex].options.filter((_, i) => i !== optIndex);
    onChange(next);
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-xs font-semibold text-[#4a5f75] px-1">
        <span>Tổng cộng {questions.length} câu hỏi được trích xuất thành công</span>
        <span>Bạn có thể chỉnh sửa nội dung, đáp án trước khi lưu</span>
      </div>

      {questions.map((q, qIdx) => (
        <EduCard
          key={qIdx}
          variant="surface"
          padding="md"
          className="border border-[rgba(15,34,54,0.12)] space-y-3"
        >
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-[#006699] text-white text-xs font-bold flex items-center justify-center shrink-0">
                {qIdx + 1}
              </span>
              <EduBadge
                variant={
                  q.difficulty === "easy"
                    ? "correct"
                    : q.difficulty === "hard"
                    ? "incorrect"
                    : "hint"
                }
                label={
                  q.difficulty === "easy"
                    ? "Dễ"
                    : q.difficulty === "hard"
                    ? "Khó"
                    : "Trung bình"
                }
              />
              <span className="text-xs text-[#4a5f75] font-mono">
                Độ tin cậy AI: {Math.round((q.confidence_score || 1) * 100)}%
              </span>
            </div>

            <div className="flex items-center gap-2">
              <select
                value={q.difficulty}
                onChange={(e) => handleUpdateField(qIdx, "difficulty", e.target.value)}
                className="text-xs rounded-lg border border-[rgba(15,34,54,0.15)] px-2 py-1 bg-white text-[#0f2236]"
              >
                <option value="easy">Dễ (Easy)</option>
                <option value="medium">Trung bình (Medium)</option>
                <option value="hard">Khó (Hard)</option>
              </select>

              <button
                type="button"
                onClick={() => handleDeleteQuestion(qIdx)}
                className="p-1 text-[#b91c1c] hover:bg-rose-50 rounded"
                title="Xóa câu hỏi này"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Nội dung câu hỏi */}
          <div>
            <textarea
              rows={2}
              value={q.prompt}
              onChange={(e) => handleUpdateField(qIdx, "prompt", e.target.value)}
              placeholder="Nội dung câu hỏi..."
              className="w-full rounded-xl border border-[rgba(15,34,54,0.16)] px-3 py-2 text-sm text-[#0f2236] bg-[#f5fbfd] font-medium"
            />
          </div>

          {/* Danh sách phương án trả lời */}
          <div className="space-y-2">
            <div className="text-xs font-bold text-[#0f2236]">Các phương án trả lời:</div>
            {q.options.map((opt, oIdx) => {
              const isCorrect = opt.key === q.correct_key || opt.is_correct;

              return (
                <div
                  key={oIdx}
                  className={`flex items-center gap-2 p-2 rounded-xl border transition-colors ${
                    isCorrect
                      ? "bg-[#ecfdf5] border-[#a7f3d0]"
                      : "bg-white border-[rgba(15,34,54,0.1)]"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => handleUpdateOption(qIdx, oIdx, "is_correct", true)}
                    className={`w-6 h-6 rounded-full text-xs font-bold flex items-center justify-center shrink-0 transition-colors ${
                      isCorrect
                        ? "bg-[#15803d] text-white"
                        : "bg-[#eaf6fa] text-[#006699] hover:bg-[#7fbbdd]/40"
                    }`}
                    title={isCorrect ? "Đáp án đúng" : "Bấm để chọn làm đáp án đúng"}
                  >
                    {isCorrect ? <CheckCircle2 className="w-4 h-4" /> : opt.key}
                  </button>

                  <input
                    type="text"
                    value={opt.text}
                    onChange={(e) => handleUpdateOption(qIdx, oIdx, "text", e.target.value)}
                    placeholder={`Nội dung phương án ${opt.key}...`}
                    className="flex-1 text-sm bg-transparent border-none focus:outline-none text-[#0f2236]"
                  />

                  {q.options.length > 2 && (
                    <button
                      type="button"
                      onClick={() => handleDeleteOption(qIdx, oIdx)}
                      className="p-1 text-[#4a5f75] hover:text-[#b91c1c]"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              );
            })}

            <div className="pt-1">
              <button
                type="button"
                onClick={() => handleAddOption(qIdx)}
                className="inline-flex items-center gap-1 text-xs text-[#006699] font-semibold hover:underline"
              >
                <Plus className="w-3 h-3" />
                <span>Thêm phương án</span>
              </button>
            </div>
          </div>

          {/* Giải thích chi tiết */}
          <div>
            <input
              type="text"
              value={q.explanation || ""}
              onChange={(e) => handleUpdateField(qIdx, "explanation", e.target.value)}
              placeholder="Giải thích đáp án (tùy chọn)..."
              className="w-full text-xs text-[#4a5f75] bg-transparent border-b border-[rgba(15,34,54,0.1)] py-1 focus:outline-none focus:border-[#006699]"
            />
          </div>
        </EduCard>
      ))}
    </div>
  );
};
