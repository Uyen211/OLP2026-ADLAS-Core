// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useState } from "react";
import { CheckCircle2, AlertCircle, Send, ShieldCheck, HelpCircle } from "lucide-react";
import { EduButton, EduCard } from "../../../../design-system";
import type { StudentGroupResponse, PeerReviewSubmitRequest } from "../../../../types/assessment";
import { assessmentService } from "../../../../services/assessmentService";

export interface PeerReviewMatrixProps {
  assignmentId: string;
  group: StudentGroupResponse;
  currentUserId: string;
  milestoneId?: string;
  onSubmitted?: () => void;
}

interface PeerScoreState {
  revieweeId: string;
  revieweeName: string;
  contributionScore: number;
  cooperationScore: number;
  qualityScore: number;
  comments: string;
}

export const PeerReviewMatrix: React.FC<PeerReviewMatrixProps> = ({
  assignmentId,
  group,
  currentUserId,
  milestoneId,
  onSubmitted,
}) => {
  // Loại trừ bản thân: Blind review chỉ đánh giá các bạn cùng nhóm khác
  const peers = (group.members || []).filter((m) => m.student_id !== currentUserId);

  const [scores, setScores] = useState<Record<string, PeerScoreState>>(() => {
    const initial: Record<string, PeerScoreState> = {};
    peers.forEach((p) => {
      initial[p.student_id] = {
        revieweeId: p.student_id,
        revieweeName: p.student_name || "Thành viên nhóm",
        contributionScore: 80,
        cooperationScore: 80,
        qualityScore: 80,
        comments: "",
      };
    });
    return initial;
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const updatePeerField = (
    peerId: string,
    field: keyof PeerScoreState,
    value: number | string
  ) => {
    setScores((prev) => ({
      ...prev,
      [peerId]: {
        ...prev[peerId],
        [field]: value,
      },
    }));
  };

  const calculateOverall = (state: PeerScoreState): number => {
    // Trọng số: 40% khối lượng, 30% phối hợp, 30% chất lượng
    const overall =
      state.contributionScore * 0.4 +
      state.cooperationScore * 0.3 +
      state.qualityScore * 0.3;
    return Math.round(overall);
  };

  const validateAll = (): string | null => {
    if (peers.length === 0) {
      return "Nhóm chưa có thành viên khác để đánh giá.";
    }
    for (const p of peers) {
      const s = scores[p.student_id];
      if (!s) return `Chưa hoàn thành đánh giá cho ${p.student_name}.`;
      if (s.comments.trim().length < 15) {
        return `Vui lòng viết nhận xét chi tiết (tối thiểu 15 ký tự) cho thành viên ${p.student_name}.`;
      }
    }
    return null;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const validationError = validateAll();
    if (validationError) {
      setErrorMsg(validationError);
      return;
    }

    setIsSubmitting(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      for (const p of peers) {
        const s = scores[p.student_id];
        const overallScore = calculateOverall(s);
        const payload: PeerReviewSubmitRequest = {
          reviewee_id: p.student_id,
          criteria_scores: {
            contribution: s.contributionScore,
            cooperation: s.cooperationScore,
            quality: s.qualityScore,
          },
          total_score: overallScore,
          comment: s.comments.trim(),
          milestone_id: milestoneId,
        };
        await assessmentService.submitPeerReview(assignmentId, payload);
      }
      setSuccessMsg("Gửi đánh giá chéo thành công. Dữ liệu đánh giá hoàn toàn được ẩn danh.");
      if (onSubmitted) onSubmitted();
    } catch (err: any) {
      setErrorMsg(err?.message || "Không thể gửi đánh giá chéo. Vui lòng thử lại.");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (peers.length === 0) {
    return (
      <EduCard variant="surface" padding="lg">
        <div className="text-center py-6">
          <HelpCircle className="w-10 h-10 text-[#4a5f75] mx-auto mb-2" />
          <h3 className="text-base font-bold text-[#0f2236]">Chưa thể thực hiện Đánh giá chéo</h3>
          <p className="text-sm text-[#4a5f75] mt-1 max-w-md mx-auto">
            Nhóm của bạn hiện tại chưa có thành viên nào khác ngoài bạn. Hãy chia sẻ mã mời nhóm để các thành viên khác gia nhập.
          </p>
        </div>
      </EduCard>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Privacy guarantee banner */}
      <div className="flex items-start gap-3 p-4 rounded-xl bg-[#eaf6fa] border border-[#7fbbdd] text-[#0f2236]">
        <ShieldCheck className="w-5 h-5 text-[#006699] shrink-0 mt-0.5" />
        <div className="text-sm">
          <span className="font-bold block">Cam kết ẩn danh tuyệt đối (Blind Peer Review)</span>
          <span className="text-[#4a5f75]">
            Điểm số và nhận xét của bạn chỉ được hệ thống tổng hợp để tính hệ số đóng góp Fi. Các thành viên khác sẽ không biết danh tính người đánh giá. Hãy đánh giá công tâm, trung thực và xây dựng.
          </span>
        </div>
      </div>

      {errorMsg && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-[#fff1f2] border border-[#fecdd3] text-[#be123c] text-sm">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {successMsg && (
        <div className="flex items-center gap-2 p-3 rounded-xl bg-[#ecfdf5] border border-[#a7f3d0] text-[#15803d] text-sm">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{successMsg}</span>
        </div>
      )}

      <div className="space-y-5">
        {peers.map((peer, idx) => {
          const s = scores[peer.student_id] || {
            contributionScore: 80,
            cooperationScore: 80,
            qualityScore: 80,
            comments: "",
          };
          const overall = calculateOverall(s);

          return (
            <EduCard key={peer.id} variant="surface" padding="md" className="border border-[rgba(15,34,54,0.12)]">
              <div className="flex items-center justify-between pb-3 border-b border-[rgba(15,34,54,0.06)]">
                <div className="flex items-center gap-2.5">
                  <span className="w-7 h-7 rounded-full bg-[#f58b05] text-white text-xs font-bold flex items-center justify-center">
                    {idx + 1}
                  </span>
                  <div>
                    <h4 className="text-base font-bold text-[#0f2236]">
                      {peer.student_name || "Thành viên nhóm"}
                    </h4>
                    <span className="text-xs text-[#4a5f75]">{peer.student_email || ""}</span>
                  </div>
                </div>

                <div className="text-right">
                  <span className="text-xs uppercase text-[#4a5f75] block font-semibold">Điểm tổng kết</span>
                  <span className="text-lg font-bold font-mono text-[#006699]">
                    {overall} <span className="text-xs font-normal text-[#4a5f75]">/ 100</span>
                  </span>
                </div>
              </div>

              {/* Tiêu chí 1: Khối lượng đóng góp */}
              <div className="mt-4 space-y-4">
                <div>
                  <div className="flex justify-between items-center text-xs font-semibold mb-1">
                    <span className="text-[#0f2236]">1. Khối lượng công việc & Mức độ chủ động (40%)</span>
                    <span className="font-mono text-[#006699] text-sm">{s.contributionScore} đ</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={s.contributionScore}
                    onChange={(e) => updatePeerField(peer.student_id, "contributionScore", Number(e.target.value))}
                    className="w-full accent-[#006699] cursor-pointer"
                  />
                </div>

                {/* Tiêu chí 2: Tinh thần phối hợp & Đúng hạn */}
                <div>
                  <div className="flex justify-between items-center text-xs font-semibold mb-1">
                    <span className="text-[#0f2236]">2. Tinh thần hợp tác, giao tiếp & Đúng hạn (30%)</span>
                    <span className="font-mono text-[#006699] text-sm">{s.cooperationScore} đ</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={s.cooperationScore}
                    onChange={(e) => updatePeerField(peer.student_id, "cooperationScore", Number(e.target.value))}
                    className="w-full accent-[#006699] cursor-pointer"
                  />
                </div>

                {/* Tiêu chí 3: Chất lượng kỹ thuật */}
                <div>
                  <div className="flex justify-between items-center text-xs font-semibold mb-1">
                    <span className="text-[#0f2236]">3. Chất lượng chuyên môn & Đóng góp giải pháp (30%)</span>
                    <span className="font-mono text-[#006699] text-sm">{s.qualityScore} đ</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={s.qualityScore}
                    onChange={(e) => updatePeerField(peer.student_id, "qualityScore", Number(e.target.value))}
                    className="w-full accent-[#006699] cursor-pointer"
                  />
                </div>

                {/* Nhận xét định tính */}
                <div>
                  <label className="block text-xs font-semibold text-[#0f2236] mb-1">
                    Nhận xét định tính mang tính xây dựng <span className="text-[#be123c]">*</span>
                  </label>
                  <textarea
                    rows={2}
                    value={s.comments}
                    onChange={(e) => updatePeerField(peer.student_id, "comments", e.target.value)}
                    placeholder="Nêu rõ điểm mạnh, tinh thần trách nhiệm và những điểm thành viên cần cải thiện..."
                    className="w-full rounded-xl border border-[rgba(15,34,54,0.16)] px-3 py-2 text-sm text-[#0f2236] placeholder-[#4a5f75] focus:outline-none focus:ring-2 focus:ring-[#7fbbdd] focus:border-[#006699] bg-[#f5fbfd]"
                  />
                  <div className="flex justify-between text-[11px] text-[#4a5f75] mt-1">
                    <span>Tối thiểu 15 ký tự</span>
                    <span>{s.comments.trim().length} ký tự</span>
                  </div>
                </div>
              </div>
            </EduCard>
          );
        })}
      </div>

      <div className="flex justify-end pt-2">
        <EduButton
          type="submit"
          variant="primary"
          size="lg"
          disabled={isSubmitting}
        >
          <Send className="w-4 h-4 mr-2" />
          {isSubmitting ? "Đang gửi đánh giá..." : "Gửi toàn bộ Đánh giá chéo"}
        </EduButton>
      </div>
    </form>
  );
};
