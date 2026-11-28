// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { PageHeader, EduTabs } from "../../../../design-system";
import { PeerReviewMatrix } from "../components/PeerReviewMatrix";
import { PeerReviewFactorTable } from "../components/PeerReviewFactorTable";
import { assessmentService } from "../../../../services/assessmentService";
import { useAuthStore } from "../../../../stores/authStore";
import type {
  StudentGroupResponse,
  PeerReviewSummaryResponse,
} from "../../../../types/assessment";

export const PeerReviewPage: React.FC = () => {
  const { assignmentId } = useParams<{ assignmentId: string }>();
  const me = useAuthStore((s) => s.me);
  const isInstructor = me?.system_role === "TEACHER" || me?.system_role === "ADMIN";

  const [activeTab, setActiveTab] = useState<string>("evaluate");
  const [currentGroup, setCurrentGroup] = useState<StudentGroupResponse | null>(null);
  const [summary, setSummary] = useState<PeerReviewSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = async () => {
    if (!assignmentId) return;
    setIsLoading(true);
    try {
      const myGroup = await assessmentService.getMyGroup(assignmentId).catch(() => null);
      setCurrentGroup(myGroup);

      if (myGroup) {
        const factors = await assessmentService
          .getPeerReviewFactors(assignmentId, myGroup.id)
          .catch(() => null);
        setSummary(factors);
      }
    } catch {
      // Non-blocking
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [assignmentId]);

  const tabs = [
    { id: "evaluate", label: "Đánh giá chéo thành viên" },
    { id: "summary", label: "Bảng tổng hợp hệ số Fi" },
  ];

  return (
    <div className="w-full max-w-5xl mx-auto p-4 sm:p-6 lg:p-8">
      <PageHeader
        breadcrumbs={[
          { label: "Môn học", href: "/courses" },
          { label: "Bài tập & Đồ án", href: `/courses` },
          { label: "Đánh giá chéo Blind Peer Review" },
        ]}
        title="Đánh giá chéo Năng lực & Đóng góp (Blind Peer Review)"
        description="Đánh giá ẩn danh sự đóng góp của các thành viên trong nhóm nhằm xác định hệ số điều chỉnh điểm Fi công bằng và minh bạch."
      />

      <div className="mb-6">
        <EduTabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-[#4a5f75]">Đang tải thông tin đánh giá chéo...</div>
      ) : !currentGroup ? (
        <div className="p-8 text-center text-[#4a5f75] bg-white rounded-2xl border border-[rgba(15,34,54,0.08)]">
          Bạn chưa tham gia nhóm nào trong bài tập này để thực hiện đánh giá chéo.
        </div>
      ) : (
        <>
          {activeTab === "evaluate" && me && (
            <PeerReviewMatrix
              assignmentId={assignmentId || ""}
              group={currentGroup}
              currentUserId={me.id}
              onSubmitted={loadData}
            />
          )}

          {activeTab === "summary" && summary && (
            <PeerReviewFactorTable
              summary={summary}
              isInstructor={isInstructor}
            />
          )}
        </>
      )}
    </div>
  );
};
