// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useState } from "react";
import { CheckCircle2, AlertCircle, Plus } from "lucide-react";
import { EduBadge, EduButton, EduCard, EduInput, EduModal } from "../../../../design-system";
import type { TopicResponse } from "../../../../types/assessment";
import { assessmentService } from "../../../../services/assessmentService";

export interface TopicSlotListProps {
  assignmentId: string;
  topics: TopicResponse[];
  currentTopicId?: string | null;
  groupId?: string | null;
  isLeader?: boolean;
  isInstructor?: boolean;
  onTopicSelected?: (topicId: string) => void;
  onTopicCreated?: (topic: TopicResponse) => void;
}

export const TopicSlotList: React.FC<TopicSlotListProps> = ({
  assignmentId,
  topics,
  currentTopicId,
  groupId,
  isLeader = false,
  isInstructor = false,
  onTopicSelected,
  onTopicCreated,
}) => {
  const [isSubmitting, setIsSubmitting] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newCode, setNewCode] = useState("");
  const [newTitle, setNewTitle] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newMax, setNewMax] = useState(1);
  const [isCreating, setIsCreating] = useState(false);

  const handleSelect = async (topicId: string) => {
    if (!groupId) {
      setErrorMsg("Bạn cần tham gia một nhóm trước khi chọn đề tài.");
      return;
    }
    if (!isLeader) {
      setErrorMsg("Chỉ nhóm trưởng mới có quyền đăng ký chọn đề tài dự án.");
      return;
    }

    setIsSubmitting(topicId);
    setErrorMsg(null);

    try {
      await assessmentService.selectGroupTopic(groupId, topicId);
      if (onTopicSelected) onTopicSelected(topicId);
    } catch (err: any) {
      if (err?.code === "E-GRP-01" || err?.status === 409) {
        setErrorMsg("Đề tài này vừa được nhóm khác đăng ký đủ chỗ. Vui lòng chọn đề tài khác.");
      } else {
        setErrorMsg(err?.message || "Không thể chọn đề tài lúc này. Vui lòng thử lại.");
      }
    } finally {
      setIsSubmitting(null);
    }
  };

  const handleCreateTopic = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCode.trim() || !newTitle.trim()) return;

    setIsCreating(true);
    try {
      const topic = await assessmentService.createTopic(assignmentId, {
        topic_code: newCode.trim().toUpperCase(),
        title: newTitle.trim(),
        description: newDesc.trim() || undefined,
        max_groups: newMax,
      });
      setIsCreateOpen(false);
      setNewCode("");
      setNewTitle("");
      setNewDesc("");
      if (onTopicCreated) onTopicCreated(topic);
    } catch (err: any) {
      alert("Không thể tạo đề tài: " + (err?.message || "Lỗi server"));
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="w-full flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-base sm:text-lg font-bold text-[#0f2236]">
            Danh mục Đề tài Đồ án
          </h3>
          <p className="text-xs sm:text-sm text-[#4a5f75] mt-0.5">
            Mỗi đề tài có giới hạn số lượng nhóm đăng ký để bảo đảm tính đa dạng.
          </p>
        </div>

        {isInstructor && (
          <EduButton
            variant="sky"
            size="sm"
            onClick={() => setIsCreateOpen(true)}
            leftIcon={<Plus className="w-4 h-4" aria-hidden="true" />}
          >
            Thêm đề tài
          </EduButton>
        )}
      </div>

      {errorMsg && (
        <div className="flex items-center gap-2 p-3 text-xs font-semibold text-[#b91c1c] bg-[#fef2f2] rounded-xl border border-[#b91c1c]/20 animate-edu-fade-in">
          <AlertCircle className="w-4 h-4 shrink-0" aria-hidden="true" />
          <span>{errorMsg}</span>
        </div>
      )}

      {topics.length === 0 ? (
        <div className="p-8 text-center text-sm text-[#4a5f75] bg-white rounded-2xl border border-dashed border-[rgba(15,34,54,0.15)]">
          Giảng viên chưa công bố đề tài đồ án cho bài tập này.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {topics.map((t) => {
            const isSelected = currentTopicId === t.id;
            const isFull = t.current_groups_count >= t.max_groups;

            return (
              <EduCard
                key={t.id}
                variant={isSelected ? "tint" : "surface"}
                padding="md"
                className={`flex flex-col justify-between transition-all ${
                  isSelected ? "ring-2 ring-[#7fbbdd]" : ""
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-2">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded-md bg-[#eaf6fa] text-[#0f2236] border border-[#7fbbdd]/40">
                      {t.topic_code}
                    </span>

                    <EduBadge
                      variant={isFull ? "incorrect" : "sky"}
                      label={`${t.current_groups_count} / ${t.max_groups} nhóm`}
                      showIcon={false}
                    />
                  </div>

                  <h4 className="text-sm sm:text-base font-bold text-[#0f2236] leading-snug">
                    {t.title}
                  </h4>

                  {t.description && (
                    <p className="text-xs text-[#4a5f75] mt-2 line-clamp-3 leading-relaxed">
                      {t.description}
                    </p>
                  )}
                </div>

                <div className="mt-4 pt-3 border-t border-[rgba(15,34,54,0.08)] flex items-center justify-between">
                  {isSelected ? (
                    <span className="flex items-center gap-1.5 text-xs font-bold text-[#15803d]">
                      <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
                      Nhóm bạn đã chọn đề tài này
                    </span>
                  ) : isFull ? (
                    <span className="text-xs font-medium text-[#b91c1c]">
                      Đã hết chỗ đăng ký
                    </span>
                  ) : isLeader ? (
                    <EduButton
                      variant="amber"
                      size="sm"
                      isLoading={isSubmitting === t.id}
                      onClick={() => handleSelect(t.id)}
                    >
                      Đăng ký đề tài
                    </EduButton>
                  ) : (
                    <span className="text-xs text-[#4a5f75]">
                      Chỉ nhóm trưởng mới có quyền chọn
                    </span>
                  )}
                </div>
              </EduCard>
            );
          })}
        </div>
      )}

      {/* Modal create topic for instructors */}
      <EduModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Thêm Đề tài Đồ án mới"
      >
        <form onSubmit={handleCreateTopic} className="flex flex-col gap-4">
          <EduInput
            label="Mã đề tài"
            placeholder="VD: DT-01"
            value={newCode}
            onChange={(e) => setNewCode(e.target.value)}
            required
          />
          <EduInput
            label="Tên đề tài"
            placeholder="Nhập tên đề tài đồ án..."
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            required
          />
          <div>
            <label className="text-sm font-semibold text-[#0f2236] block mb-1.5">
              Mô tả yêu cầu
            </label>
            <textarea
              rows={3}
              placeholder="Mô tả phạm vi, công nghệ hoặc yêu cầu đề tài..."
              value={newDesc}
              onChange={(e) => setNewDesc(e.target.value)}
              className="w-full rounded-xl border border-[rgba(15,34,54,0.18)] p-3 text-sm text-[#0f2236] outline-none focus:ring-2 focus:ring-[#7fbbdd]"
            />
          </div>
          <EduInput
            label="Số lượng nhóm tối đa"
            type="number"
            min={1}
            max={20}
            value={newMax}
            onChange={(e) => setNewMax(Number(e.target.value) || 1)}
          />

          <div className="flex justify-end gap-3 pt-3">
            <EduButton variant="secondary" onClick={() => setIsCreateOpen(false)}>
              Hủy
            </EduButton>
            <EduButton type="submit" variant="primary" isLoading={isCreating}>
              Lưu đề tài
            </EduButton>
          </div>
        </form>
      </EduModal>
    </div>
  );
};
