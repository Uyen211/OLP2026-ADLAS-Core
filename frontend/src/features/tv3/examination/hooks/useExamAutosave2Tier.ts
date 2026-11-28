// Copyright (c) 2026 ADLAS Team - OLP 2026 Open Source Software Track
// SPDX-License-Identifier: MIT

import { useEffect, useRef, useState, useCallback } from "react";
import { indexedDbExamStore } from "../utils/indexedDbExamStore";
import { examinationService } from "../../../../services/examinationService";
import type { LocalExamDraft, StudentAnswersMap } from "../../../../types/examination";

export type AutosaveSyncStatus = "synced" | "saving" | "offline_saved" | "error";

interface UseExamAutosave2TierParams {
  submissionId: string;
  quizId: string;
  initialSeqNum?: number;
  initialAnswers?: StudentAnswersMap;
  initialFlagged?: string[];
}

export function useExamAutosave2Tier({
  submissionId,
  quizId,
  initialSeqNum = 0,
  initialAnswers = {},
  initialFlagged = [],
}: UseExamAutosave2TierParams) {
  const [answers, setAnswers] = useState<StudentAnswersMap>(initialAnswers);
  const [flaggedQuestions, setFlaggedQuestions] = useState<string[]>(initialFlagged);
  const [syncStatus, setSyncStatus] = useState<AutosaveSyncStatus>("synced");
  const [lastSavedAt, setLastSavedAt] = useState<string>(new Date().toISOString());

  const seqNumRef = useRef<number>(initialSeqNum);
  const answersRef = useRef<StudentAnswersMap>(initialAnswers);
  const flaggedRef = useRef<string[]>(initialFlagged);
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isOnlineRef = useRef<boolean>(typeof navigator !== "undefined" ? navigator.onLine : true);

  answersRef.current = answers;
  flaggedRef.current = flaggedQuestions;

  // Tier 1: Cập nhật cục bộ vào IndexedDB ngay lập tức
  const saveLocalDraft = useCallback(async () => {
    const draft: LocalExamDraft = {
      submission_id: submissionId,
      quiz_id: quizId,
      seq_num: seqNumRef.current,
      answers: answersRef.current,
      flagged_questions: flaggedRef.current,
      updated_at: new Date().toISOString(),
    };
    await indexedDbExamStore.saveDraft(draft);
  }, [submissionId, quizId]);

  // Tier 2: Đồng bộ lên Server qua API autosaveAttempt
  const syncToServer = useCallback(async () => {
    if (!navigator.onLine) {
      setSyncStatus("offline_saved");
      return;
    }

    setSyncStatus("saving");
    try {
      const currentSeq = seqNumRef.current;
      await examinationService.autosaveAttempt(submissionId, {
        answers: answersRef.current,
        seq_num: currentSeq,
      });
      setSyncStatus("synced");
      setLastSavedAt(new Date().toISOString());
    } catch {
      setSyncStatus("offline_saved");
    }
  }, [submissionId]);

  // Hàm chọn hoặc sửa đáp án
  const updateAnswer = useCallback(
    (questionId: string, selectedOptions: string[]) => {
      seqNumRef.current += 1;
      const nextAnswers = {
        ...answersRef.current,
        [questionId]: selectedOptions,
      };
      setAnswers(nextAnswers);
      answersRef.current = nextAnswers;

      // Tier 1: Lưu IndexedDB tức thì
      saveLocalDraft();

      // Tier 2: Debounce 600ms đẩy lên server
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      setSyncStatus("saving");
      debounceTimerRef.current = setTimeout(() => {
        syncToServer();
      }, 600);
    },
    [saveLocalDraft, syncToServer]
  );

  // Đánh dấu cờ câu hỏi
  const toggleFlagQuestion = useCallback(
    (questionId: string) => {
      setFlaggedQuestions((prev) => {
        const next = prev.includes(questionId)
          ? prev.filter((id) => id !== questionId)
          : [...prev, questionId];
        flaggedRef.current = next;
        saveLocalDraft();
        return next;
      });
    },
    [saveLocalDraft]
  );

  // Lắng nghe sự kiện Online để tự động flush đồng bộ dữ liệu
  useEffect(() => {
    const handleOnline = () => {
      isOnlineRef.current = true;
      syncToServer();
    };

    const handleOffline = () => {
      isOnlineRef.current = false;
      setSyncStatus("offline_saved");
    };

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [syncToServer]);

  return {
    answers,
    flaggedQuestions,
    syncStatus,
    lastSavedAt,
    updateAnswer,
    toggleFlagQuestion,
    flushSync: syncToServer,
  };
}
