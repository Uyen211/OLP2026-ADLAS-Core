// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { PageHeader, EduTabs } from "../../../../design-system";
import { GroupFormationPanel } from "../components/GroupFormationPanel";
import { TopicSlotList } from "../components/TopicSlotList";
import { InstructorGroupMatrix } from "../components/InstructorGroupMatrix";
import { assessmentService } from "../../../../services/assessmentService";
import { useAuthStore } from "../../../../stores/authStore";
import type { StudentGroupResponse, TopicResponse } from "../../../../types/assessment";

export const ProjectGroupWorkspacePage: React.FC = () => {
  const { assignmentId } = useParams<{ assignmentId: string }>();
  const me = useAuthStore((s) => s.me);
  const isInstructor = me?.system_role === "TEACHER" || me?.system_role === "ADMIN";

  const [activeTab, setActiveTab] = useState<string>("my-group");
  const [topics, setTopics] = useState<TopicResponse[]>([]);
  const [myGroup, setMyGroup] = useState<StudentGroupResponse | null>(null);
  const [allGroups, setAllGroups] = useState<StudentGroupResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = async () => {
    if (!assignmentId) return;
    setIsLoading(true);
    try {
      const [tList, gList, currentGroup] = await Promise.all([
        assessmentService.listTopics(assignmentId).catch(() => []),
        isInstructor ? assessmentService.listGroups(assignmentId).catch(() => []) : Promise.resolve([]),
        assessmentService.getMyGroup(assignmentId).catch(() => null),
      ]);
      setTopics(tList);
      setAllGroups(gList);
      setMyGroup(currentGroup);
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
    { id: "my-group", label: "Nhóm của tôi" },
    { id: "topics", label: "Đề tài đồ án", badge: topics.length },
    ...(isInstructor ? [{ id: "matrix", label: "Quản lý toàn bộ nhóm" }] : []),
  ];

  return (
    <div className="w-full max-w-7xl mx-auto p-4 sm:p-6 lg:p-8">
      <PageHeader
        breadcrumbs={[
          { label: "Môn học", href: "/courses" },
          { label: "Bài tập & Đồ án", href: `/courses` },
          { label: "Không gian Nhóm & Đề tài" },
        ]}
        title="Không gian Làm việc Nhóm & Đề tài"
        description="Gia nhập nhóm bằng mã mời, đăng ký đề tài đồ án và thực hiện đánh giá chéo năng lực thành viên."
      />

      <div className="mb-6">
        <EduTabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />
      </div>

      {isLoading ? (
        <div className="p-8 text-center text-[#4a5f75]">Đang tải dữ liệu nhóm và đề tài...</div>
      ) : (
        <>
          {activeTab === "my-group" && (
            <GroupFormationPanel
              assignmentId={assignmentId || ""}
              currentGroup={myGroup}
              userId={me?.id}
              onGroupUpdated={loadData}
            />
          )}

          {activeTab === "topics" && (
            <TopicSlotList
              assignmentId={assignmentId || ""}
              topics={topics}
              currentTopicId={myGroup?.topic_id}
              groupId={myGroup?.id}
              isLeader={myGroup?.leader_student_id === me?.id}
              isInstructor={isInstructor}
              onTopicSelected={loadData}
              onTopicCreated={loadData}
            />
          )}

          {activeTab === "matrix" && isInstructor && (
            <InstructorGroupMatrix
              assignmentId={assignmentId || ""}
              groups={allGroups}
              onRefresh={loadData}
            />
          )}
        </>
      )}
    </div>
  );
};
