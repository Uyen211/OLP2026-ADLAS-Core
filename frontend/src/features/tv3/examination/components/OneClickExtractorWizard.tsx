// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useState } from "react";
import { UploadCloud, FileText, ArrowRight, ArrowLeft, Save, Sparkles, AlertCircle } from "lucide-react";
import { EduButton, EduCard, StepProgressRail, type StepItem } from "../../../../design-system";
import { StagingQuestionEditor } from "./StagingQuestionEditor";
import { examinationService } from "../../../../services/examinationService";
import type {
  ExtractedQuestionDraft,
  QuestionBankResponse,
  QuestionFolderResponse,
} from "../../../../types/examination";

export interface OneClickExtractorWizardProps {
  courseId: string;
  banks: QuestionBankResponse[];
  folders: QuestionFolderResponse[];
  onComplete: () => void;
  onCancel: () => void;
}

export const OneClickExtractorWizard: React.FC<OneClickExtractorWizardProps> = ({
  courseId,
  banks,
  folders,
  onComplete,
  onCancel,
}) => {
  const [currentStep, setCurrentStep] = useState(1);
  const [inputMode, setInputMode] = useState<"upload" | "text">("upload");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [rawText, setRawText] = useState("");

  const [extractedQuestions, setExtractedQuestions] = useState<ExtractedQuestionDraft[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Lưu cấu hình đích
  const [targetBankId, setTargetBankId] = useState<string>(banks[0]?.id || "");
  const [targetFolderId, setTargetFolderId] = useState<string>("");

  const steps: StepItem[] = [
    { id: 1, title: "Nguồn dữ liệu", description: "Tải lên DOCX/PDF hoặc dán text" },
    { id: 2, title: "Kiểm duyệt câu hỏi", description: "Chỉnh sửa câu hỏi & đáp án AI" },
    { id: 3, title: "Lưu vào ngân hàng", description: "Chọn danh mục & thư mục lưu" },
  ];

  const handleExtract = async () => {
    setIsProcessing(true);
    setErrorMsg(null);
    try {
      let preview;
      if (inputMode === "upload") {
        if (!selectedFile) {
          setErrorMsg("Vui lòng chọn một tệp DOCX hoặc PDF để trích xuất.");
          return;
        }
        preview = await examinationService.extractQuestionsFromUpload(courseId, selectedFile);
      } else {
        if (!rawText.trim()) {
          setErrorMsg("Vui lòng nhập hoặc dán nội dung văn bản câu hỏi.");
          return;
        }
        preview = await examinationService.extractQuestionsFromText(courseId, rawText.trim());
      }

      if (!preview.questions || preview.questions.length === 0) {
        setErrorMsg("Không tìm thấy câu hỏi trắc nghiệm hợp lệ nào trong nội dung.");
        return;
      }

      setExtractedQuestions(preview.questions);
      setCurrentStep(2);
    } catch (err: any) {
      setErrorMsg(err?.message || "Lỗi trong quá trình trích xuất câu hỏi.");
    } finally {
      setIsProcessing(false);
    }
  };

  const handleBatchSave = async () => {
    if (!targetBankId) {
      setErrorMsg("Vui lòng chọn ngân hàng câu hỏi đích.");
      return;
    }
    if (extractedQuestions.length === 0) {
      setErrorMsg("Không có câu hỏi nào để lưu.");
      return;
    }

    setIsProcessing(true);
    setErrorMsg(null);
    try {
      await examinationService.batchSaveQuestions(courseId, {
        bank_id: targetBankId,
        folder_id: targetFolderId ? targetFolderId : null,
        questions: extractedQuestions,
      });
      onComplete();
    } catch (err: any) {
      setErrorMsg(err?.message || "Không thể lưu câu hỏi vào ngân hàng.");
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      <StepProgressRail steps={steps} currentStepIndex={currentStep - 1} />

      {errorMsg && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-[#fff1f2] border border-[#fecdd3] text-[#be123c] text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Bước 1: Chọn nguồn dữ liệu */}
      {currentStep === 1 && (
        <EduCard variant="surface" padding="lg" className="space-y-5">
          <div className="flex gap-3 border-b border-[rgba(15,34,54,0.08)] pb-3">
            <button
              type="button"
              onClick={() => setInputMode("upload")}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
                inputMode === "upload"
                  ? "bg-[#006699] text-white"
                  : "text-[#4a5f75] hover:bg-[#f5fbfd]"
              }`}
            >
              <UploadCloud className="w-4 h-4" />
              <span>Tải file (PDF, DOCX)</span>
            </button>
            <button
              type="button"
              onClick={() => setInputMode("text")}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-semibold transition-colors ${
                inputMode === "text"
                  ? "bg-[#006699] text-white"
                  : "text-[#4a5f75] hover:bg-[#f5fbfd]"
              }`}
            >
              <FileText className="w-4 h-4" />
              <span>Dán văn bản trực tiếp</span>
            </button>
          </div>

          {inputMode === "upload" ? (
            <div className="border-2 border-dashed border-[rgba(127,187,221,0.6)] rounded-2xl p-8 text-center bg-[#f5fbfd]">
              <UploadCloud className="w-12 h-12 text-[#006699] mx-auto mb-3" />
              <p className="text-sm font-bold text-[#0f2236]">
                Kéo thả file đề thi vào đây, hoặc bấm để duyệt file
              </p>
              <p className="text-xs text-[#4a5f75] mt-1 mb-4">
                Hỗ trợ định dạng .docx, .doc, .pdf (Dung lượng tối đa 15MB)
              </p>
              <input
                type="file"
                accept=".docx,.doc,.pdf"
                id="file-upload"
                className="hidden"
                onChange={(e) => {
                  if (e.target.files?.[0]) setSelectedFile(e.target.files[0]);
                }}
              />
              <label
                htmlFor="file-upload"
                className="inline-flex items-center px-4 py-2 rounded-xl bg-white border border-[rgba(15,34,54,0.15)] text-sm font-semibold text-[#0f2236] cursor-pointer hover:bg-[#eaf6fa]"
              >
                {selectedFile ? selectedFile.name : "Chọn tệp từ máy tính"}
              </label>
            </div>
          ) : (
            <div>
              <label className="block text-xs font-bold text-[#0f2236] mb-1.5">
                Nội dung câu hỏi trắc nghiệm:
              </label>
              <textarea
                rows={10}
                value={rawText}
                onChange={(e) => setRawText(e.target.value)}
                placeholder={`Câu 1: Thủ đô của Việt Nam là gì?\nA. Hà Nội\nB. TP. Hồ Chí Minh\nC. Đà Nẵng\nD. Huế\nĐáp án: A\n\nCâu 2: ...`}
                className="w-full rounded-xl border border-[rgba(15,34,54,0.16)] p-3 text-sm font-mono text-[#0f2236] bg-[#f5fbfd]"
              />
            </div>
          )}

          <div className="flex justify-between items-center pt-2">
            <EduButton variant="secondary" onClick={onCancel}>
              Hủy bỏ
            </EduButton>
            <EduButton
              variant="primary"
              onClick={handleExtract}
              disabled={isProcessing}
            >
              <Sparkles className="w-4 h-4 mr-2" />
              {isProcessing ? "Đang trích xuất AI..." : "Bắt đầu trích xuất"}
            </EduButton>
          </div>
        </EduCard>
      )}

      {/* Bước 2: Kiểm duyệt & chỉnh sửa câu hỏi */}
      {currentStep === 2 && (
        <div className="space-y-4">
          <StagingQuestionEditor
            questions={extractedQuestions}
            onChange={setExtractedQuestions}
          />
          <div className="flex justify-between items-center pt-2">
            <EduButton
              variant="secondary"
              onClick={() => setCurrentStep(1)}
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Quay lại nguồn
            </EduButton>
            <EduButton
              variant="primary"
              onClick={() => setCurrentStep(3)}
              disabled={extractedQuestions.length === 0}
            >
              <span>Tiếp tục chọn thư mục lưu</span>
              <ArrowRight className="w-4 h-4 ml-2" />
            </EduButton>
          </div>
        </div>
      )}

      {/* Bước 3: Chọn ngân hàng & thư mục đích */}
      {currentStep === 3 && (
        <EduCard variant="surface" padding="lg" className="space-y-5">
          <h3 className="text-base font-bold text-[#0f2236]">
            Xác nhận vị trí lưu cho {extractedQuestions.length} câu hỏi
          </h3>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-bold text-[#0f2236] mb-1">
                Ngân hàng câu hỏi <span className="text-[#be123c]">*</span>
              </label>
              <select
                value={targetBankId}
                onChange={(e) => setTargetBankId(e.target.value)}
                className="w-full rounded-xl border border-[rgba(15,34,54,0.16)] px-3 py-2 text-sm text-[#0f2236] bg-[#f5fbfd]"
              >
                {banks.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.category_name} ({b.question_count} câu hiện có)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-bold text-[#0f2236] mb-1">
                Thư mục đích (tùy chọn)
              </label>
              <select
                value={targetFolderId}
                onChange={(e) => setTargetFolderId(e.target.value)}
                className="w-full rounded-xl border border-[rgba(15,34,54,0.16)] px-3 py-2 text-sm text-[#0f2236] bg-[#f5fbfd]"
              >
                <option value="">(Không đưa vào thư mục cụ thể)</option>
                {folders.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.folder_name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex justify-between items-center pt-2">
            <EduButton
              variant="secondary"
              onClick={() => setCurrentStep(2)}
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Quay lại chỉnh sửa
            </EduButton>
            <EduButton
              variant="primary"
              onClick={handleBatchSave}
              disabled={isProcessing}
            >
              <Save className="w-4 h-4 mr-2" />
              {isProcessing ? "Đang lưu..." : `Lưu ${extractedQuestions.length} câu hỏi`}
            </EduButton>
          </div>
        </EduCard>
      )}
    </div>
  );
};
