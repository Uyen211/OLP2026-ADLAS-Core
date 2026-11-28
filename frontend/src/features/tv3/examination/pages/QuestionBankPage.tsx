// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Sparkles, Layers } from "lucide-react";
import {
  EduBadge,
  EduButton,
  EduCard,
  EduEmptyState,
  PageHeader,
  SplitPaneWorkspace,
} from "../../../../design-system";
import { QuestionFolderTree } from "../components/QuestionFolderTree";
import { OneClickExtractorWizard } from "../components/OneClickExtractorWizard";
import { examinationService } from "../../../../services/examinationService";
import type {
  QuestionBankResponse,
  QuestionFolderResponse,
  QuestionFolderStatsResponse,
  QuestionResponse,
} from "../../../../types/examination";

export const QuestionBankPage: React.FC = () => {
  const { courseId } = useParams<{ courseId: string }>();

  const [banks, setBanks] = useState<QuestionBankResponse[]>([]);
  const [folders, setFolders] = useState<QuestionFolderResponse[]>([]);
  const [stats, setStats] = useState<QuestionFolderStatsResponse | undefined>();
  const [questions, setQuestions] = useState<QuestionResponse[]>([]);
  const [selectedFolderId, setSelectedFolderId] = useState<string | null>(null);

  const [showExtractorWizard, setShowExtractorWizard] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const loadAll = async () => {
    if (!courseId) return;
    setIsLoading(true);
    try {
      const [bList, fList, sData] = await Promise.all([
        examinationService.listQuestionBanks(courseId).catch(() => []),
        examinationService.listQuestionFolders(courseId).catch(() => []),
        examinationService.getQuestionFolderStats(courseId).catch(() => undefined),
      ]);
      setBanks(bList);
      setFolders(fList);
      setStats(sData);

      // Load questions if banks exist
      if (bList.length > 0) {
        const qList = await examinationService
          .listQuestions(courseId, { bank_id: bList[0].id })
          .catch(() => []);
        setQuestions(qList);
      }
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAll();
  }, [courseId]);

  const handleCreateFolder = async (name: string, parentId?: string | null) => {
    if (!courseId) return;
    await examinationService.createQuestionFolder(courseId, {
      folder_name: name,
      parent_folder_id: parentId,
    });
    await loadAll();
  };

  const handleDeleteFolder = async (folderId: string) => {
    await examinationService.deleteQuestionFolder(folderId);
    if (selectedFolderId === folderId) setSelectedFolderId(null);
    await loadAll();
  };

  const filteredQuestions = selectedFolderId
    ? questions.filter((q) => q.folder_id === selectedFolderId)
    : questions;

  return (
    <div className="w-full max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <PageHeader
        breadcrumbs={[
          { label: "Môn học", href: "/courses" },
          { label: "Kiểm tra & Đánh giá", href: `/courses/${courseId}/exams` },
          { label: "Ngân hàng câu hỏi & Thư mục" },
        ]}
        title="Ngân hàng câu hỏi Đa cấp & Trích xuất 1-Click"
        description="Quản lý cấu trúc thư mục chương mục, phân loại độ khó câu hỏi và tự động trích xuất đề thi từ tệp DOCX/PDF bằng AI."
        actions={
          <div className="flex items-center gap-2">
            <EduButton
              variant="primary"
              onClick={() => setShowExtractorWizard(true)}
            >
              <Sparkles className="w-4 h-4 mr-2" />
              <span>Trích xuất đề thi 1-Click (AI)</span>
            </EduButton>
          </div>
        }
      />

      {showExtractorWizard ? (
        <OneClickExtractorWizard
          courseId={courseId || ""}
          banks={banks}
          folders={folders}
          onComplete={() => {
            setShowExtractorWizard(false);
            loadAll();
          }}
          onCancel={() => setShowExtractorWizard(false)}
        />
      ) : (
        <SplitPaneWorkspace
          leftPane={
            <QuestionFolderTree
              folders={folders}
              selectedFolderId={selectedFolderId}
              stats={stats}
              onSelectFolder={setSelectedFolderId}
              onCreateFolder={handleCreateFolder}
              onDeleteFolder={handleDeleteFolder}
            />
          }
          rightPane={
            <div className="space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-[rgba(15,34,54,0.08)]">
                <div className="flex items-center gap-2 text-sm font-bold text-[#0f2236]">
                  <Layers className="w-4 h-4 text-[#006699]" />
                  <span>
                    {selectedFolderId
                      ? folders.find((f) => f.id === selectedFolderId)?.folder_name ||
                        "Thư mục đã chọn"
                      : "Tất cả câu hỏi trong ngân hàng"}
                  </span>
                  <span className="text-xs font-mono font-normal text-[#4a5f75]">
                    ({filteredQuestions.length} câu)
                  </span>
                </div>
              </div>

              {isLoading ? (
                <div className="py-12 text-center text-sm text-[#4a5f75]">
                  Đang tải câu hỏi ngân hàng...
                </div>
              ) : filteredQuestions.length === 0 ? (
                <EduEmptyState
                  title="Chưa có câu hỏi nào trong thư mục này"
                  description="Hãy bấm 'Trích xuất đề thi 1-Click (AI)' hoặc tải câu hỏi mới vào thư mục để bắt đầu."
                  actionLabel="Trích xuất ngay"
                  onAction={() => setShowExtractorWizard(true)}
                />
              ) : (
                <div className="space-y-3">
                  {filteredQuestions.map((q, idx) => (
                    <EduCard
                      key={q.id}
                      variant="surface"
                      padding="md"
                      className="border border-[rgba(15,34,54,0.1)] space-y-2"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <span className="w-6 h-6 rounded-full bg-[#f5fbfd] border border-[rgba(15,34,54,0.15)] text-[#0f2236] text-xs font-bold flex items-center justify-center">
                            {idx + 1}
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
                          <span className="text-xs font-mono text-[#4a5f75]">
                            {q.default_points} điểm
                          </span>
                        </div>
                      </div>

                      <p className="text-sm font-semibold text-[#0f2236] pl-8">
                        {q.question_text}
                      </p>

                      <div className="pl-8 grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1 text-xs">
                        {q.options.map((opt) => (
                          <div
                            key={opt.key}
                            className={`p-2 rounded-lg border ${
                              opt.is_correct
                                ? "bg-[#ecfdf5] border-[#a7f3d0] font-semibold text-[#15803d]"
                                : "bg-white border-[rgba(15,34,54,0.08)] text-[#4a5f75]"
                            }`}
                          >
                            <span className="font-bold mr-1.5">{opt.key}.</span>
                            {opt.text}
                          </div>
                        ))}
                      </div>
                    </EduCard>
                  ))}
                </div>
              )}
            </div>
          }
        />
      )}
    </div>
  );
};
